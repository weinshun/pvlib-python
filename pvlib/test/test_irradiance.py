import datetime
from collections import OrderedDict

import numpy as np
import pandas as pd

import pytest
from numpy.testing import assert_almost_equal, assert_allclose

from pandas.util.testing import assert_frame_equal, assert_series_equal

from pvlib.location import Location
from pvlib import clearsky
from pvlib import solarposition
from pvlib import irradiance
from pvlib import atmosphere

from conftest import requires_ephem, requires_numba, needs_numpy_1_10

# setup times and location to be tested.
tus = Location(32.2, -111, 'US/Arizona', 700)

# must include night values
times = pd.date_range(start='20140624', freq='6H', periods=4, tz=tus.tz)

ephem_data = solarposition.get_solarposition(
    times, tus.latitude, tus.longitude, method='nrel_numpy')

irrad_data = tus.get_clearsky(times, model='ineichen', linke_turbidity=3)

dni_et = irradiance.extraradiation(times.dayofyear)

ghi = irrad_data['ghi']


# setup for et rad test. put it here for readability
timestamp = pd.Timestamp('20161026')
dt_index = pd.DatetimeIndex([timestamp])
doy = timestamp.dayofyear
dt_date = timestamp.date()
dt_datetime = datetime.datetime.combine(dt_date, datetime.time(0))
dt_np64 = np.datetime64(dt_datetime)
value = 1383.636203

@pytest.mark.parametrize('input, expected', [
    (doy, value),
    (np.float64(doy), value),
    (dt_date, value),
    (dt_datetime, value),
    (dt_np64, value),
    (np.array([doy]), np.array([value])),
    (pd.Series([doy]), np.array([value])),
    (dt_index, pd.Series([value], index=dt_index)),
    (timestamp, value)
])
@pytest.mark.parametrize('method', [
    'asce', 'spencer', 'nrel', requires_ephem('pyephem')])
def test_extraradiation(input, expected, method):
    out = irradiance.extraradiation(input)
    assert_allclose(out, expected, atol=1)


@requires_numba
def test_extraradiation_nrel_numba():
    result = irradiance.extraradiation(times, method='nrel', how='numba', numthreads=8)
    assert_allclose(result, [1322.332316, 1322.296282, 1322.261205, 1322.227091])


def test_extraradiation_epoch_year():
    out = irradiance.extraradiation(doy, method='nrel', epoch_year=2012)
    assert_allclose(out, 1382.4926804890767, atol=0.1)


def test_extraradiation_invalid():
    with pytest.raises(ValueError):
        irradiance.extraradiation(300, method='invalid')


def test_grounddiffuse_simple_float():
    result = irradiance.grounddiffuse(40, 900)
    assert_allclose(result, 26.32000014911496)


def test_grounddiffuse_simple_series():
    ground_irrad = irradiance.grounddiffuse(40, ghi)
    assert ground_irrad.name == 'diffuse_ground'


def test_grounddiffuse_albedo_0():
    ground_irrad = irradiance.grounddiffuse(40, ghi, albedo=0)
    assert 0 == ground_irrad.all()


def test_grounddiffuse_albedo_invalid_surface():
    with pytest.raises(KeyError):
        irradiance.grounddiffuse(40, ghi, surface_type='invalid')


def test_grounddiffuse_albedo_surface():
    result = irradiance.grounddiffuse(40, ghi, surface_type='sand')
    assert_allclose(result, [0, 3.731058, 48.778813, 12.035025], atol=1e-4)


def test_isotropic_float():
    result = irradiance.isotropic(40, 100)
    assert_allclose(result, 88.30222215594891)


def test_isotropic_series():
    result = irradiance.isotropic(40, irrad_data['dhi'])
    assert_allclose(result, [0, 35.728402, 104.601328, 54.777191], atol=1e-4)


def test_klucher_series_float():
    result = irradiance.klucher(40, 180, 100, 900, 20, 180)
    assert_allclose(result, 88.3022221559)


def test_klucher_series():
    result = irradiance.klucher(40, 180, irrad_data['dhi'], irrad_data['ghi'],
                       ephem_data['apparent_zenith'],
                       ephem_data['azimuth'])
    assert_allclose(result, [0, 37.446276, 109.209347, 56.965916], atol=1e-4)


def test_haydavies():
    result = irradiance.haydavies(40, 180, irrad_data['dhi'], irrad_data['dni'],
                         dni_et,
                         ephem_data['apparent_zenith'],
                         ephem_data['azimuth'])
    assert_allclose(result, [0, 14.967008, 102.994862, 33.190865], atol=1e-4)


def test_reindl():
    result = irradiance.reindl(40, 180, irrad_data['dhi'], irrad_data['dni'],
                      irrad_data['ghi'], dni_et,
                      ephem_data['apparent_zenith'],
                      ephem_data['azimuth'])
    assert_allclose(result, [np.nan, 15.730664, 104.131724, 34.166258], atol=1e-4)


