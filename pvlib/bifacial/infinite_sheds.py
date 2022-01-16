r"""
Infinite Sheds
==============

The "infinite sheds" model is a 2-dimensional model of irradiance on the front
and rear surfaces of a PV array. The model assumes that the array comprises
parallel, equally spaced rows (sheds) and calculates irradiance in the middle
of a shed which is long enough that end-of-row effects are negligible. Rows
can be at fixed tilt or on single-axis trackers.

The ground is assumed to be flat and level. To consider arrays on an
non-level ground, rotate the solar vector into the reference frame of the
ground plane.

The infinite shdes model accounts for the following effects:
    - limited view from the row surfaces to the sky due to blocking of the
      sky by nearby rows;
    - reduction of irradiance reaching the ground due to shadows cast by
      rows and due to blocking of the sky by nearby rows.
The model operates in the following steps:
1. Find the fraction of unshaded ground between rows, ``f_gnd_beam`` where
   both direct and diffuse irradiance is recieved. The model assumes that
   there is no direct irradiance in the shaded fraction ``1 - f_gnd_beam``.
2. Calculate the view factor,``fz_sky``, from the ground to the sky accounting
   for the parts of the sky that are blocked from view by the array's rows.
   The view factor is multipled by the sky diffuse irradiance to calculate
   the diffuse irradiance reaching the ground. Sky diffuse irradiance is thus
   assumed to be isotropic.
3. Calculate the view factor from the row surface to the ground which
   determines the fraction of ground-reflected irradiance that reaches the row
   surface.
4. Find the fraction of the row surface that is shaded from direct irradiance.
   Only sky and ground-reflected irradiance reach the the shaded fraction of
   the row surface.
5. For the front and rear surfaces, apply the incidence angle modifier to
   the direct irradiance and sum the diffuse sky, diffuse ground, and direct
   irradiance to compute the plane-of-array (POA) irradiance on each surface.
6. Apply the bifaciality factor, shade factor and transmission factor to
   the rear surface POA irradiance and add the result to the front surface
   POA irradiance to calculate the total POA irradiance on the row.

Array geometry is defined by the following:
    - ground coverage ratio (GCR), ``gcr``, the ratio of row slant height to
      the spacing between rows (pitch).
    - height of row center above ground, ``height``.
    - tilt of the row from horizontal, ``surface_tilt``.
    - azimuth of the row's normal vector, ``surface_azimuth``.
    - azimuth of the tracking axis, ``axis_azimuth``, when the array is on
      single axis trackers.
View factors from the ground to the sky are calculated at points spaced along
a one-dimensional axis on the ground, with the origin under the center of a
row and the positive direction toward the right. The positive direction is
considered to be towards the "front" of the array.

That's it folks! This model is influenced by the 2D model published by Marion,
*et al.* in [1].

References
----------
[1] A Practical Irradiance Model for Bifacial PV Modules, Bill Marion, et al.,
IEEE PVSC 2017
[2] Bifacial Performance Modeling in Large Arrays, Mikofski, et al., IEEE PVSC
2018
"""

from collections import OrderedDict
import numpy as np
import pandas as pd
from pvlib.tools import cosd, sind
from pvlib.bifacial import utils
from pvlib.shading import shaded_fraction, masking_angle
from pvlib.irradiance import get_ground_diffuse, beam_component

# TODO: document deviations from PVSC paper
# TODO: add reference to docstrings for public functions


