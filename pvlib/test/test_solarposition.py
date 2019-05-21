import calendar
import datetime

import numpy as np
import pandas as pd

from pandas.util.testing import (assert_frame_equal, assert_series_equal,
                                 assert_index_equal)
from numpy.testing import assert_allclose
import pytest

from pvlib._deprecation import pvlibDeprecationWarning
from pvlib.location import Location
from pvlib import solarposition, spa

from conftest import (fail_on_pvlib_version, requires_ephem, needs_pandas_0_17,
                      requires_spa_c, requires_numba)


# setup times and locations to be tested.
times = pd.date_range(start=datetime.datetime(2014,6,24),
                      end=datetime.datetime(2014,6,26), freq='15Min')

tus = Location(32.2, -111, 'US/Arizona', 700) # no DST issues possible
times_localized = times.tz_localize(tus.tz)

tol = 5


@pytest.fixture()
def golden():
    return Location(39.742476, -105.1786, 'America/Denver', 1830.14)


@pytest.fixture()
def golden_mst():
    return Location(39.742476, -105.1786, 'MST', 1830.14)


@pytest.fixture()
def expected_solpos():
    return _expected_solpos_df()


# hack to make tests work without too much modification while avoiding
# pytest 4.0 inability to call features directly
def _expected_solpos_df():
    return pd.DataFrame({'elevation': 39.872046,
                         'apparent_zenith': 50.111622,
                         'azimuth': 194.340241,
                         'apparent_elevation': 39.888378},
                        index=['2003-10-17T12:30:30Z'])


@pytest.fixture()
def expected_solpos_multi():
    return pd.DataFrame({'elevation': [39.872046, 39.505196],
                         'apparent_zenith': [50.111622, 50.478260],
                         'azimuth': [194.340241, 194.311132],
                         'apparent_elevation': [39.888378, 39.521740]},
                        index=[['2003-10-17T12:30:30Z', '2003-10-18T12:30:30Z']])


@pytest.fixture()
def expected_rise_set_spa():
    # for Golden, CO, from NREL SPA website
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2),
                              datetime.datetime(2015, 8, 2),
                              ]).tz_localize('MST')
    sunrise = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 7, 21, 55),
                                datetime.datetime(2015, 8, 2, 5, 0, 27)
                                ]).tz_localize('MST').tolist()
    sunset = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 16, 47, 43),
                               datetime.datetime(2015, 8, 2, 19, 13, 58)
                               ]).tz_localize('MST').tolist()
    transit = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 12, 4, 45),
                                datetime.datetime(2015, 8, 2, 12, 6, 58)
                                ]).tz_localize('MST').tolist()
    return pd.DataFrame({'sunrise': sunrise,
                         'sunset': sunset,
                         'transit': transit},
                        index=times)


@pytest.fixture()
def expected_rise_set_ephem():
    # for Golden, CO, from USNO websites
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 1),
                              datetime.datetime(2015, 1, 2),
                              datetime.datetime(2015, 1, 3),
                              datetime.datetime(2015, 8, 2),
                              ]).tz_localize('MST')
    sunrise = pd.DatetimeIndex([datetime.datetime(2015, 1, 1, 7, 22, 0),
                                datetime.datetime(2015, 1, 2, 7, 22, 0),
                                datetime.datetime(2015, 1, 3, 7, 22, 0),
                                datetime.datetime(2015, 8, 2, 5, 0, 0)
                                ]).tz_localize('MST').tolist()
    sunset = pd.DatetimeIndex([datetime.datetime(2015, 1, 1, 16, 47, 0),
                               datetime.datetime(2015, 1, 2, 16, 48, 0),
                               datetime.datetime(2015, 1, 3, 16, 49, 0),
                               datetime.datetime(2015, 8, 2, 19, 13, 0)
                               ]).tz_localize('MST').tolist()
    transit = pd.DatetimeIndex([datetime.datetime(2015, 1, 1, 12, 4, 0),
                                datetime.datetime(2015, 1, 2, 12, 5, 0),
                                datetime.datetime(2015, 1, 3, 12, 5, 0),
                                datetime.datetime(2015, 8, 2, 12, 7, 0)
                                ]).tz_localize('MST').tolist()
    return pd.DataFrame({'sunrise': sunrise,
                         'sunset': sunset,
                         'transit': transit},
                        index=times)


