"""
tests for :mod:`pvlib.iotools.ecmwf_macc`
"""

from __future__ import division
import os
import datetime
import numpy as np
from conftest import requires_netCDF4
from pvlib.iotools import ecmwf_macc

DIRNAME = os.path.dirname(__file__)
PROJNAME = os.path.dirname(DIRNAME)
DATADIR = os.path.join(PROJNAME, 'data')
TESTDATA = 'aod550_2012Nov1_test.nc'

# for creating test data
DATES = [datetime.date(2012, 11, 1), datetime.date(2012, 11, 2)]
DATAFILE = 'aod550_2012Nov1.nc'
RESIZE = 4
LON_BND = (0, 360.0)
LAT_BND = (90, -90)


@requires_netCDF4
def test_get_nearest_indices():
    """Test getting indices given latitude, longitude from ECMWF_MACC data."""
    data = ecmwf_macc.ECMWF_MACC(os.path.join(DATADIR, TESTDATA))
    ilat, ilon = data.get_nearest_indices(38, -122)
    assert ilat == 17
    assert ilon == 79


@requires_netCDF4
def test_interp_data():
    """Test interpolating UTC time from ECMWF_MACC data."""
    data = ecmwf_macc.ECMWF_MACC(os.path.join(DATADIR, TESTDATA))
    test9am = data.interp_data(
        38, -122, datetime.datetime(2012, 11, 1, 9, 0, 0), data.data, 'aod550')
    assert np.isclose(test9am, data.data.variables['aod550'][2, 17, 79])
    test12pm = data.interp_data(
        38, -122, datetime.datetime(2012, 11, 1, 12, 0, 0), data.data,
        'aod550')
    assert np.isclose(test12pm, data.data.variables['aod550'][3, 17, 79])
    test113301 = data.interp_data(
        38, -122, datetime.datetime(2012, 11, 1, 11, 33, 1), data.data,
        'aod550')
    expected = test9am + (2 + (33 + 1 / 60) / 60) / 3 * (test12pm - test9am)
    assert np.isclose(test113301, expected)  # 0.15515305836696536


@requires_netCDF4
def test_read_ecmwf_macc():
    """Test reading ECMWF_MACC data from netCDF4 file."""
    aod = ecmwf_macc.read_ecmwf_macc(os.path.join(DATADIR, TESTDATA), 38, -122)
    expected_times = [
        1351738800, 1351749600, 1351760400, 1351771200, 1351782000, 1351792800,
        1351803600, 1351814400]
    assert np.allclose(aod.index.astype(int) // 1000000000, expected_times)
    expected = [
        0.39530905, 0.22372988, 0.18373338, 0.15011313, 0.13081389, 0.11171923,
        0.09743233, 0.0921472]
    assert np.allclose(aod.aod550.values, expected)


def _create_test_data():
    """
    Create test data from downloaded data.

    Downloaded data from ECMWF for a single day is 3MB. This creates a subset
    of the downloaded data that is only 100kb.
    """

    import netCDF4

    if not os.path.exists(DATAFILE):
        ecmwf_macc.get_ecmwf_macc(DATAFILE, "aod550", DATES[0], DATES[1])

    data = netCDF4.Dataset(DATAFILE)
    testdata = netCDF4.Dataset(TESTDATA, 'w', format="NETCDF3_64BIT_OFFSET")

    # attributes
    testdata.Conventions = data.Conventions
    testdata.history = "intensionally blank"

    # longitiude
    lon_name = 'longitude'
    lon_test = data.variables[lon_name][::RESIZE]
    lon_size = lon_test.size
    lon = testdata.createDimension(lon_name, lon_size)
    assert not lon.isunlimited()
    assert lon_test[0] == LON_BND[0]
    assert (LON_BND[-1] - lon_test[-1]) == (LON_BND[-1] / lon_size)
    longitudes = testdata.createVariable(lon_name, "f4", (lon_name,))
    longitudes.units = data.variables[lon_name].units
    longitudes.long_name = lon_name
    longitudes[:] = lon_test

    # latitude
    lat_name = 'latitude'
    lat_test = data.variables[lat_name][::RESIZE]
    lat = testdata.createDimension(lat_name, lat_test.size)
    assert not lat.isunlimited()
    assert lat_test[0] == LAT_BND[0]
    assert lat_test[-1] == LAT_BND[-1]
    latitudes = testdata.createVariable(lat_name, "f4", (lat_name,))
    latitudes.units = data.variables[lat_name].units
    latitudes.long_name = lat_name
    latitudes[:] = lat_test

    # time
    time_name = 'time'
    time_size = data.dimensions[time_name].size // 2
    time_test = data.variables[time_name][:time_size]
    time = testdata.createDimension(time_name, None)
    assert time.isunlimited()
    times = testdata.createVariable(time_name, 'i4', (time_name,))
    times.units = data.variables[time_name].units
    times.long_name = time_name
    times.calendar = data.variables[time_name].calendar
    times[:] = time_test

    # aod
    aod_name = 'aod550'
    aod_vars = data.variables[aod_name]
    aod_dims = (time_name, lat_name, lon_name)
    aod_fill_value = getattr(aod_vars, '_FillValue')
    aods = testdata.createVariable(
        aod_name, 'i2', aod_dims, fill_value=aod_fill_value)
    for attr in aod_vars.ncattrs():
        if attr.startswith('_'):
            continue
        setattr(aods, attr, getattr(aod_vars, attr))
    aods[:] = aod_vars[:time_size, ::RESIZE, ::RESIZE]

    data.close()
    testdata.close()