def _tilt_to_rotation(surface_tilt, surface_azimuth, axis_azimuth=None):
    """
    Convert surface tilt to rotation angle.

    Surface tilt angles are positive by definition. A positive rotation
    angle is counterclockwise in a right hand coordinate system with the
    axis of rotation positive in the direction of axis_azimuth. A positive
    rotation elevates the left (bottom) edge of the row.

    Parameters
    ----------
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    surface_azimuth : numeric
        Surface azimuth angles in decimal degrees east of north
        (e.g. North = 0, South=180 East = 90, West = 270). surface_azimuth must
        be >=0 and <=360.
    axis_azimuth : float or None, default None
        The azimuth of the axis of rotation. Decimal degrees east of north.
        For fixed tilt, set axis_azimuth = None.

    Returns
    -------
    float or np.ndarray
        Calculated rotation angle(s) in [deg]

    Notes
    -----
    Based on pvfactors.geometry.base._get_rotation_from_tilt_azimuth
    """
    if axis_azimuth is None:
        # Assume fixed tilt. Place axis_azimuth 90 degrees clockwise so that
        # tilt becomes a negative rotation (lowers left/bottom edge)
        axis_azimuth = ((surface_azimuth + 90.) + 360) % 360
    # Calculate rotation of PV row (signed tilt angle)
    is_pointing_right = ((surface_azimuth - axis_azimuth) % 360.) < 180.
    rotation = np.where(is_pointing_right, surface_tilt, -surface_tilt)
    return rotation


def _vf_ground_sky_integ(surface_tilt, surface_azimuth, gcr, height,
                         pitch, axis_azimuth=None, max_rows=5, npoints=100):
    """
    Integrated and per-point view factors from the ground to the sky at points
    between interior rows of the array.

    Parameters
    ----------
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    surface_azimuth : numeric
        Surface azimuth angles in decimal degrees east of north
        (e.g. North = 0, South=180 East = 90, West = 270). surface_azimuth must
        be >=0 and <=360.
    gcr : float
        Ratio of row slant length to row spacing (pitch). [unitless]
    height : float
        Height of the center point of the row above the ground; must be in the
        same units as ``pitch``.
    pitch : float
        Distance between two rows. Must be in the same units as ``height``.
    axis_azimuth : numeric, default None
        The compass direction of the axis of rotation lies for a single-axis
        tracking system. Decimal degrees east of north.
    max_rows : int, default 5
        Maximum number of rows to consider in front and behind the current row.
    npoints : int, default 100
        Number of points used to discretize distance along the ground.

    Returns
    -------
    fgnd_sky : float
        Integration of view factor over the length between adjacent, interior
        rows. [unitless]
    fz : ndarray
        Fraction of distance from the previous row to the next row. [unitless]
    fz_sky : ndarray
        View factors at discrete points between adjacent, interior rows.
        [unitless]

    """
    z = np.linspace(0, 1, npoints)
    rotation = np.atleast_1d(_tilt_to_rotation(
        surface_tilt, surface_azimuth, axis_azimuth))
    # calculate the view factor from the ground to the sky. Accounts for
    # views between rows both towards the array front, and array back
    # TODO: vectorize over rotation
    fz_sky = np.zeros((len(rotation), npoints))
    for k, r in enumerate(rotation):
        vf, _ = utils._vf_ground_sky_2d(z, r, gcr, pitch, height, max_rows)
        fz_sky[k, :] = vf
    # calculate the integrated view factor for all of the ground between rows
    fgnd_sky = np.trapz(fz_sky, z, axis=1)

    return fgnd_sky, z, fz_sky


def _poa_ground_shadows(poa_ground, f_gnd_beam, df, vf_gnd_sky):
    """
    Reduce ground-reflected irradiance to the tilted plane (poa_ground) to
    account for shadows on the ground.

    Parameters
    ----------
    poa_ground : numeric
        Ground reflected irradiance on the tilted surface, assuming full GHI
        illumination on all of the ground. [W/m^2]
    f_gnd_beam : numeric
        Fraction of the distance between rows that is illuminated (unshaded).
        [unitless]
    df : numeric
        Diffuse fraction, the ratio of DHI to GHI. [unitless]
    vf_gnd_sky : numeric
        View factor from the ground to the sky, integrated along the distance
        between rows. [unitless]

    Returns
    -------
    poa_gnd_sky : numeric
        Adjusted ground-reflected irradiance accounting for shadows on the
        ground. [W/m^2]

    """
    df = np.where(np.isfinite(df), df, 0.0)
    return poa_ground * (f_gnd_beam*(1 - df) + df*vf_gnd_sky)