def test_king():
    result = irradiance.king(40, irrad_data['dhi'], irrad_data['ghi'],
                    ephem_data['apparent_zenith'])
    assert_allclose(result, [0, 44.629352, 115.182626, 79.719855], atol=1e-4)


def test_perez():
    am = atmosphere.relativeairmass(ephem_data['apparent_zenith'])
    dni = irrad_data['dni'].copy()
    dni.iloc[2] = np.nan
    out = irradiance.perez(40, 180, irrad_data['dhi'], dni,
                     dni_et, ephem_data['apparent_zenith'],
                     ephem_data['azimuth'], am)
    expected = pd.Series(np.array(
        [   0.        ,   31.46046871,  np.nan,   45.45539877]),
        index=times)
    assert_series_equal(out, expected, check_less_precise=2)


def test_perez_components():
    am = atmosphere.relativeairmass(ephem_data['apparent_zenith'])
    dni = irrad_data['dni'].copy()
    dni.iloc[2] = np.nan
    out, components = irradiance.perez(40, 180, irrad_data['dhi'], dni,
                     dni_et, ephem_data['apparent_zenith'],
                     ephem_data['azimuth'], am, return_components=True)
    expected = pd.Series(np.array(
        [   0.        ,   31.46046871,  np.nan,   45.45539877]),
        index=times)
    expected_components = pd.DataFrame(
        {
            'circumsolar': np.array([ 0.        ,  0.        ,         np.nan,  4.47966439]),
            'isotropic': np.array([  0.        ,  26.84138589,          np.nan,  31.72696071]),
            'horizon': np.array([ 0.        ,  4.62212181,         np.nan,  9.25316454])
        },
        index=times
    )
    df_components = pd.DataFrame(components)
    sum_components = pd.Series(np.sum(list(components.values()), axis=0), index=times)
    assert_series_equal(out, expected, check_less_precise=2)
    assert_frame_equal(df_components, expected_components)
    assert_series_equal(sum_components, expected, check_less_precise=2)

@needs_numpy_1_10
def test_perez_arrays():
    am = atmosphere.relativeairmass(ephem_data['apparent_zenith'])
    dni = irrad_data['dni'].copy()
    dni.iloc[2] = np.nan
    out = irradiance.perez(40, 180, irrad_data['dhi'].values, dni.values,
                     dni_et, ephem_data['apparent_zenith'].values,
                     ephem_data['azimuth'].values, am.values)
    expected = np.array(
        [   0.        ,   31.46046871,  np.nan,   45.45539877])
    assert_allclose(out, expected, atol=1e-2)



def test_liujordan():
    expected = pd.DataFrame(np.
        array([[863.859736967, 653.123094076, 220.65905025]]),
        columns=['ghi', 'dni', 'dhi'],
        index=[0])
    out = irradiance.liujordan(
        pd.Series([10]), pd.Series([0.5]), pd.Series([1.1]),
        pressure=93000., dni_extra=1400)
    assert_frame_equal(out, expected)


# klutcher (misspelling) will be removed in 0.3
def test_total_irrad():
    models = ['isotropic', 'klutcher', 'klucher',
              'haydavies', 'reindl', 'king', 'perez']
    AM = atmosphere.relativeairmass(ephem_data['apparent_zenith'])

    for model in models:
        total = irradiance.total_irrad(
            32, 180,
            ephem_data['apparent_zenith'], ephem_data['azimuth'],
            dni=irrad_data['dni'], ghi=irrad_data['ghi'],
            dhi=irrad_data['dhi'],
            dni_extra=dni_et, airmass=AM,
            model=model,
            surface_type='urban')

        assert total.columns.tolist() == ['poa_global', 'poa_direct',
                                          'poa_diffuse', 'poa_sky_diffuse',
                                          'poa_ground_diffuse']


@pytest.mark.parametrize('model', ['isotropic', 'klucher',
                                   'haydavies', 'reindl', 'king', 'perez'])
def test_total_irrad_scalars(model):
    total = irradiance.total_irrad(
        32, 180,
        10, 180,
        dni=1000, ghi=1100,
        dhi=100,
        dni_extra=1400, airmass=1,
        model=model,
        surface_type='urban')

    assert list(total.keys()) == ['poa_global', 'poa_direct',
                                  'poa_diffuse', 'poa_sky_diffuse',
                                  'poa_ground_diffuse']
    # test that none of the values are nan
    assert np.isnan(np.array(list(total.values()))).sum() == 0


def test_globalinplane():
    aoi = irradiance.aoi(40, 180, ephem_data['apparent_zenith'],
                         ephem_data['azimuth'])
    airmass = atmosphere.relativeairmass(ephem_data['apparent_zenith'])
    gr_sand = irradiance.grounddiffuse(40, ghi, surface_type='sand')
    diff_perez = irradiance.perez(
        40, 180, irrad_data['dhi'], irrad_data['dni'], dni_et,
        ephem_data['apparent_zenith'], ephem_data['azimuth'], airmass)
    irradiance.globalinplane(
        aoi=aoi, dni=irrad_data['dni'], poa_sky_diffuse=diff_perez,
        poa_ground_diffuse=gr_sand)