@fail_on_pvlib_version('0.7')
def test_deprecated_07():
    tt = pd.DatetimeIndex(['2015-01-01 00:00:00']).tz_localize('MST')
    with pytest.warns(pvlibDeprecationWarning):
        solarposition.get_sun_rise_set_transit(tt,
                                               39.7,
                                               -105.2)


# the physical tests are run at the same time as the NREL SPA test.
# pyephem reproduces the NREL result to 2 decimal places.
# this doesn't mean that one code is better than the other.

@requires_spa_c
def test_spa_c_physical(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_c(times, golden_mst.latitude,
                                     golden_mst.longitude,
                                     pressure=82000,
                                     temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_spa_c
def test_spa_c_physical_dst(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_c(times, golden.latitude,
                                     golden.longitude,
                                     pressure=82000,
                                     temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_spa_python_numpy_physical(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_python(times, golden_mst.latitude,
                                          golden_mst.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numpy')
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_spa_python_numpy_physical_dst(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_python(times, golden.latitude,
                                          golden.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numpy')
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_numba
def test_spa_python_numba_physical(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.spa_python(times, golden_mst.latitude,
                                          golden_mst.longitude,
                                          pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numba', numthreads=1)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_numba
def test_spa_python_numba_physical_dst(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.spa_python(times, golden.latitude,
                                          golden.longitude, pressure=82000,
                                          temperature=11, delta_t=67,
                                          atmos_refract=0.5667,
                                          how='numba', numthreads=1)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@needs_pandas_0_17
def test_sun_rise_set_transit_spa(expected_rise_set_spa, golden):
    # solution from NREL SAP web calculator
    south = Location(-35.0, 0.0, tz='UTC')
    times = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 0),
                              datetime.datetime(2004, 12, 4, 0)]
                             ).tz_localize('UTC')
    sunrise = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 7, 8, 15),
                                datetime.datetime(2004, 12, 4, 4, 38, 57)]
                               ).tz_localize('UTC').tolist()
    sunset = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 17, 1, 4),
                               datetime.datetime(2004, 12, 4, 19, 2, 3)]
                              ).tz_localize('UTC').tolist()
    transit = pd.DatetimeIndex([datetime.datetime(1996, 7, 5, 12, 4, 36),
                                datetime.datetime(2004, 12, 4, 11, 50, 22)]
                               ).tz_localize('UTC').tolist()
    frame = pd.DataFrame({'sunrise': sunrise,
                          'sunset': sunset,
                          'transit': transit}, index=times)

    result = solarposition.sun_rise_set_transit_spa(times, south.latitude,
                                                    south.longitude,
                                                    delta_t=65.0)
    result_rounded = pd.DataFrame(index=result.index)
    # need to iterate because to_datetime does not accept 2D data
    # the rounding fails on pandas < 0.17
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('1s')

    assert_frame_equal(frame, result_rounded)

    # test for Golden, CO compare to NREL SPA
    result = solarposition.sun_rise_set_transit_spa(
        expected_rise_set_spa.index, golden.latitude, golden.longitude,
        delta_t=65.0)

    # round to nearest minute
    result_rounded = pd.DataFrame(index=result.index)
    # need to iterate because to_datetime does not accept 2D data
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('s').tz_convert('MST')

    assert_frame_equal(expected_rise_set_spa, result_rounded)


@requires_ephem
def test_sun_rise_set_transit_ephem(expected_rise_set_ephem, golden):
    # test for Golden, CO compare to USNO, using local midnight
    result = solarposition.sun_rise_set_transit_ephem(
        expected_rise_set_ephem.index, golden.latitude, golden.longitude,
        next_or_previous='next', altitude=golden.altitude, pressure=0,
        temperature=11, horizon='-0:34')
    # round to nearest minute
    result_rounded = pd.DataFrame(index=result.index)
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('min').tz_convert('MST')
    assert_frame_equal(expected_rise_set_ephem, result_rounded)

    # test next sunrise/sunset with times
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 3, 0, 0),
                              datetime.datetime(2015, 1, 2, 10, 15, 0),
                              datetime.datetime(2015, 1, 2, 15, 3, 0),
                              datetime.datetime(2015, 1, 2, 21, 6, 7)
                              ]).tz_localize('MST')
    expected = pd.DataFrame(index=times,
                            columns=['sunrise', 'sunset'],
                            dtype='datetime64[ns]')
    expected['sunrise'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'sunrise']])
    expected['sunset'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'sunset']])
    expected['transit'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'transit']])

    result = solarposition.sun_rise_set_transit_ephem(times,
                                                      golden.latitude,
                                                      golden.longitude,
                                                      next_or_previous='next',
                                                      altitude=golden.altitude,
                                                      pressure=0,
                                                      temperature=11,
                                                      horizon='-0:34')
    # round to nearest minute
    result_rounded = pd.DataFrame(index=result.index)
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('min').tz_convert('MST')
    assert_frame_equal(expected, result_rounded)

    # test previous sunrise/sunset with times
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 3, 0, 0),
                              datetime.datetime(2015, 1, 2, 10, 15, 0),
                              datetime.datetime(2015, 1, 3, 3, 0, 0),
                              datetime.datetime(2015, 1, 3, 13, 6, 7)
                              ]).tz_localize('MST')
    expected = pd.DataFrame(index=times,
                            columns=['sunrise', 'sunset'],
                            dtype='datetime64[ns]')
    expected['sunrise'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 1), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunrise'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'sunrise']])
    expected['sunset'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 1), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 1), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunset'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'sunset']])
    expected['transit'] = pd.Series(index=times, data=
       [expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 1), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 1), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 2), 'transit'],
        expected_rise_set_ephem.loc[datetime.datetime(2015, 1, 3), 'transit']])

    result = solarposition.sun_rise_set_transit_ephem(times,
        golden.latitude, golden.longitude, next_or_previous='previous',
        altitude=golden.altitude, pressure=0, temperature=11, horizon='-0:34')
    # round to nearest minute
    result_rounded = pd.DataFrame(index=result.index)
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('min').tz_convert('MST')
    assert_frame_equal(expected, result_rounded)

    # test with different timezone
    times = times.tz_convert('UTC')
    expected = expected.tz_convert('UTC')  # resuse result from previous
    for col, data in expected.iteritems():
        expected[col] = data.dt.tz_convert('UTC')
    result = solarposition.sun_rise_set_transit_ephem(times,
        golden.latitude, golden.longitude, next_or_previous='previous',
        altitude=golden.altitude, pressure=0, temperature=11, horizon='-0:34')
    # round to nearest minute
    result_rounded = pd.DataFrame(index=result.index)
    for col, data in result.iteritems():
        result_rounded[col] = data.dt.round('min').tz_convert(times.tz)
    assert_frame_equal(expected, result_rounded)