def _vf_row_sky_integ(f_x, surface_tilt, gcr, npoints=100):
    """
    Integrated view factors from the shaded and unshaded parts of
    the row slant height to the sky.

    Parameters
    ----------
    f_x : numeric
        Fraction of row slant height from the bottom that is shaded. [unitless]
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    gcr : float
        Ratio of row slant length to row spacing (pitch). [unitless]
    npoints : int, default 100
        Number of points for integration. [unitless]

    Returns
    -------
    vf_shade_sky_integ : numeric
        Integrated view factor from the shaded part of the row to the sky.
        [unitless]
    vf_noshade_sky_integ : numeric
        Integrated view factor from the unshaded part of the row to the sky.
        [unitless]

    Notes
    -----
    The view factor to the sky at a point x along the row slant height is
    given by

    .. math ::
        \\large{f_{sky} = \frac{1}{2} \\left(\\cos\\left(\\psi_t\\right) +
        \\cos \\left(\\beta\\right) \\right)

    where :math:`\\psi_t` is the angle from horizontal of the line from point
    x to the top of the facing row, and :math:`\\beta` is the surface tilt.

    View factors are integrated separately over shaded and unshaded portions
    of the row slant height.

    """
    # handle Series inputs
    surface_tilt = np.array(surface_tilt)
    cst = cosd(surface_tilt)
    # shaded portion
    x = np.linspace(0 * f_x, f_x, num=npoints)
    psi_t_shaded = masking_angle(surface_tilt, gcr, x)
    y = 0.5 * (cosd(psi_t_shaded) + cst)
    # integrate view factors from each point in the discretization. This is an
    # improvement over the algorithm described in [2]
    vf_shade_sky_integ = np.trapz(y, x, axis=0)
    # unshaded portion
    x = np.linspace(f_x, np.ones_like(f_x), num=npoints)
    psi_t_unshaded = masking_angle(surface_tilt, gcr, x)
    y = 0.5 * (cosd(psi_t_unshaded) + cst)
    vf_noshade_sky_integ = np.trapz(y, x, axis=0)
    return vf_shade_sky_integ, vf_noshade_sky_integ


def _poa_sky_diffuse_pv(f_x, dhi, vf_shade_sky_integ, vf_noshade_sky_integ):
    """
    Sky diffuse POA from integrated view factors combined for both shaded and
    unshaded parts of the surface.

    Parameters
    ----------
    f_x : numeric
        Fraction of row slant height from the bottom that is shaded. [unitless]
    dhi : numeric
        Diffuse horizontal irradiance (DHI). [W/m^2]
    vf_shade_sky_integ : numeric
        Integrated view factor from the shaded part of the row to the sky.
        [unitless]
    vf_noshade_sky_integ : numeric
        Integrated view factor from the unshaded part of the row to the sky.
        [unitless]

    Returns
    -------
    poa_sky_diffuse_pv : numeric
        Total sky diffuse irradiance incident on the PV surface. [W/m^2]
    """
    return dhi * (f_x * vf_shade_sky_integ + (1 - f_x) * vf_noshade_sky_integ)


def _ground_angle(x, surface_tilt, gcr):
    """
    Angle from horizontal of the line from a point x on the row slant length
    to the bottom of the facing row.

    The angles are clockwise from horizontal, rather than the usual
    counterclockwise direction.

    Parameters
    ----------
    x : numeric
        fraction of row slant length from bottom, ``x = 0`` is at the row
        bottom, ``x = 1`` is at the top of the row.
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    gcr : float
        ground coverage ratio, ratio of row slant length to row spacing.
        [unitless]

    Returns
    -------
    psi : numeric
        Angle [degree].
    tan_psi : numeric
        Tangent of angle [unitless]
    """
    #  : \\            \
    #  :  \\            \
    #  :   \\            \
    #  :    \\            \  facing row
    #  :     \\.___________\
    #  :       \  ^*-.  psi \
    #  :        \  x   *-.   \
    #  :         \  v      *-.\
    #  :          \<-----P---->\

    x1 = x * sind(surface_tilt)
    x2 = (x * cosd(surface_tilt) + 1 / gcr)
    psi = np.arctan2(x1, x2)  # do this first because it handles 0 / 0
    tan_psi = np.tan(psi)
    return np.rad2deg(psi), tan_psi


