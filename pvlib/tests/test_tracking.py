import numpy as np
from numpy import nan
import pandas as pd

import pytest
from conftest import assert_frame_equal
from numpy.testing import assert_allclose

import pvlib
from pvlib.location import Location
from pvlib import tracking
from conftest import DATA_DIR

SINGLEAXIS_COL_ORDER = ['tracker_theta', 'aoi',
                        'surface_azimuth', 'surface_tilt']


def test_solar_noon():
    index = pd.date_range(start='20180701T1200', freq='1s', periods=1)
    apparent_zenith = pd.Series([10], index=index)
    apparent_azimuth = pd.Series([180], index=index)
    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'tracker_theta': 0, 'aoi': 10,
                           'surface_azimuth': 90, 'surface_tilt': 0},
                          index=index, dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_scalars():
    apparent_zenith = 10
    apparent_azimuth = 180
    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)
    assert isinstance(tracker_data, dict)
    expect = {'tracker_theta': 0, 'aoi': 10, 'surface_azimuth': 90,
              'surface_tilt': 0}
    for k, v in expect.items():
        assert_allclose(tracker_data[k], v)


def test_arrays():
    apparent_zenith = np.array([10])
    apparent_azimuth = np.array([180])
    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)
    assert isinstance(tracker_data, dict)
    expect = {'tracker_theta': 0, 'aoi': 10, 'surface_azimuth': 90,
              'surface_tilt': 0}
    for k, v in expect.items():
        assert_allclose(tracker_data[k], v)


def test_nans():
    apparent_zenith = np.array([10, np.nan, 10])
    apparent_azimuth = np.array([180, 180, np.nan])
    with np.errstate(invalid='ignore'):
        tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                           axis_tilt=0, axis_azimuth=0,
                                           max_angle=90, backtrack=True,
                                           gcr=2.0/7.0)
    expect = {'tracker_theta': np.array([0, nan, nan]),
              'aoi': np.array([10, nan, nan]),
              'surface_azimuth': np.array([90, nan, nan]),
              'surface_tilt': np.array([0, nan, nan])}
    for k, v in expect.items():
        assert_allclose(tracker_data[k], v)

    # repeat with Series because nans can differ
    apparent_zenith = pd.Series(apparent_zenith)
    apparent_azimuth = pd.Series(apparent_azimuth)
    with np.errstate(invalid='ignore'):
        tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                           axis_tilt=0, axis_azimuth=0,
                                           max_angle=90, backtrack=True,
                                           gcr=2.0/7.0)
    expect = pd.DataFrame(np.array(
        [[ 0., 10., 90.,  0.],
         [nan, nan, nan, nan],
         [nan, nan, nan, nan]]),
        columns=['tracker_theta', 'aoi', 'surface_azimuth', 'surface_tilt'])
    assert_frame_equal(tracker_data, expect)


def test_arrays_multi():
    apparent_zenith = np.array([[10, 10], [10, 10]])
    apparent_azimuth = np.array([[180, 180], [180, 180]])
    # singleaxis should fail for num dim > 1
    with pytest.raises(ValueError):
        tracking.singleaxis(apparent_zenith, apparent_azimuth,
                            axis_tilt=0, axis_azimuth=0,
                            max_angle=90, backtrack=True,
                            gcr=2.0/7.0)
    # uncomment if we ever get singleaxis to support num dim > 1 arrays
    # assert isinstance(tracker_data, dict)
    # expect = {'tracker_theta': np.full_like(apparent_zenith, 0),
    #           'aoi': np.full_like(apparent_zenith, 10),
    #           'surface_azimuth': np.full_like(apparent_zenith, 90),
    #           'surface_tilt': np.full_like(apparent_zenith, 0)}
    # for k, v in expect.items():
    #     assert_allclose(tracker_data[k], v)


def test_azimuth_north_south():
    apparent_zenith = pd.Series([60])
    apparent_azimuth = pd.Series([90])

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=180,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'tracker_theta': -60, 'aoi': 0,
                           'surface_azimuth': 90, 'surface_tilt': 60},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect['tracker_theta'] *= -1

    assert_frame_equal(expect, tracker_data)


