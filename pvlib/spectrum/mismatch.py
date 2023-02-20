"""
The ``mismatch`` module provides functions for spectral mismatch calculations.
"""

import pvlib
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import os

from warnings import warn


def get_example_spectral_response(wavelength=None):
    '''
    Generate a generic smooth spectral response (SR) for tests and experiments.

    Parameters
    ----------
    wavelength: 1-D sequence of numeric, optional
        Wavelengths at which spectral response values are generated.
        By default ``wavelength`` is from 280 to 1200 in 5 nm intervals. [nm]

    Returns
    -------
    spectral_response : pandas.Series
        The relative spectral response indexed by ``wavelength`` in nm. [-]

    Notes
    -----
    This spectral response is based on measurements taken on a c-Si cell.
    A small number of points near the measured curve are used to define
    a cubic spline having no undue oscillations, as shown in [1]_.  The spline
    can be interpolated at arbitrary wavelengths to produce a continuous,
    smooth curve , which makes it suitable for experimenting with spectral
    data of different resolutions.

    References
    ----------
    .. [1] Driesse, Anton, and Stein, Joshua. "Global Normal Spectral
       Irradiance in Albuquerque: a One-Year Open Dataset for PV Research".
       United States 2020. :doi:`10.2172/1814068`.
    '''
    # Contributed by Anton Driesse (@adriesse), PV Performance Labs. Aug. 2022

    SR_DATA = np.array([[ 290, 0.00],
                        [ 350, 0.27],
                        [ 400, 0.37],
                        [ 500, 0.52],
                        [ 650, 0.71],
                        [ 800, 0.88],
                        [ 900, 0.97],
                        [ 950, 1.00],
                        [1000, 0.93],
                        [1050, 0.58],
                        [1100, 0.21],
                        [1150, 0.05],
                        [1190, 0.00]]).transpose()

    if wavelength is None:
        resolution = 5.0
        wavelength = np.arange(280, 1200 + resolution, resolution)

    interpolator = interp1d(SR_DATA[0], SR_DATA[1],
                            kind='cubic',
                            bounds_error=False,
                            fill_value=0.0,
                            copy=False,
                            assume_sorted=True)

    sr = pd.Series(data=interpolator(wavelength), index=wavelength)

    sr.index.name = 'wavelength'
    sr.name = 'spectral_response'

    return sr


def get_am15g(wavelength=None):
    '''
    Read the ASTM G173-03 AM1.5 global spectrum on a 37-degree tilted surface,
    optionally interpolated to the specified wavelength(s).

    Global (tilted) irradiance includes direct and diffuse irradiance from sky
    and ground reflections, and is more formally called hemispherical
    irradiance (on a tilted surface).  In the context of photovoltaic systems
    the irradiance on a flat receiver is frequently called plane-of-array (POA)
    irradiance.

    Parameters
    ----------
    wavelength: 1-D sequence of numeric, optional
        Wavelengths at which the spectrum is interpolated.
        By default the 2002 wavelengths of the standard are returned. [nm]

    Returns
    -------
    am15g: pandas.Series
        The AM1.5g standard spectrum indexed by ``wavelength``. [(W/m^2)/nm]

    Notes
    -----
    If ``wavelength`` is specified this function uses linear interpolation.

    If the values in ``wavelength`` are too widely spaced, the integral of the
    spectrum may deviate from the standard value of 1000.37 W/m^2.

    The values in the data file provided with pvlib-python are copied from an
    Excel file distributed by NREL, which is found here:
    https://www.nrel.gov/grid/solar-resource/assets/data/astmg173.xls

    More information about reference spectra is found here:
    https://www.nrel.gov/grid/solar-resource/spectra-am1.5.html

    References
    ----------
    .. [1] ASTM "G173-03 Standard Tables for Reference Solar Spectral
        Irradiances: Direct Normal and Hemispherical on 37° Tilted Surface."
    '''
    # Contributed by Anton Driesse (@adriesse), PV Performance Labs. Aug. 2022

    pvlib_path = pvlib.__path__[0]
    filepath = os.path.join(pvlib_path, 'data', 'astm_g173_am15g.csv')

    am15g = pd.read_csv(filepath, index_col=0).squeeze()

    if wavelength is not None:
        interpolator = interp1d(am15g.index, am15g,
                                kind='linear',
                                bounds_error=False,
                                fill_value=0.0,
                                copy=False,
                                assume_sorted=True)

        am15g = pd.Series(data=interpolator(wavelength), index=wavelength)

    am15g.index.name = 'wavelength'
    am15g.name = 'am15g'

    return am15g