@requires_ephem
def test_sun_rise_set_transit_ephem_error(expected_rise_set_ephem, golden):
    with pytest.raises(ValueError):
        solarposition.sun_rise_set_transit_ephem(expected_rise_set_ephem.index,
                                                 golden.latitude,
                                                 golden.longitude,
                                                 next_or_previous='other')
    tz_naive = pd.DatetimeIndex([datetime.datetime(2015, 1, 2, 3, 0, 0)])
    with pytest.raises(ValueError):
        solarposition.sun_rise_set_transit_ephem(tz_naive,
                                                 golden.latitude,
                                                 golden.longitude,
                                                 next_or_previous='next')


@requires_ephem
def test_sun_rise_set_transit_ephem_horizon(golden):
    times = pd.DatetimeIndex([datetime.datetime(2016, 1, 3, 0, 0, 0)
                              ]).tz_localize('MST')
    # center of sun disk
    center = solarposition.sun_rise_set_transit_ephem(times,
        latitude=golden.latitude, longitude=golden.longitude)
    edge = solarposition.sun_rise_set_transit_ephem(times,
        latitude=golden.latitude, longitude=golden.longitude, horizon='-0:34')
    result_rounded = (edge['sunrise'] - center['sunrise']).dt.round('min')

    sunrise_delta = datetime.datetime(2016, 1, 3, 7, 17, 11) - \
        datetime.datetime(2016, 1, 3, 7, 21, 33)
    expected = pd.Series(index=times,
                         data=sunrise_delta,
                         name='sunrise').dt.round('min')
    assert_series_equal(expected, result_rounded)