def test_max_angle():
    apparent_zenith = pd.Series([60])
    apparent_azimuth = pd.Series([90])
    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=45, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 15, 'surface_azimuth': 90,
                           'surface_tilt': 45, 'tracker_theta': 45},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_backtrack():
    apparent_zenith = pd.Series([80])
    apparent_azimuth = pd.Series([90])

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=False,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 0, 'surface_azimuth': 90,
                           'surface_tilt': 80, 'tracker_theta': 80},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 52.5716, 'surface_azimuth': 90,
                           'surface_tilt': 27.42833, 'tracker_theta': 27.4283},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_axis_tilt():
    apparent_zenith = pd.Series([30])
    apparent_azimuth = pd.Series([135])

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=30, axis_azimuth=180,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 7.286245, 'surface_azimuth': 142.65730,
                           'surface_tilt': 35.98741,
                           'tracker_theta': -20.88121},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=30, axis_azimuth=0,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 47.6632, 'surface_azimuth': 50.96969,
                           'surface_tilt': 42.5152, 'tracker_theta': 31.6655},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_axis_azimuth():
    apparent_zenith = pd.Series([30])
    apparent_azimuth = pd.Series([90])

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=90,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 30, 'surface_azimuth': 180,
                           'surface_tilt': 0, 'tracker_theta': 0},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)

    apparent_zenith = pd.Series([30])
    apparent_azimuth = pd.Series([180])

    tracker_data = tracking.singleaxis(apparent_zenith, apparent_azimuth,
                                       axis_tilt=0, axis_azimuth=90,
                                       max_angle=90, backtrack=True,
                                       gcr=2.0/7.0)

    expect = pd.DataFrame({'aoi': 0, 'surface_azimuth': 180,
                           'surface_tilt': 30, 'tracker_theta': 30},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_horizon_flat():
    # GH 569
    solar_azimuth = np.array([0, 180, 359])
    solar_zenith = np.array([100, 45, 100])
    solar_azimuth = pd.Series(solar_azimuth)
    solar_zenith = pd.Series(solar_zenith)
    # depending on platform and numpy versions this will generate
    # RuntimeWarning: invalid value encountered in > < >=
    out = tracking.singleaxis(solar_zenith, solar_azimuth, axis_tilt=0,
                              axis_azimuth=180, backtrack=False, max_angle=180)
    expected = pd.DataFrame(np.array(
        [[ nan,  nan,  nan,  nan],
         [  0.,  45., 270.,   0.],
         [ nan,  nan,  nan,  nan]]),
        columns=['tracker_theta', 'aoi', 'surface_azimuth', 'surface_tilt'])
    assert_frame_equal(out, expected)


def test_horizon_tilted():
    # GH 569
    solar_azimuth = np.array([0, 180, 359])
    solar_zenith = np.full_like(solar_azimuth, 45)
    solar_azimuth = pd.Series(solar_azimuth)
    solar_zenith = pd.Series(solar_zenith)
    out = tracking.singleaxis(solar_zenith, solar_azimuth, axis_tilt=90,
                              axis_azimuth=180, backtrack=False, max_angle=180)
    expected = pd.DataFrame(np.array(
        [[ 180.,  45.,   0.,  90.],
         [   0.,  45., 180.,  90.],
         [ 179.,  45., 359.,  90.]]),
        columns=['tracker_theta', 'aoi', 'surface_azimuth', 'surface_tilt'])
    assert_frame_equal(out, expected)


def test_low_sun_angles():
    # GH 656
    result = tracking.singleaxis(
        apparent_zenith=80, apparent_azimuth=338, axis_tilt=30,
        axis_azimuth=180, max_angle=60, backtrack=True, gcr=0.35)
    expected = {
        'tracker_theta': np.array([-50.31051385]),
        'aoi': np.array([61.35300178]),
        'surface_azimuth': np.array([112.53615425]),
        'surface_tilt': np.array([56.42233095])}
    for k, v in result.items():
        assert_allclose(expected[k], v)


def test_SingleAxisTracker_creation():
    system = tracking.SingleAxisTracker(max_angle=45,
                                        gcr=.25,
                                        module='blah',
                                        inverter='blarg')

    assert system.max_angle == 45
    assert system.gcr == .25
    assert system.module == 'blah'
    assert system.inverter == 'blarg'


def test_SingleAxisTracker_tracking():
    system = tracking.SingleAxisTracker(max_angle=90, axis_tilt=30,
                                        axis_azimuth=180, gcr=2.0/7.0,
                                        backtrack=True)

    apparent_zenith = pd.Series([30])
    apparent_azimuth = pd.Series([135])

    tracker_data = system.singleaxis(apparent_zenith, apparent_azimuth)

    expect = pd.DataFrame({'aoi': 7.286245, 'surface_azimuth': 142.65730,
                           'surface_tilt': 35.98741,
                           'tracker_theta': -20.88121},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)

    # results calculated using PVsyst
    pvsyst_solar_azimuth = 7.1609
    pvsyst_solar_height = 27.315
    pvsyst_axis_tilt = 20.
    pvsyst_axis_azimuth = 20.
    pvsyst_system = tracking.SingleAxisTracker(
        max_angle=60., axis_tilt=pvsyst_axis_tilt,
        axis_azimuth=180+pvsyst_axis_azimuth, backtrack=False)
    # the definition of azimuth is different from PYsyst
    apparent_azimuth = pd.Series([180+pvsyst_solar_azimuth])
    apparent_zenith = pd.Series([90-pvsyst_solar_height])
    tracker_data = pvsyst_system.singleaxis(apparent_zenith, apparent_azimuth)
    expect = pd.DataFrame({'aoi': 41.07852, 'surface_azimuth': 180-18.432,
                           'surface_tilt': 24.92122,
                           'tracker_theta': -15.18391},
                          index=[0], dtype=np.float64)
    expect = expect[SINGLEAXIS_COL_ORDER]

    assert_frame_equal(expect, tracker_data)


def test_LocalizedSingleAxisTracker_creation():
    localized_system = tracking.LocalizedSingleAxisTracker(latitude=32,
                                                           longitude=-111,
                                                           module='blah',
                                                           inverter='blarg')

    assert localized_system.module == 'blah'
    assert localized_system.inverter == 'blarg'
    assert localized_system.latitude == 32
    assert localized_system.longitude == -111


def test_SingleAxisTracker_localize():
    system = tracking.SingleAxisTracker(max_angle=45, gcr=.25,
                                        module='blah', inverter='blarg')

    localized_system = system.localize(latitude=32, longitude=-111)

    assert localized_system.module == 'blah'
    assert localized_system.inverter == 'blarg'
    assert localized_system.latitude == 32
    assert localized_system.longitude == -111


def test_SingleAxisTracker_localize_location():
    system = tracking.SingleAxisTracker(max_angle=45, gcr=.25,
                                        module='blah', inverter='blarg')
    location = Location(latitude=32, longitude=-111)
    localized_system = system.localize(location=location)

    assert localized_system.module == 'blah'
    assert localized_system.inverter == 'blarg'
    assert localized_system.latitude == 32
    assert localized_system.longitude == -111


# see test_irradiance for more thorough testing
def test_get_aoi():
    system = tracking.SingleAxisTracker(max_angle=90, axis_tilt=30,
                                        axis_azimuth=180, gcr=2.0/7.0,
                                        backtrack=True)
    surface_tilt = np.array([30, 0])
    surface_azimuth = np.array([90, 270])
    solar_zenith = np.array([70, 10])
    solar_azimuth = np.array([100, 180])
    out = system.get_aoi(surface_tilt, surface_azimuth,
                         solar_zenith, solar_azimuth)
    expected = np.array([40.632115, 10.])
    assert_allclose(out, expected, atol=0.000001)


def test_get_irradiance():
    system = tracking.SingleAxisTracker(max_angle=90, axis_tilt=30,
                                        axis_azimuth=180, gcr=2.0/7.0,
                                        backtrack=True)
    times = pd.date_range(start='20160101 1200-0700',
                          end='20160101 1800-0700', freq='6H')
    # latitude=32, longitude=-111
    solar_position = pd.DataFrame(np.array(
        [[55.36421554,  55.38851771,  34.63578446,  34.61148229,
          172.32003763,  -3.44516534],
         [96.50000401,  96.50000401,  -6.50000401,  -6.50000401,
          246.91581654,  -3.56292888]]),
        columns=['apparent_zenith', 'zenith', 'apparent_elevation',
                 'elevation', 'azimuth', 'equation_of_time'],
        index=times)
    irrads = pd.DataFrame({'dni': [900, 0], 'ghi': [600, 0], 'dhi': [100, 0]},
                          index=times)
    solar_zenith = solar_position['apparent_zenith']
    solar_azimuth = solar_position['azimuth']

    # invalid warnings already generated in horizon test above,
    # no need to clutter test output here
    with np.errstate(invalid='ignore'):
        tracker_data = system.singleaxis(solar_zenith, solar_azimuth)

    # some invalid values in irradiance.py. not our problem here
    with np.errstate(invalid='ignore'):
        irradiance = system.get_irradiance(tracker_data['surface_tilt'],
                                           tracker_data['surface_azimuth'],
                                           solar_zenith,
                                           solar_azimuth,
                                           irrads['dni'],
                                           irrads['ghi'],
                                           irrads['dhi'])

    expected = pd.DataFrame(data=np.array(
        [[961.80070,   815.94490,   145.85580,   135.32820, 10.52757492],
         [nan, nan, nan, nan, nan]]),
                            columns=['poa_global', 'poa_direct',
                                     'poa_diffuse', 'poa_sky_diffuse',
                                     'poa_ground_diffuse'],
                            index=times)

    assert_frame_equal(irradiance, expected, check_less_precise=2)


def test_SingleAxisTracker___repr__():
    system = tracking.SingleAxisTracker(
        max_angle=45, gcr=.25, module='blah', inverter='blarg',
        temperature_model_parameters={'a': -3.56})
    expected = """SingleAxisTracker:
  axis_tilt: 0
  axis_azimuth: 0
  max_angle: 45
  backtrack: True
  gcr: 0.25
  name: None
  surface_tilt: None
  surface_azimuth: None
  module: blah
  inverter: blarg
  albedo: 0.25
  racking_model: None
  module_type: None
  temperature_model_parameters: {'a': -3.56}"""
    assert system.__repr__() == expected


def test_LocalizedSingleAxisTracker___repr__():
    localized_system = tracking.LocalizedSingleAxisTracker(
        latitude=32, longitude=-111, module='blah', inverter='blarg',
        gcr=0.25, temperature_model_parameters={'a': -3.56})
    # apparently the repr order is different for LocalizedSingleAxisTracker
    # than for LocalizedPVSystem. maybe a MRO thing.
    expected = """LocalizedSingleAxisTracker:
  axis_tilt: 0
  axis_azimuth: 0
  max_angle: 90
  backtrack: True
  gcr: 0.25
  name: None
  surface_tilt: None
  surface_azimuth: None
  module: blah
  inverter: blarg
  albedo: 0.25
  racking_model: None
  module_type: None
  temperature_model_parameters: {'a': -3.56}
  latitude: 32
  longitude: -111
  altitude: 0
  tz: UTC"""

    assert localized_system.__repr__() == expected


def test_calc_axis_tilt():
    # expected values
    expected_axis_tilt = 2.239  # [degrees]
    expected_side_slope = 9.86649274360294  # [degrees]
    expected = DATA_DIR / 'singleaxis_tracker_wslope.csv'
    expected = pd.read_csv(expected, index_col='timestamp', parse_dates=True)
    # solar positions
    starttime = '2017-01-01T00:30:00-0300'
    stoptime = '2017-12-31T23:59:59-0300'
    lat, lon = -27.597300, -48.549610
    times = pd.DatetimeIndex(pd.date_range(starttime, stoptime, freq='H'))
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
    # singleaxis tracker w/slope data
    system_plane = (77.34, 10.1149)
    axis_azimuth = 0.0
    max_angle = 75.0
    # Note: GCR is relative to horizontal distance between rows
    gcr = 0.33292759  # GCR = length / horizontal_pitch = 1.64 / 5 / cos(9.86)
    # calculate tracker axis zenith
    axis_tilt = tracking.calc_tracker_axis_tilt(
        *system_plane, axis_azimuth=axis_azimuth)
    assert np.isclose(axis_tilt, expected_axis_tilt)
    # calculate side slope and relative rotation
    side_slope = tracking.calc_system_tracker_side_slope(
        axis_azimuth, axis_tilt, *system_plane)
    assert np.isclose(side_slope, expected_side_slope)
    sat = tracking.singleaxis(
        solpos.apparent_zenith, solpos.azimuth, axis_tilt, axis_azimuth,
        max_angle, backtrack=True, gcr=gcr, side_slope=side_slope)
    assert np.allclose(
        sat['tracker_theta'], expected['tracker_theta'], equal_nan=True)
    assert np.allclose(sat['aoi'], expected['aoi'], equal_nan=True)
    assert np.allclose(
        sat['surface_azimuth'], expected['surface_azimuth'], equal_nan=True)
    assert np.allclose(
        sat['surface_tilt'], expected['surface_tilt'], equal_nan=True)


def test_slope_aware_backtracking():
    """
    Test validation data set from https://www.nrel.gov/docs/fy20osti/76626.pdf
    """
    expected_data = np.array(
        [('2019-01-01T08:00-0500',  2.404287, 122.79177, -84.440, -10.899),
         ('2019-01-01T09:00-0500', 11.263058, 133.288729, -72.604, -25.747),
         ('2019-01-01T10:00-0500', 18.733558, 145.285552, -59.861, -59.861),
         ('2019-01-01T11:00-0500', 24.109076, 158.939435, -45.578, -45.578),
         ('2019-01-01T12:00-0500', 26.810735, 173.931802, -28.764, -28.764),
         ('2019-01-01T13:00-0500', 26.482495, 189.371536, -8.475, -8.475),
         ('2019-01-01T14:00-0500', 23.170447, 204.13681, 15.120, 15.120),
         ('2019-01-01T15:00-0500', 17.296785, 217.446538, 39.562, 39.562),
         ('2019-01-01T16:00-0500',  9.461862, 229.102218, 61.587, 32.339),
         ('2019-01-01T17:00-0500',  0.524817, 239.330401, 79.530, 5.490)],
        dtype=[
            ('Time', '<M8[h]'), ('ApparentElevation', '<f8'),
            ('SolarAzimuth', '<f8'), ('TrueTracking', '<f8'),
            ('Backtracking', '<f8')])
    expected_axis_tilt = 9.666
    expected_slope_angle = -2.576
    system_azimuth, system_zenith = 180.0, 10.0
    axis_azimuth = 195.0
    axis_tilt = tracking.calc_tracker_axis_tilt(
        system_azimuth, system_zenith, axis_azimuth)
    assert np.isclose(axis_tilt, expected_axis_tilt, rtol=1e-3, atol=1e-3)
    side_slope = tracking.calc_system_tracker_side_slope(
        axis_azimuth, axis_tilt, system_azimuth, system_zenith)
    assert np.isclose(side_slope, expected_slope_angle, rtol=1e-3, atol=1e-3)
    sat = tracking.singleaxis(
        90.0-expected_data['ApparentElevation'], expected_data['SolarAzimuth'],
        axis_tilt, axis_azimuth, max_angle=90.0, backtrack=True, gcr=0.5,
        side_slope=side_slope)
    np.testing.assert_allclose(
        sat['tracker_theta'], expected_data['Backtracking'],
        rtol=1e-3, atol=1e-3)