def calc_spectral_mismatch_field(sr, e_sun, e_ref=None):
    """
    Calculate spectral mismatch between a test device and broadband reference
    device under specified solar spectral irradiance conditions.

    Parameters
    ----------
    sr: pandas.Series
        The relative spectral response of one (photovoltaic) test device.
        The index of the Series must contain wavelength values in nm. [-]

    e_sun: pandas.DataFrame or pandas.Series
        One or more measured solar irradiance spectra in a pandas.DataFrame
        having wavelength in nm as column index.  A single spectrum may be
        be given as a pandas.Series having wavelength in nm as index.
        [(W/m^2)/nm]

    e_ref: pandas.Series, optional
        The reference spectrum to use for the mismatch calculation.
        The index of the Series must contain wavelength values in nm.
        The default is the ASTM G173-03 global tilted spectrum. [(W/m^2)/nm]

    Returns
    -------
    smm: pandas.Series or float if a single measured spectrum is provided. [-]

    Notes
    -----
    Measured solar spectral irradiance usually covers a wavelength range
    that is smaller than the range considered as broadband irradiance.
    The infrared limit for the former typically lies around 1100 or 1600 nm,
    whereas the latter extends to around 2800 or 4000 nm.  To avoid imbalance
    between the magnitudes of the integrated spectra (the broadband values)
    this function truncates the reference spectrum to the same range as the
    measured (or simulated) field spectra. The assumption implicit in this
    truncation is that the energy in the unmeasured wavelength range
    is the same fraction of the broadband energy for both the measured
    spectra and the reference spectrum.

    If the default reference spectrum is used it is linearly interpolated
    to the wavelengths of the measured spectrum, but if a reference spectrum
    is provided via the parameter ``e_ref`` it is used without change. This
    makes it possible to avoid interpolation, or to use a different method of
    interpolation, or to avoid truncation.

    The spectral response is linearly interpolated to the wavelengths of each
    spectrum with which is it multiplied internally (``e_sun`` and ``e_ref``).
    If the wavelengths of the spectral response already match one or both
    of these spectra interpolation has no effect; therefore, another type of
    interpolation could be used to process ``sr`` before calling this function.

    The standards describing mismatch calculations focus on indoor laboratory
    applications, but are applicable to outdoor performance as well.
    The 2016 version of ASTM E973 [1]_ is somewhat more difficult to
    read than the 2010 version [2]_ because it includes adjustments for
    the temperature dependency of spectral response, which led to a
    formulation using quantum efficiency (QE).
    IEC 60904-7 is clearer and also discusses the use of a broadband
    reference device. [3]_

    References
    ----------
    .. [1] ASTM "E973-16 Standard Test Method for Determination of the
       Spectral Mismatch Parameter Between a Photovoltaic Device and a
       Photovoltaic Reference Cell" :doi:`10.1520/E0973-16R20`
    .. [2] ASTM "E973-10 Standard Test Method for Determination of the
       Spectral Mismatch Parameter Between a Photovoltaic Device and a
       Photovoltaic Reference Cell" :doi:`10.1520/E0973-10`
    .. [3] IEC 60904-7 "Computation of the spectral mismatch correction
       for measurements of photovoltaic devices"
    """
    # Contributed by Anton Driesse (@adriesse), PV Performance Labs. Aug. 2022

    # get the reference spectrum at wavelengths matching the measured spectra
    if e_ref is None:
        e_ref = get_am15g(wavelength=e_sun.T.index)

    # interpolate the sr at the wavelengths of the spectra
    # reference spectrum wavelengths may differ if e_ref is from caller
    sr_sun = np.interp(e_sun.T.index, sr.index, sr, left=0.0, right=0.0)
    sr_ref = np.interp(e_ref.T.index, sr.index, sr, left=0.0, right=0.0)

    # a helper function to make usable fraction calculations more readable
    def integrate(e):
        return np.trapz(e, x=e.T.index, axis=-1)

    # calculate usable fractions
    uf_sun = integrate(e_sun * sr_sun) / integrate(e_sun)
    uf_ref = integrate(e_ref * sr_ref) / integrate(e_ref)

    # mismatch is the ratio or quotient of the usable fractions
    smm = uf_sun / uf_ref

    if isinstance(e_sun, pd.DataFrame):
        smm = pd.Series(smm, index=e_sun.index)

    return smm