@requires_ephem
def test_pyephem_physical(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.pyephem(times, golden_mst.latitude,
                                       golden_mst.longitude, pressure=82000,
                                       temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos.round(2),
                       ephem_data[expected_solpos.columns].round(2))


@requires_ephem
def test_pyephem_physical_dst(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30), periods=1,
                          freq='D', tz=golden.tz)
    ephem_data = solarposition.pyephem(times, golden.latitude,
                                       golden.longitude, pressure=82000,
                                       temperature=11)
    expected_solpos.index = times
    assert_frame_equal(expected_solpos.round(2),
                       ephem_data[expected_solpos.columns].round(2))


@requires_ephem
def test_calc_time():
    import pytz
    import math
    # validation from USNO solar position calculator online

    epoch = datetime.datetime(1970,1,1)
    epoch_dt = pytz.utc.localize(epoch)

    loc = tus
    loc.pressure = 0
    actual_time = pytz.timezone(loc.tz).localize(
        datetime.datetime(2014, 10, 10, 8, 30))
    lb = pytz.timezone(loc.tz).localize(datetime.datetime(2014, 10, 10, tol))
    ub = pytz.timezone(loc.tz).localize(datetime.datetime(2014, 10, 10, 10))
    alt = solarposition.calc_time(lb, ub, loc.latitude, loc.longitude,
                                  'alt', math.radians(24.7))
    az = solarposition.calc_time(lb, ub, loc.latitude, loc.longitude,
                                 'az', math.radians(116.3))
    actual_timestamp = (actual_time - epoch_dt).total_seconds()

    assert_allclose((alt.replace(second=0, microsecond=0) -
                          epoch_dt).total_seconds(), actual_timestamp)
    assert_allclose((az.replace(second=0, microsecond=0) -
                          epoch_dt).total_seconds(), actual_timestamp)


@requires_ephem
def test_earthsun_distance():
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D')
    distance = solarposition.pyephem_earthsun_distance(times).values[0]
    assert_allclose(1, distance, atol=0.1)


