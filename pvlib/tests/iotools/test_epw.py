from pandas.util.testing import network
import pytest

from pvlib.iotools import epw
from conftest import DATA_DIR

epw_testfile = DATA_DIR / 'NLD_Amsterdam062400_IWEC.epw'


def test_read_epw():
    epw.read_epw(epw_testfile)


@network
@pytest.mark.remote_data
@pytest.mark.flaky(reruns=5, reruns_delay=2)
def test_read_epw_remote():
    url = 'https://energyplus.net/weather-download/europe_wmo_region_6/NLD//NLD_Amsterdam.062400_IWEC/NLD_Amsterdam.062400_IWEC.epw'
    epw.read_epw(url)


def test_read_epw_coerce_year():
    coerce_year = 1987
    data, _ = epw.read_epw(epw_testfile, coerce_year=coerce_year)
    assert (data.index.year == 1987).all()