def test_disc_keys():
    clearsky_data = tus.get_clearsky(times, model='ineichen',
                                     linke_turbidity=3)
    disc_data = irradiance.disc(clearsky_data['ghi'], ephem_data['zenith'],
                                ephem_data.index)
    assert 'dni' in disc_data.columns
    assert 'kt' in disc_data.columns
    assert 'airmass' in disc_data.columns


def test_disc_value():
    times = pd.DatetimeIndex(['2014-06-24T12-0700','2014-06-24T18-0700'])
    ghi = pd.Series([1038.62, 254.53], index=times)
    zenith = pd.Series([10.567, 72.469], index=times)
    pressure = 93193.
    disc_data = irradiance.disc(ghi, zenith, times, pressure=pressure)
    assert_almost_equal(disc_data['dni'].values,
                        np.array([830.46, 676.09]), 1)


def test_dirint():
    clearsky_data = tus.get_clearsky(times, model='ineichen',
                                     linke_turbidity=3)
    pressure = 93193.
    dirint_data = irradiance.dirint(clearsky_data['ghi'], ephem_data['zenith'],
                                    ephem_data.index, pressure=pressure)

def test_dirint_value():
    times = pd.DatetimeIndex(['2014-06-24T12-0700','2014-06-24T18-0700'])
    ghi = pd.Series([1038.62, 254.53], index=times)
    zenith = pd.Series([10.567, 72.469], index=times)
    pressure = 93193.
    dirint_data = irradiance.dirint(ghi, zenith, times, pressure=pressure)
    assert_almost_equal(dirint_data.values,
                        np.array([ 888. ,  683.7]), 1)


def test_dirint_nans():
    times = pd.DatetimeIndex(start='2014-06-24T12-0700', periods=5, freq='6H')
    ghi = pd.Series([np.nan, 1038.62, 1038.62, 1038.62, 1038.62], index=times)
    zenith = pd.Series([10.567, np.nan, 10.567, 10.567, 10.567,], index=times)
    pressure = pd.Series([93193., 93193., np.nan, 93193., 93193.], index=times)
    temp_dew = pd.Series([10, 10, 10, np.nan, 10], index=times)
    dirint_data = irradiance.dirint(ghi, zenith, times, pressure=pressure,
                                    temp_dew=temp_dew)
    assert_almost_equal(dirint_data.values,
                        np.array([np.nan, np.nan, np.nan, np.nan, 893.1]), 1)


def test_dirint_tdew():
    times = pd.DatetimeIndex(['2014-06-24T12-0700','2014-06-24T18-0700'])
    ghi = pd.Series([1038.62, 254.53], index=times)
    zenith = pd.Series([10.567, 72.469], index=times)
    pressure = 93193.
    dirint_data = irradiance.dirint(ghi, zenith, times, pressure=pressure,
                                    temp_dew=10)
    assert_almost_equal(dirint_data.values,
                        np.array([892.9,  636.5]), 1)

def test_dirint_no_delta_kt():
    times = pd.DatetimeIndex(['2014-06-24T12-0700','2014-06-24T18-0700'])
    ghi = pd.Series([1038.62, 254.53], index=times)
    zenith = pd.Series([10.567, 72.469], index=times)
    pressure = 93193.
    dirint_data = irradiance.dirint(ghi, zenith, times, pressure=pressure,
                                    use_delta_kt_prime=False)
    assert_almost_equal(dirint_data.values,
                        np.array([861.9,  670.4]), 1)

def test_dirint_coeffs():
    coeffs = irradiance._get_dirint_coeffs()
    assert coeffs[0,0,0,0] == 0.385230
    assert coeffs[0,1,2,1] == 0.229970
    assert coeffs[3,2,6,3] == 1.032260


def test_erbs():
    ghi = pd.Series([0, 50, 1000, 1000])
    zenith = pd.Series([120, 85, 10, 10])
    doy = pd.Series([1, 1, 1, 180])
    expected = pd.DataFrame(np.
        array([[ -0.00000000e+00,   0.00000000e+00,  -0.00000000e+00],
               [  9.67127061e+01,   4.15709323e+01,   4.05715990e-01],
               [  7.94187742e+02,   2.17877755e+02,   7.18119416e-01],
               [  8.42358014e+02,   1.70439297e+02,   7.68919470e-01]]),
        columns=['dni', 'dhi', 'kt'])

    out = irradiance.erbs(ghi, zenith, doy)

    assert_frame_equal(np.round(out, 0), np.round(expected, 0))


def test_erbs_all_scalar():
    ghi = 1000
    zenith = 10
    doy = 180

    expected = OrderedDict()
    expected['dni'] = 8.42358014e+02
    expected['dhi'] = 1.70439297e+02
    expected['kt'] = 7.68919470e-01

    out = irradiance.erbs(ghi, zenith, doy)

    for k, v in out.items():
        assert_allclose(v, expected[k], 5)
