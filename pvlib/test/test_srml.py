import inspect
import os

from numpy import isnan
import pandas as pd
from pandas.util.testing import network
import pytest

from pvlib.iotools import srml


test_dir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
srml_testfile = os.path.join(test_dir, '../data/SRML-EUPO1801.txt')


def test_read_srml():
    srml.read_srml(srml_testfile)


@network
def test_read_srml_remote():
    srml.read_srml('http://solardat.uoregon.edu/download/Archive/EUPO1801.txt')


def test_read_srml_columns_exist():
    data = srml.read_srml(srml_testfile)
    assert 'ghi_0' in data.columns
    assert 'ghi_0_flag' in data.columns
    assert 'ghi_2' in data.columns
    assert '7008' in data.columns
    assert '7008_flag' in data.columns


def test_read_srml_nans_exist():
    data = srml.read_srml(srml_testfile)
    assert isnan(data['temp_air_3'][1510])
    assert data['temp_air_3_flag'][1510] == 99


@pytest.mark.parametrize('url,year,month', [
    ('http://solardat.uoregon.edu/download/Archive/EUPO1801.txt',
     2018, 1),
    ('http://solardat.uoregon.edu/download/Archive/EUPO1612.txt',
     2016, 12),
])
def test_read_srml_dt_index(url, year, month):
    data = srml.read_srml(url)
    start = pd.Timestamp(year, month, 1, 0, 0).tz_localize('Etc/GMT+8')
    end = pd.Timestamp(year, month, 31, 23, 59).tz_localize('Etc/GMT+8')
    assert data.index[0] == start
    assert data.index[-1] == end
    assert (data.index[59::60].minute == 59).all()
    assert year not in data.columns


@pytest.mark.parametrize('column,expected', [
    ('1001', 'ghi_1'),
    ('7324', '7324'),
    ('2001', '2001'),
    ('2017', 'dni_7')
])
def test_map_columns(column, expected):
    assert srml.map_columns(column) == expected


@network
def test_request_srml_data():
    file_data = srml.read_srml(srml_testfile)
    requested = srml.request_srml_data('EU', 2018, 1)
    assert file_data.equals(requested)