def test_ephemeris_physical(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,12,30,30),
                          periods=1, freq='D', tz=golden_mst.tz)
    ephem_data = solarposition.ephemeris(times, golden_mst.latitude,
                                         golden_mst.longitude,
                                         pressure=82000,
                                         temperature=11)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_ephemeris_physical_dst(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.ephemeris(times, golden.latitude,
                                         golden.longitude, pressure=82000,
                                         temperature=11)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_ephemeris_physical_no_tz(expected_solpos, golden_mst):
    times = pd.date_range(datetime.datetime(2003,10,17,19,30,30),
                          periods=1, freq='D')
    ephem_data = solarposition.ephemeris(times, golden_mst.latitude,
                                         golden_mst.longitude,
                                         pressure=82000,
                                         temperature=11)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_get_solarposition_error(golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    with pytest.raises(ValueError):
        ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                     golden.longitude,
                                                     pressure=82000,
                                                     temperature=11,
                                                     method='error this')


@pytest.mark.parametrize("pressure, expected", [
    (82000, _expected_solpos_df()),
    (90000, pd.DataFrame(
        np.array([[  39.88997,   50.11003,  194.34024,   39.87205,   14.64151,
                     50.12795]]),
        columns=['apparent_elevation', 'apparent_zenith', 'azimuth',
                 'elevation', 'equation_of_time', 'zenith'],
        index=['2003-10-17T12:30:30Z']))
    ])
def test_get_solarposition_pressure(pressure, expected, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 pressure=pressure,
                                                 temperature=11)
    this_expected = expected.copy()
    this_expected.index = times
    this_expected = np.round(this_expected, 5)
    ephem_data = np.round(ephem_data, 5)
    assert_frame_equal(this_expected, ephem_data[this_expected.columns])


@pytest.mark.parametrize("altitude, expected", [
    (1830.14, _expected_solpos_df()),
    (2000, pd.DataFrame(
        np.array([[  39.88788,   50.11212,  194.34024,   39.87205,   14.64151,
                     50.12795]]),
        columns=['apparent_elevation', 'apparent_zenith', 'azimuth',
                 'elevation', 'equation_of_time', 'zenith'],
        index=['2003-10-17T12:30:30Z']))
    ])
def test_get_solarposition_altitude(altitude, expected, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 altitude=altitude,
                                                 temperature=11)
    this_expected = expected.copy()
    this_expected.index = times
    this_expected = np.round(this_expected, 5)
    ephem_data = np.round(ephem_data, 5)
    assert_frame_equal(this_expected, ephem_data[this_expected.columns])


@pytest.mark.parametrize("delta_t, method", [
    (None, 'nrel_numpy'),
    (67.0, 'nrel_numpy'),
    pytest.param(
        None, 'nrel_numba',
        marks=[pytest.mark.xfail(
            reason='spa.calculate_deltat not implemented for numba yet')]),
    (67.0, 'nrel_numba')
    ])
def test_get_solarposition_deltat(delta_t, method, expected_solpos_multi,
                                  golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=2, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 pressure=82000,
                                                 delta_t=delta_t,
                                                 temperature=11,
                                                 method=method)
    this_expected = expected_solpos_multi
    this_expected.index = times
    this_expected = np.round(this_expected, 5)
    ephem_data = np.round(ephem_data, 5)
    assert_frame_equal(this_expected, ephem_data[this_expected.columns])


def test_get_solarposition_no_kwargs(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003,10,17,13,30,30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude)
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


@requires_ephem
def test_get_solarposition_method_pyephem(expected_solpos, golden):
    times = pd.date_range(datetime.datetime(2003, 10, 17, 13, 30, 30),
                          periods=1, freq='D', tz=golden.tz)
    ephem_data = solarposition.get_solarposition(times, golden.latitude,
                                                 golden.longitude,
                                                 method='pyephem')
    expected_solpos.index = times
    expected_solpos = np.round(expected_solpos, 2)
    ephem_data = np.round(ephem_data, 2)
    assert_frame_equal(expected_solpos, ephem_data[expected_solpos.columns])


def test_nrel_earthsun_distance():
    times = pd.DatetimeIndex([datetime.datetime(2015, 1, 2),
                              datetime.datetime(2015, 8, 2),]
                             ).tz_localize('MST')
    result = solarposition.nrel_earthsun_distance(times, delta_t=64.0)
    expected = pd.Series(np.array([0.983289204601, 1.01486146446]),
                         index=times)
    assert_series_equal(expected, result)

    times = datetime.datetime(2015, 1, 2)
    result = solarposition.nrel_earthsun_distance(times, delta_t=64.0)
    expected = pd.Series(np.array([0.983289204601]),
                         index=pd.DatetimeIndex([times, ]))
    assert_series_equal(expected, result)


def test_equation_of_time():
    times = pd.DatetimeIndex(start="1/1/2015 0:00", end="12/31/2015 23:00",
                             freq="H")
    output = solarposition.spa_python(times, 37.8, -122.25, 100)
    eot = output['equation_of_time']
    eot_rng = eot.max() - eot.min()  # range of values, around 30 minutes
    eot_1 = solarposition.equation_of_time_spencer71(times.dayofyear)
    eot_2 = solarposition.equation_of_time_pvcdrom(times.dayofyear)
    assert np.allclose(eot_1 / eot_rng, eot / eot_rng, atol=0.3)  # spencer
    assert np.allclose(eot_2 / eot_rng, eot / eot_rng, atol=0.4)  # pvcdrom


def test_declination():
    times = pd.DatetimeIndex(start="1/1/2015 0:00", end="12/31/2015 23:00",
                             freq="H")
    atmos_refract = 0.5667
    delta_t = spa.calculate_deltat(times.year, times.month)
    unixtime = np.array([calendar.timegm(t.timetuple()) for t in times])
    _, _, declination = spa.solar_position(unixtime, 37.8, -122.25, 100,
                                           1013.25, 25, delta_t, atmos_refract,
                                           sst=True)
    declination = np.deg2rad(declination)
    declination_rng = declination.max() - declination.min()
    declination_1 = solarposition.declination_cooper69(times.dayofyear)
    declination_2 = solarposition.declination_spencer71(times.dayofyear)
    a, b = declination_1 / declination_rng, declination / declination_rng
    assert np.allclose(a, b, atol=0.03)  # cooper
    a, b = declination_2 / declination_rng, declination / declination_rng
    assert np.allclose(a, b, atol=0.02)  # spencer


def test_analytical_zenith():
    times = pd.DatetimeIndex(start="1/1/2015 0:00", end="12/31/2015 23:00",
                             freq="H").tz_localize('Etc/GMT+8')
    lat, lon = 37.8, -122.25
    lat_rad = np.deg2rad(lat)
    output = solarposition.spa_python(times, lat, lon, 100)
    solar_zenith = np.deg2rad(output['zenith'])  # spa
    # spencer
    eot = solarposition.equation_of_time_spencer71(times.dayofyear)
    hour_angle = np.deg2rad(solarposition.hour_angle(times, lon, eot))
    decl = solarposition.declination_spencer71(times.dayofyear)
    zenith_1 = solarposition.solar_zenith_analytical(lat_rad, hour_angle, decl)
    # pvcdrom and cooper
    eot = solarposition.equation_of_time_pvcdrom(times.dayofyear)
    hour_angle = np.deg2rad(solarposition.hour_angle(times, lon, eot))
    decl = solarposition.declination_cooper69(times.dayofyear)
    zenith_2 = solarposition.solar_zenith_analytical(lat_rad, hour_angle, decl)
    assert np.allclose(zenith_1, solar_zenith, atol=0.015)
    assert np.allclose(zenith_2, solar_zenith, atol=0.025)


def test_analytical_azimuth():
    times = pd.DatetimeIndex(start="1/1/2015 0:00", end="12/31/2015 23:00",
                             freq="H").tz_localize('Etc/GMT+8')
    lat, lon = 37.8, -122.25
    lat_rad = np.deg2rad(lat)
    output = solarposition.spa_python(times, lat, lon, 100)
    solar_azimuth = np.deg2rad(output['azimuth'])  # spa
    solar_zenith = np.deg2rad(output['zenith'])
    # spencer
    eot = solarposition.equation_of_time_spencer71(times.dayofyear)
    hour_angle = np.deg2rad(solarposition.hour_angle(times, lon, eot))
    decl = solarposition.declination_spencer71(times.dayofyear)
    zenith = solarposition.solar_zenith_analytical(lat_rad, hour_angle, decl)
    azimuth_1 = solarposition.solar_azimuth_analytical(lat_rad, hour_angle,
                                                       decl, zenith)
    # pvcdrom and cooper
    eot = solarposition.equation_of_time_pvcdrom(times.dayofyear)
    hour_angle = np.deg2rad(solarposition.hour_angle(times, lon, eot))
    decl = solarposition.declination_cooper69(times.dayofyear)
    zenith = solarposition.solar_zenith_analytical(lat_rad, hour_angle, decl)
    azimuth_2 = solarposition.solar_azimuth_analytical(lat_rad, hour_angle,
                                                       decl, zenith)

    idx = np.where(solar_zenith < np.pi/2)
    assert np.allclose(azimuth_1[idx], solar_azimuth.values[idx], atol=0.01)
    assert np.allclose(azimuth_2[idx], solar_azimuth.values[idx], atol=0.017)

    # test for NaN values at boundary conditions (PR #431)
    test_angles = np.radians(np.array(
                   [[   0., -180.,  -20.],
                    [   0.,    0.,   -5.],
                    [   0.,    0.,    0.],
                    [   0.,    0.,   15.],
                    [   0.,  180.,   20.],
                    [  30.,    0.,  -20.],
                    [  30.,    0.,   -5.],
                    [  30.,    0.,    0.],
                    [  30.,  180.,    5.],
                    [  30.,    0.,   10.],
                    [ -30.,    0.,  -20.],
                    [ -30.,    0.,  -15.],
                    [ -30.,    0.,    0.],
                    [ -30., -180.,    5.],
                    [ -30.,  180.,   10.]]))

    zeniths = solarposition.solar_zenith_analytical(*test_angles.T)
    azimuths = solarposition.solar_azimuth_analytical(*test_angles.T,
                                                      zenith=zeniths)

    assert not np.isnan(azimuths).any()


def test_hour_angle():
    """
    Test conversion from hours to hour angles in degrees given the following
    inputs from NREL SPA calculator at Golden, CO
    date,times,eot,sunrise,sunset
    1/2/2015,7:21:55,-3.935172,-70.699400,70.512721
    1/2/2015,16:47:43,-4.117227,-70.699400,70.512721
    1/2/2015,12:04:45,-4.026295,-70.699400,70.512721
    """
    longitude = -105.1786  # degrees
    times = pd.DatetimeIndex([
        '2015-01-02 07:21:55.2132',
        '2015-01-02 16:47:42.9828',
        '2015-01-02 12:04:44.6340'
    ]).tz_localize('Etc/GMT+7')
    eot = np.array([-3.935172, -4.117227, -4.026295])
    hours = solarposition.hour_angle(times, longitude, eot)
    expected = (-70.682338, 70.72118825000001, 0.000801250)
    # FIXME: there are differences from expected NREL SPA calculator values
    # sunrise: 4 seconds, sunset: 48 seconds, transit: 0.2 seconds
    # but the differences may be due to other SPA input parameters
    assert np.allclose(hours, expected)


def test_sun_rise_set_transit_geometric(expected_rise_set_spa, golden_mst):
    """Test geometric calculations for sunrise, sunset, and transit times"""
    times = expected_rise_set_spa.index
    latitude = golden_mst.latitude
    longitude = golden_mst.longitude
    eot = solarposition.equation_of_time_spencer71(times.dayofyear)  # minutes
    decl = solarposition.declination_spencer71(times.dayofyear)  # radians
    sr, ss, st = solarposition.sun_rise_set_transit_geometric(
        times, latitude=latitude, longitude=longitude, declination=decl,
        equation_of_time=eot)
    # sunrise: 2015-01-02 07:26:39.763224487, 2015-08-02 05:04:35.688533801
    # sunset:  2015-01-02 16:41:29.951096777, 2015-08-02 19:09:46.597355085
    # transit: 2015-01-02 12:04:04.857160632, 2015-08-02 12:07:11.142944443
    test_sunrise = solarposition._times_to_hours_after_local_midnight(sr)
    test_sunset = solarposition._times_to_hours_after_local_midnight(ss)
    test_transit = solarposition._times_to_hours_after_local_midnight(st)
    # convert expected SPA sunrise, sunset, transit to local datetime indices
    expected_sunrise = pd.DatetimeIndex(expected_rise_set_spa.sunrise.values,
                                        tz='UTC').tz_convert(golden_mst.tz)
    expected_sunset = pd.DatetimeIndex(expected_rise_set_spa.sunset.values,
                                       tz='UTC').tz_convert(golden_mst.tz)
    expected_transit = pd.DatetimeIndex(expected_rise_set_spa.transit.values,
                                        tz='UTC').tz_convert(golden_mst.tz)
    # convert expected times to hours since midnight as arrays of floats
    expected_sunrise = solarposition._times_to_hours_after_local_midnight(
        expected_sunrise)
    expected_sunset = solarposition._times_to_hours_after_local_midnight(
        expected_sunset)
    expected_transit = solarposition._times_to_hours_after_local_midnight(
        expected_transit)
    # geometric time has about 4-6 minute error compared to SPA sunset/sunrise
    expected_sunrise_error = np.array(
        [0.07910089555555544, 0.06908014805555496])  # 4.8[min], 4.2[min]
    expected_sunset_error = np.array(
        [-0.1036246955555562, -0.06983406805555603])  # -6.2[min], -4.2[min]
    expected_transit_error = np.array(
        [-0.011150788888889096, 0.0036508177777765383])  # -40[sec], 13.3[sec]
    assert np.allclose(test_sunrise, expected_sunrise,
                       atol=np.abs(expected_sunrise_error).max())
    assert np.allclose(test_sunset, expected_sunset,
                       atol=np.abs(expected_sunset_error).max())
    assert np.allclose(test_transit, expected_transit,
                       atol=np.abs(expected_transit_error).max())


def test_spencer_mc():
    """ test for the calculation based on spencer 1972 """
    latitude = 48.367073
    longitude = 10.868378
    assert_frame_equal(solarposition.spencer_mc(times[:10],
                                                latitude,
                                                longitude),
                       pd.DataFrame([[107.60190741, -17.60190741, 9.95454033,
                                      0.96706069, 0.40900622, -2.0908958],
                                     [107.09533954, -17.09533954, 13.51934494,
                                      0.96705971,
                                      0.4090031, -2.09315672],
                                     [106.43889684, -16.43889684, 17.04622292,
                                      0.96705874,
                                      0.40899997, -2.0954175],
                                     [105.63682427, -15.63682427, 20.52704485,
                                      0.96705777,
                                      0.40899683, -2.09767815],
                                     [104.69411613, -14.69411613, 23.95490053,
                                      0.9670568,
                                      0.40899367, -2.09993867],
                                     [103.61638656, -13.61638656, 27.32420466,
                                      0.96705583,
                                      0.4089905, -2.10219905],
                                     [102.40973635, -12.40973635, 30.63074363,
                                      0.96705486,
                                      0.40898732, -2.1044593],
                                     [101.08062211, -11.08062211, 33.87167089,
                                      0.9670539,
                                      0.40898412, -2.10671942],
                                     [99.63573414, -9.63573414, 37.04545803,
                                      0.96705293,
                                      0.40898091, -2.10897939],
                                     [98.0818867, -8.0818867, 40.15181379,
                                      0.96705197,
                                      0.40897769, -2.11123924]],
                                    index=times,
                                    columns=['zenith',
                                             'elevation',
                                             'azimuth',
                                             'eccentricity',
                                             'declination',
                                             'equation_of_time'])
                       )


def test_datetime2julians():
    """ test transformation from datetime to julians """
    julians = solarposition.datetime2julian(pd.to_datetime(times))
    np.testing.assert_array_almost_equal(julians,
                                         np.array([2458119.5, 2458119.54166667,
                                                   2458119.58333333,
                                                   2458119.625,
                                                   2458119.66666667,
                                                   2458119.70833333,
                                                   2458119.75, 2458119.79166667,
                                                   2458119.83333333,
                                                   2458119.875,
                                                   2458119.91666667,
                                                   2458119.95833333,
                                                   2458120., 2458120.04166667,
                                                   2458120.08333333,
                                                   2458120.125,
                                                   2458120.16666667,
                                                   2458120.20833333,
                                                   2458120.25, 2458120.29166667,
                                                   2458120.33333333,
                                                   2458120.375,
                                                   2458120.41666667,
                                                   2458120.45833333])
                                         )