def _vf_row_ground(x, surface_tilt, gcr):
    """
    View factor from a point x on the row to the ground.

    Parameters
    ----------
    x : numeric
        Fraction of row slant height from the bottom. [unitless]
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    gcr : float
        Ground coverage ratio, ratio of row slant length to row spacing.
        [unitless]

    Returns
    -------
    vf : numeric
        View factor from the point at x to the ground. [unitless]

    """
    cst = cosd(surface_tilt)
    # angle from horizontal at the point x on the row slant height to the
    # bottom of the facing row
    psi_t_shaded, _ = _ground_angle(x, surface_tilt, gcr)
    # view factor from the point on the row to the ground
    return 0.5 * (cosd(psi_t_shaded) - cst)


def _vf_row_ground_integ(f_x, surface_tilt, gcr, npoints=100):
    """
    View factors to the ground from shaded and unshaded parts of a row.

    Parameters
    ----------
    f_x : numeric
        Fraction of row slant height from the bottom that is shaded. [unitless]
    surface_tilt : numeric
        Surface tilt angle in degrees from horizontal, e.g., surface facing up
        = 0, surface facing horizon = 90. [degree]
    gcr : float
        Ground coverage ratio, ratio of row slant length to row spacing.
        [unitless]
    npoints : int, default 100
        Number of points for integration. [unitless]

    Returns
    -------
    vf_shade_ground_integ : numeric
        View factor from the shaded portion of the row to the ground.
        [unitless]
    vf_noshade_ground_integ : numeric
        View factor from the unshaded portion of the row to the ground.
        [unitless]

    Notes
    -----
    The view factor to the ground at a point x along the row slant height is
    given by

    .. math ::
        \\large{f_{gr} = \frac{1}{2} \\left(\\cos\\left(\\psi_t\\right) -
        \\cos \\left(\\beta\\right) \\right)

    where :math:`\\psi_t` is the angle from horizontal of the line from point
    x to the bottom of the facing row, and :math:`\\beta` is the surface tilt.

    Each view factor is integrated over the relevant portion of the row
    slant height.
    """
    # handle Series inputs
    surface_tilt = np.array(surface_tilt)
    # shaded portion of row slant height
    x = np.linspace(0 * f_x, f_x, num=npoints)
    # view factor from the point on the row to the ground
    y = _vf_row_ground(gcr, surface_tilt, x)
    # integrate view factors along the shaded portion of the row slant height.
    # This is an improvement over the algorithm described in [2]
    vf_shade_ground_integ = np.trapz(y, x, axis=0)

    # unshaded portion of row slant height
    x = np.linspace(f_x, np.ones_like(f_x), num=npoints)
    # view factor from the point on the row to the ground
    y = _vf_row_ground(gcr, surface_tilt, x)
    # integrate view factors along the unshaded portion.
    # This is an improvement over the algorithm described in [2]
    vf_noshade_ground_integ = np.trapz(y, x, axis=0)

    return vf_shade_ground_integ, vf_noshade_ground_integ


def _poa_ground_pv(f_x, poa_gnd_sky, f_gnd_pv_shade, f_gnd_pv_noshade):
    """
    Reduce ground-reflected irradiance to account for limited view of the
    ground from the row surface.

    Parameters
    ----------
    f_x : numeric
        Fraction of row slant height from the bottom that is shaded. [unitless]
    poa_gnd_sky : numeric
        Ground-reflected irradiance that would reach the row surface if the
        full ground was visible. poa_gnd_sky accounts for limited view of the
        sky from the ground. [W/m^2]
    f_gnd_pv_shade : numeric
        fraction of ground visible from shaded part of PV surface. [unitless]
    f_gnd_pv_noshade : numeric
        fraction of ground visible from unshaded part of PV surface. [unitless]

    Returns
    -------
    mumeric
        Ground diffuse irradiance on the row plane. [W/m^2]
    """
    return poa_gnd_sky * (f_x * f_gnd_pv_shade + (1 - f_x) * f_gnd_pv_noshade)


