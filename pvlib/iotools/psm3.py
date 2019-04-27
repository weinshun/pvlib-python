"""
Get PSM3 TMY
see https://developer.nrel.gov/docs/solar/nsrdb/psm3_data_download/
"""

import io
import requests
import pandas as pd

URL = "http://developer.nrel.gov/api/solar/nsrdb_psm3_download.csv"

# 'relative_humidity', 'total_precipitable_water' are not available
ATTRIBUTES = [
    'air_temperature', 'dew_point', 'dhi', 'dni', 'ghi', 'surface_albedo',
    'surface_pressure', 'wind_direction', 'wind_speed']


def get_psm3(latitude, longitude, names='tmy', interval=60,
             api_key='DEMO_KEY'):
    """
    Get PSM3 data

    Parameters
    ----------
    latitude : float or int
        in decimal degrees, between -90 and 90, north is positive
    longitude : float or int
        in decimal degrees, between -180 and 180, east is positive
    names : str
        PSM3 API parameter specifing year or TMY variant to download, see notes
        below for options, default: ``'tmy'``
    interval : int
        interval size in minutes, can be only either 30 or 60, default: 60
    api_key : str
        optional, supply your NREL Developer Network API key

    Returns
    -------
    headers : dict
        metadata from NREL PSM3 about the record, see notes for fields
    data : pandas.DataFrame
        timeseries data from NREL PSM3

    Raises
    ------
    requests.HTTPError
        if the request return status is not ok then the ``'errors'`` from the
        JSON response will be returned as an exception

    Notes
    -----
    The PSM3 API `names` parameter must be a single value from the following
    list::

        ['1998', '1999', '2000', '2001', '2002', '2003', '2004', '2005',
         '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013',
         '2014', '2015', '2016', '2017', 'tmy', 'tmy-2016', 'tmy-2017',
         'tdy-2017', 'tgy-2017']

    The return is a tuple with two items. The first item is a header with
    metadata from NREL PSM3 about the record containing the following fields:

    * Source
    * Location ID
    * City
    * State
    * Country
    * Latitude
    * Longitude
    * Time Zone
    * Elevation
    * Local Time Zone
    * Dew Point Units
    * DHI Units
    * DNI Units
    * GHI Units
    * Temperature Units
    * Pressure Units
    * Wind Direction Units
    * Wind Speed
    * Surface Albedo Units
    * Version

    The second item is a dataframe with the timeseries data downloaded.

    See Also
    --------
    pvlib.iotools.read_tmy2, pvlib.iotools.read_tmy3

    References
    ----------

    * `NREL Developer Network - Physical Solar Model (PSM) v3
      <https://developer.nrel.gov/docs/solar/nsrdb/psm3_data_download/>`_
    * `NREL National Solar Radiation Database (NSRDB)
      <https://nsrdb.nrel.gov/>`_

    """
    longitude = ('%9.4f' % longitude).strip()
    latitude = ('%8.4f' % latitude).strip()
    params = {
        'api_key': api_key,
        'full_name': 'Sample User',
        'email': 'sample@email.com',
        'affiliation': 'Test Organization',
        'reason': 'Example',
        'mailing_list': 'true',
        'wkt': 'POINT(%s %s)' % (longitude, latitude),
        'names': names,
        'attributes':  ','.join(ATTRIBUTES),
        'leap_day': 'false',
        'utc': 'false',
        'interval': interval
    }
    # request CSV download from NREL PSM3
    response = requests.get(URL, params=params)
    if not response.ok:
        raise requests.HTTPError(response.json()['errors'])
    # the CSV is in the response content as a UTF-8 bytestring
    # to use pandas we need to create a file buffer from the response
    fbuf = io.StringIO(response.content.decode('utf-8'))
    # The first 2 lines of the response are headers with metadat
    header_fields = fbuf.readline().split(',')
    header_fields[-1] = header_fields[-1].strip()  # strip trailing newline
    header_values = fbuf.readline().split(',')
    header_values[-1] = header_values[-1].strip()  # strip trailing newline
    header = dict(zip(header_fields, header_values))
    # the response is all strings, so set some header types to numbers
    header['Local Time Zone'] = int(header['Local Time Zone'])
    header['Time Zone'] = int(header['Time Zone'])
    header['Latitude'] = float(header['Latitude'])
    header['Longitude'] = float(header['Longitude'])
    header['Elevation'] = int(header['Elevation'])
    # get the column names so we can set the dtypes
    columns = fbuf.readline().split(',')
    columns[-1] = columns[-1].strip()  # strip trailing newline
    dtypes = dict.fromkeys(columns, float)  # all floats except datevec
    dtypes.update(Year=int, Month=int, Day=int, Hour=int, Minute=int)
    data = pd.read_csv(
        fbuf, header=None, names=columns, dtype=dtypes,
        delimiter=',', lineterminator='\n')  # skip carriage returns \r
    # the response 1st 5 columns are a date vector, convert to datetime
    dtidx = pd.to_datetime(
        data[['Year', 'Month', 'Day', 'Hour', 'Minute']])
    # in USA all timezones are intergers
    tz = 'Etc/GMT%+d' % -header['Time Zone']
    data.index = pd.DatetimeIndex(dtidx).tz_localize(tz)
    return header, data