def first_solar(pw, airmass_absolute, module_type=None, coefficients=None,
                min_pw=0.1, max_pw=8):
    r"""
    Spectral mismatch modifier based on precipitable water and absolute
    (pressure-adjusted) airmass.

    Estimates a spectral mismatch modifier :math:`M` representing the effect on
    module short circuit current of variation in the spectral
    irradiance. :math:`M`  is estimated from absolute (pressure currected) air
    mass, :math:`AM_a`, and precipitable water, :math:`Pw`, using the following
    function:

    .. math::

        M = c_1 + c_2 AM_a  + c_3 Pw  + c_4 AM_a^{0.5}
            + c_5 Pw^{0.5} + c_6 \frac{AM_a} {Pw^{0.5}}

    Default coefficients are determined for several cell types with
    known quantum efficiency curves, by using the Simple Model of the
    Atmospheric Radiative Transfer of Sunshine (SMARTS) [1]_. Using
    SMARTS, spectrums are simulated with all combinations of AMa and
    Pw where:

       * :math:`0.5 \textrm{cm} <= Pw <= 5 \textrm{cm}`
       * :math:`1.0 <= AM_a <= 5.0`
       * Spectral range is limited to that of CMP11 (280 nm to 2800 nm)
       * spectrum simulated on a plane normal to the sun
       * All other parameters fixed at G173 standard

    From these simulated spectra, M is calculated using the known
    quantum efficiency curves. Multiple linear regression is then
    applied to fit Eq. 1 to determine the coefficients for each module.

    Based on the PVLIB Matlab function ``pvl_FSspeccorr`` by Mitchell
    Lee and Alex Panchula of First Solar, 2016 [2]_.

    Parameters
    ----------
    pw : array-like
        atmospheric precipitable water. [cm]

    airmass_absolute : array-like
        absolute (pressure-adjusted) airmass. [unitless]

    min_pw : float, default 0.1
        minimum atmospheric precipitable water. Any pw value lower than min_pw
        is set to min_pw to avoid model divergence. [cm]

    max_pw : float, default 8
        maximum atmospheric precipitable water. Any pw value higher than max_pw
        is set to NaN to avoid model divergence. [cm]

    module_type : None or string, default None
        a string specifying a cell type. Values of 'cdte', 'monosi', 'xsi',
        'multisi', and 'polysi' (can be lower or upper case). If provided,
        module_type selects default coefficients for the following modules:

            * 'cdte' - First Solar Series 4-2 CdTe module.
            * 'monosi', 'xsi' - First Solar TetraSun module.
            * 'multisi', 'polysi' - anonymous multi-crystalline silicon module.
            * 'cigs' - anonymous copper indium gallium selenide module.
            * 'asi' - anonymous amorphous silicon module.

        The module used to calculate the spectral correction
        coefficients corresponds to the Multi-crystalline silicon
        Manufacturer 2 Model C from [3]_. The spectral response (SR) of CIGS
        and a-Si modules used to derive coefficients can be found in [4]_

    coefficients : None or array-like, default None
        Allows for entry of user-defined spectral correction
        coefficients. Coefficients must be of length 6. Derivation of
        coefficients requires use of SMARTS and PV module quantum
        efficiency curve. Useful for modeling PV module types which are
        not included as defaults, or to fine tune the spectral
        correction to a particular PV module. Note that the parameters for
        modules with very similar quantum efficiency should be similar,
        in most cases limiting the need for module specific coefficients.

    Returns
    -------
    modifier: array-like
        spectral mismatch factor (unitless) which is can be multiplied
        with broadband irradiance reaching a module's cells to estimate
        effective irradiance, i.e., the irradiance that is converted to
        electrical current.

    References
    ----------
    .. [1] Gueymard, Christian. SMARTS2: a simple model of the atmospheric
       radiative transfer of sunshine: algorithms and performance
       assessment. Cocoa, FL: Florida Solar Energy Center, 1995.
    .. [2] Lee, Mitchell, and Panchula, Alex. "Spectral Correction for
       Photovoltaic Module Performance Based on Air Mass and Precipitable
       Water." IEEE Photovoltaic Specialists Conference, Portland, 2016
    .. [3] Marion, William F., et al. User's Manual for Data for Validating
       Models for PV Module Performance. National Renewable Energy
       Laboratory, 2014. http://www.nrel.gov/docs/fy14osti/61610.pdf
    .. [4] Schweiger, M. and Hermann, W, Influence of Spectral Effects
       on Energy Yield of Different PV Modules: Comparison of Pwat and
       MMF Approach, TUV Rheinland Energy GmbH report 21237296.003,
       January 2017
    """

    # --- Screen Input Data ---

    # *** Pw ***
    # Replace Pw Values below 0.1 cm with 0.1 cm to prevent model from
    # diverging"
    pw = np.atleast_1d(pw)
    pw = pw.astype('float64')
    if np.min(pw) < min_pw:
        pw = np.maximum(pw, min_pw)
        warn(f'Exceptionally low pw values replaced with {min_pw} cm to '
             'prevent model divergence')

    # Warn user about Pw data that is exceptionally high
    if np.max(pw) > max_pw:
        pw[pw > max_pw] = np.nan
        warn('Exceptionally high pw values replaced by np.nan: '
             'check input data.')

    # *** AMa ***
    # Replace Extremely High AM with AM 10 to prevent model divergence
    # AM > 10 will only occur very close to sunset
    if np.max(airmass_absolute) > 10:
        airmass_absolute = np.minimum(airmass_absolute, 10)

    # Warn user about AMa data that is exceptionally low
    if np.min(airmass_absolute) < 0.58:
        warn('Exceptionally low air mass: ' +
             'model not intended for extra-terrestrial use')
        # pvl_absoluteairmass(1,pvl_alt2pres(4340)) = 0.58 Elevation of
        # Mina Pirquita, Argentian = 4340 m. Highest elevation city with
        # population over 50,000.

    _coefficients = {}
    _coefficients['cdte'] = (
        0.86273, -0.038948, -0.012506, 0.098871, 0.084658, -0.0042948)
    _coefficients['monosi'] = (
        0.85914, -0.020880, -0.0058853, 0.12029, 0.026814, -0.0017810)
    _coefficients['xsi'] = _coefficients['monosi']
    _coefficients['polysi'] = (
        0.84090, -0.027539, -0.0079224, 0.13570, 0.038024, -0.0021218)
    _coefficients['multisi'] = _coefficients['polysi']
    _coefficients['cigs'] = (
        0.85252, -0.022314, -0.0047216, 0.13666, 0.013342, -0.0008945)
    _coefficients['asi'] = (
        1.12094, -0.047620, -0.0083627, -0.10443, 0.098382, -0.0033818)

    if module_type is not None and coefficients is None:
        coefficients = _coefficients[module_type.lower()]
    elif module_type is None and coefficients is not None:
        pass
    elif module_type is None and coefficients is None:
        raise TypeError('No valid input provided, both module_type and ' +
                        'coefficients are None')
    else:
        raise TypeError('Cannot resolve input, must supply only one of ' +
                        'module_type and coefficients')

    # Evaluate Spectral Shift
    coeff = coefficients
    ama = airmass_absolute
    modifier = (
        coeff[0] + coeff[1]*ama + coeff[2]*pw + coeff[3]*np.sqrt(ama) +
        coeff[4]*np.sqrt(pw) + coeff[5]*ama/np.sqrt(pw))

    return modifier


def sapm(airmass_absolute, module):
    """
    Calculates the SAPM spectral loss coefficient, F1.

    Parameters
    ----------
    airmass_absolute : numeric
        Absolute airmass

    module : dict-like
        A dict, Series, or DataFrame defining the SAPM performance
        parameters. See the :py:func:`sapm` notes section for more
        details.

    Returns
    -------
    F1 : numeric
        The SAPM spectral loss coefficient.

    Notes
    -----
    nan airmass values will result in 0 output.
    """

    am_coeff = [module['A4'], module['A3'], module['A2'], module['A1'],
                module['A0']]

    spectral_loss = np.polyval(am_coeff, airmass_absolute)

    spectral_loss = np.where(np.isnan(spectral_loss), 0, spectral_loss)

    spectral_loss = np.maximum(0, spectral_loss)

    if isinstance(airmass_absolute, pd.Series):
        spectral_loss = pd.Series(spectral_loss, airmass_absolute.index)

    return spectral_loss