def get_irradiance_poa(surface_tilt, surface_azimuth, solar_zenith,
                       solar_azimuth, gcr, height, pitch, ghi, dhi, dni,
                       albedo, iam=1.0, axis_azimuth=None, max_rows=5,
                       npoints=100):
    r"""
    Calculate plane-of-array (POA) irradiance on one side of a row of modules.

    POA irradiance components include direct, diffuse and global (total).
    Irradiance values are not adjusted for solar spectrum or reduced
    by a module's aperture for light, which is quantified by the module's
    bifaciality factor.

    Parameters
    ----------
    surface_tilt : numeric
        Surface tilt angles in decimal degrees. Tilt must be >=0 and
        <=180. The tilt angle is defined as degrees from horizontal
        (e.g. surface facing up = 0, surface facing horizon = 90).

    surface_azimuth : numeric
        Surface azimuth angles in decimal degrees east of north
        (e.g. North = 0, South=180 East = 90, West = 270). surface_azimuth must
        be >=0 and <=360.

    solar_zenith : numeric
        True (not refraction-corrected) solar zenith angles in decimal
        degrees.

    solar_azimuth : numeric
        Solar azimuth angles in decimal degrees.

    gcr : float
        Ground coverage ratio, ratio of row slant length to row spacing.
        [unitless]

    height : float
        Height of the center point of the row above the ground; must be in the
        same units as ``pitch``.

    pitch : float
        Distance between two rows; must be in the same units as ``height``.

    ghi : numeric
        Global horizontal irradiance. [W/m2]

    dhi : numeric
        Diffuse horizontal irradiance. [W/m2]

    dni : numeric
        Direct normal irradiance. [W/m2]

    albedo : numeric
        Surface albedo. [unitless]

    iam : numeric, default 1.0
        Incidence angle modifier, the fraction of direct irradiance incident
        on the surface that is not reflected away. [unitless]

    axis_azimuth : numeric, default None
        The compass direction of the axis of rotation lies for a single-axis
        tracking system. Decimal degrees east of north.

    max_rows : int, default 5
        Maximum number of rows to consider in front and behind the current row.

    npoints : int, default 100
        Number of points used to discretize distance along the ground.


    Returns
    -------
    output : OrderedDict or DataFrame
        Output is a DataFrame when input ghi is a Series. See Notes for
        descriptions of content.

    Notes
    -----
    Input parameters ``height`` and ``pitch`` must have the same unit.

    ``output`` always includes:

    - ``poa_global`` : total POA irradiance. [W/m^2]
    - ``poa_diffuse`` : total diffuse POA irradiance from all sources. [W/m^2]
    - ``poa_direct`` : total direct POA irradiance. [W/m^2]
    - ``poa_diffuse_sky`` : total sky diffuse irradiance on the plane of array.
      [W/m^2]
    - ``poa_diffuse_ground`` : total ground-reflected diffuse irradiance on the
      plane of array. [W/m^2]

    See also
    --------
    get_irradiance
    """
    # Calculate some geometric quantities
    # fraction of ground between rows that is illuminated accounting for
    # shade from panels
    f_gnd_beam = utils._unshaded_ground_fraction(
        gcr, surface_tilt, surface_azimuth, solar_zenith, solar_azimuth)
    # integrated view factor from the ground to the sky, integrated between
    # adjacent rows interior to the array
    vf_gnd_sky, _, _ = _vf_ground_sky_integ(
        surface_tilt, surface_azimuth, gcr, height, pitch, axis_azimuth,
        max_rows, npoints)
    # fraction of row slant height that is shaded
    f_x = shaded_fraction(solar_zenith, solar_azimuth, surface_tilt,
                          surface_azimuth, gcr)

    # Integrated view factors to the sky from the shaded and unshaded parts of
    # the row slant height
    vf_shade_sky, vf_noshade_sky = _vf_row_sky_integ(
        f_x, surface_tilt, gcr)
    # angle from shadeline to bottom of facing row
    psi_shade, _ = _ground_angle(f_x, surface_tilt, gcr)
    # angle from top of row to bottom of facing row
    psi_bottom, _ = _ground_angle(1.0, surface_tilt, gcr)
    # view factors from the ground to shaded and unshaded portions of the row
    # slant height
    f_gnd_pv_shade, f_gnd_pv_noshade = _vf_row_ground_integ(
        f_x, surface_tilt, gcr)

    # Calculate some preliminary irradiance quantities
    # diffuse fraction
    df = dhi / ghi
    # sky diffuse reflected from the ground to an array consisting of a single
    # row
    poa_ground = get_ground_diffuse(surface_tilt, ghi, albedo)

    # Total sky diffuse recieved by both shaded and unshaded portions
    poa_sky_pv = _poa_sky_diffuse_pv(
        f_x, dhi, vf_shade_sky, vf_noshade_sky)

    # Reduce ground-reflected irradiance because other rows in the array
    # block irradiance from reaching the ground.
    # [2], Eq. 9
    poa_gnd_sky = _poa_ground_shadows(poa_ground, f_gnd_beam, df, vf_gnd_sky)

    # Further reduce ground-reflected irradiance because adjacent rows block
    # the view to the ground.
    poa_gnd_pv = _poa_ground_pv(
        f_x, poa_gnd_sky, f_gnd_pv_shade, f_gnd_pv_noshade)

    # add sky and ground-reflected irradiance on the row by irradiance
    # component
    poa_diffuse = poa_gnd_pv + poa_sky_pv
    # beam on plane, make an array for consistency with poa_diffuse
    poa_beam = np.atleast_1d(beam_component(
        surface_tilt, surface_azimuth, solar_zenith, solar_azimuth, dni))
    poa_direct = poa_beam * (1 - f_x) * iam  # direct only on the unshaded part
    poa_global = poa_direct + poa_diffuse

    output = OrderedDict(
        poa_global=poa_global, poa_direct=poa_direct,
        poa_diffuse=poa_diffuse, poa_ground_diffuse=poa_gnd_pv,
        poa_sky_diffuse=poa_sky_pv)
    if isinstance(poa_global, pd.Series):
        output = pd.DataFrame(output)
    return output


def get_irradiance(surface_tilt, surface_azimuth, solar_zenith, solar_azimuth,
                   gcr, height, pitch, ghi, dhi, dni,
                   albedo, iam_front=1.0, iam_back=1.0,
                   bifaciality=0.8, shade_factor=-0.02,
                   transmission_factor=0, max_rows=5, npoints=100):
    """
    Get bifacial irradiance using the infinite sheds model.

    Parameters
    ----------
    surface_tilt : numeric
        Surface tilt angles in decimal degrees. Tilt must be >=0 and
        <=180. The tilt angle is defined as degrees from horizontal
        (e.g. surface facing up = 0, surface facing horizon = 90).

    surface_azimuth : numeric
        Surface azimuth angles in decimal degrees. surface_azimuth must
        be >=0 and <=360. The Azimuth convention is defined as degrees
        east of north (e.g. North = 0, South=180 East = 90, West = 270).

    solar_zenith : numeric
        True (not refraction-corrected) solar zenith angles in decimal
        degrees.

    solar_azimuth : numeric
        Solar azimuth angles in decimal degrees.

    gcr : float
        Ground coverage ratio, ratio of row slant length to row spacing.
        [unitless]

    height : float
        Height of the center point of the row above the ground; must be in the
        same units as ``pitch``.

    pitch : float
        Distance between two rows; must be in the same units as ``height``.

    ghi : numeric
        Global horizontal irradiance. [W/m2]

    dhi : numeric
        Diffuse horizontal irradiance. [W/m2]

    dni : numeric
        Direct normal irradiance. [W/m2]

    albedo : numeric
        Surface albedo. [unitless]

    iam_front : numeric, default 1.0
        Incidence angle modifier, the fraction of direct irradiance incident
        on the front surface that is not reflected away. [unitless]

    iam_back : numeric, default 1.0
        Incidence angle modifier, the fraction of direct irradiance incident
        on the back surface that is not reflected away. [unitless]

    bifaciality : numeric, default 0.8
        Ratio of the efficiency of the module's rear surface to the efficiency
        of the front surface. [unitless]

    shade_factor : numeric, default -0.02
        Fraction of back surface irradiance that is blocked by array mounting
        structures. Negative value is a reduction in back irradiance.
        [unitless]

    transmission_factor : numeric, default 0.0
        Fraction of irradiance on the back surface that does not reach the
        module's cells due to module structures. Negative value is a reduction
        in back irradiance. [unitless]

    max_rows : int, default 5
        Maximum number of rows to consider in front and behind the current row.

    npoints : int, default 100
        Number of points used to discretize distance along the ground.

    Returns
    -------
    output : OrderedDict or DataFrame
        Output is a DataFrame when input ghi is a Series. See Notes for
        descriptions of content.

    Notes
    -----
    Input parameters ``height`` and ``pitch`` must have the same unit.

    ``output`` includes:

    - ``poa_global`` : total irradiance reaching the module cells from both
      front and back surfaces. [W/m^2]
    - ``poa_front`` : total irradiance reaching the module cells from the front
      surface. [W/m^2]
    - ``poa_back`` : total irradiance reaching the module cells from the front
      surface. [W/m^2]

    """
    # backside is rotated and flipped relative to front
    backside_tilt, backside_sysaz = _backside(surface_tilt, surface_azimuth)
    # front side POA irradiance
    irrad_front = get_irradiance_poa(
        surface_tilt, surface_azimuth, solar_zenith, solar_azimuth,
        gcr, height, pitch, ghi, dhi, dni, albedo, iam_front)
    # back side POA irradiance
    irrad_back = get_irradiance_poa(
        backside_tilt, backside_sysaz, solar_zenith, solar_azimuth,
        gcr, height, pitch, ghi, dhi, dni, albedo, iam_back)
    if isinstance(ghi, pd.Series):
        irrad_front = irrad_front.rename(
            columns={'poa_global': 'poa_front',
                     'poa_diffuse': 'poa_front_diffuse',
                     'poa_direct': 'poa_front_direct'})
        irrad_back = irrad_back.rename(
            columns={'poa_global': 'poa_back',
                     'poa_diffuse': 'poa_back_diffuse',
                     'poa_direct': 'poa_back_direct'})
        output = pd.concat([irrad_front, irrad_back], axis=1)
    else:
        old = ['poa_global', 'poa_diffuse', 'poa_direct']
        front = ['poa_front', 'poa_front_diffuse', 'poa_front_direct']
        back = ['poa_back', 'poa_back_diffuse', 'poa_back_direct']
        for old_key, new_key in zip(old, front):
            irrad_front[new_key] = irrad_front.pop(old_key)
        for old_key, new_key in zip(old, back):
            irrad_back[new_key] = irrad_back.pop(old_key)
        irrad_front.update(irrad_back)
        output = irrad_front
    effects = (1 + shade_factor) * (1 + transmission_factor)
    output['poa_global'] = output['poa_front'] + \
        output['poa_back'] * bifaciality * effects
    return output


def _backside(tilt, system_azimuth):
    backside_tilt = 180. - tilt
    backside_sysaz = (180. + system_azimuth) % 360.
    return backside_tilt, backside_sysaz
