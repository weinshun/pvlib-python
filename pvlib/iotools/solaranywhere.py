"""Functions to read and retrieve SolarAnywhere data."""

import requests
import pandas as pd
import time
import json

URL = 'https://service.solaranywhere.com/api/v2'

# Dictionary mapping SolarAnywhere names to standard pvlib names
# Names with spaces are used in SolarAnywhere files, and names without spaces
# are used by the SolarAnywhere API
VARIABLE_MAP = {
    'Global Horizontal Irradiance (GHI) W/m2': 'ghi',
    'GlobalHorizontalIrradiance_WattsPerMeterSquared': 'ghi',
    'DirectNormalIrradiance_WattsPerMeterSquared': 'dni',
    'Direct Normal Irradiance (DNI) W/m2': 'dni',
    'Diffuse Horizontal Irradiance (DIF) W/m2': 'dhi',
    'DiffuseHorizontalIrradiance_WattsPerMeterSquared': 'dhi',
    'AmbientTemperature (deg C)': 'temp_air',
    'AmbientTemperature_DegreesC': 'temp_air',
    'WindSpeed (m/s)': 'wind_speed',
    'WindSpeed_MetersPerSecond': 'wind_speed',
    'Relative Humidity (%)': 'relative_humidity',
    'RelativeHumidity_Percent': 'relative_humidity',
    'Clear Sky GHI': 'ghi_clear',
    'ClearSkyGHI_WattsPerMeterSquared': 'ghi_clear',
    'Clear Sky DNI': 'dni_clear',
    'ClearSkyDNI_WattsPerMeterSquared': 'dni_clear',
    'Clear Sky DHI': 'dhi_clear',
    'ClearSkyDHI_WattsPerMeterSquared': 'dhi_clear',
    'Albedo': 'albedo',
    'Albedo_Unitless': 'albedo',
}

DEFAULT_VARIABLES = [
    'StartTime', 'ObservationTime', 'EndTime',
    'GlobalHorizontalIrradiance_WattsPerMeterSquared',
    'DirectNormalIrradiance_WattsPerMeterSquared',
    'DiffuseHorizontalIrradiance_WattsPerMeterSquared',
    'AmbientTemperature_DegreesC', 'WindSpeed_MetersPerSecond',
    'Albedo_Unitless', 'DataVersion'
]


def get_solaranywhere(latitude, longitude, api_key, start=None, end=None,
                      source='SolarAnywhereLatest', time_resolution=60,
                      spatial_resolution=0.01, true_dynamics=False,
                      probability_of_exceedance=None,
                      variables=DEFAULT_VARIABLES, missing_data='FillAverage',
                      url=URL, map_variables=True, max_response_time=300):
    """Retrieve historical irradiance time series data from SolarAnywhere.

    The SolarAnywhere API is described in [1]_ and [2]_. A detailed list of
    available options for the input parameters can be found in [3]_.

    Parameters
    ----------
    latitude: float
        In decimal degrees, north is positive (ISO 19115).
    longitude: float
        In decimal degrees, east is positive (ISO 19115).
    api_key: str
        SolarAnywhere API key.
    start: datetime like, optional
        First timestamp of the requested period. If a timezone is not
        specified, UTC is assumed. Not applicable for TMY data.
    end: datetime like, optional
        Last timtestamp of the requested period. If a timezone is not
        specified, UTC is assumed. Not applicable for TMY data.
    source: str, default: 'SolarAnywhereLatest'
        Data source. Options include: 'SolarAnywhereLatest' (historical data),
        'SolarAnywhereTGYLatest' (TMY for GHI), 'SolarAnywhereTDYLatest' (TMY
        for DNI), or 'SolarAnywherePOELatest' for probability of exceedance.
        Specific dataset versions can also be specified, e.g.,
        'SolarAnywhere3_2' (see [3]_ for a full list of options).
    time_resolution: {60, 30, 15, 5}, default: 60
        Time resolution in minutes. For TMY data, time resolution has to be 60
        min. (hourly).
    spatial_resolution: {0.1, 0.01, 0.005}, default: 0.01
        Spatial resolution in degrees.
    true_dynamics: bool, default: False
        Whether to apply SolarAnywhere TrueDynamics statistical processing.
        Only available for the 5-min time resolution.
    probability_of_exceedance: int, optional
        Probability of exceedance in the range of 1 to 99. Only relevant when
        requesting probability of exceedance (POE) time series.
    variables: list-like, default: :const:`DEFAULT_VARIABLES`
        Variables to retrieve (described in [4]_).  Available variables depend
        on whether historical or TMY data is requested.
    missing_data: {'Omit', 'FillAverage'}, default: 'FillAverage'
        Method for treating missing data.
    url: str, default: :const:`pvlib.iotools.solaranywhere.URL`
        Base url of SolarAnywhere API.
    map_variables: bool, default: True
        When true, renames columns of the DataFrame to pvlib variable names
        where applicable. See variable :const:`VARIABLE_MAP`.
    max_response_time: float, default: 300
        Time in seconds to wait for requested data to become available.

    Returns
    -------
    data: pandas.DataFrame
        Timeseries data from SolarAnywhere. The index is the observation time
        (middle of period) localized to UTC.
    metadata: dict
        Metadata available (includes site latitude, longitude, and altitude).

    See Also
    --------
    pvlib.iotools.read_solaranywhere

    Note
    ----
    SolarAnywhere data requests are asynchronous, and it might take several
    minutes for the requested data to become available.

    Examples
    --------
    >>> # Retrieve one month of SolarAnywhere data for Atlanta, GA
    >>> data, meta = pvlib.iotools.get_solaranywhere(
    ...     latitude=33.765, longitude=-84.395, api_key='redacted',
    ...     start=pd.Timestamp(2020,1,1), end=pd.Timestamp(2020,2,1))  # doctest: +SKIP

    References
    ----------
    .. [1] `SolarAnywhere API
       <https://www.solaranywhere.com/support/using-solaranywhere/api/>`_
    .. [2] `SolarAnywhere irradiance and weather API requests
       <https://developers.cleanpower.com/irradiance-and-weather-data/irradiance-and-weather-requests/>`_
    .. [3] `SolarAnywhere API options
       <https://developers.cleanpower.com/irradiance-and-weather-data/complete-schema/createweatherdatarequest/options/>`_
    .. [4] `SolarAnywhere variable definitions
       <https://www.solaranywhere.com/support/data-fields/definitions/>`_
    """  # noqa: E501
    headers = {'content-type': "application/json; charset=utf-8",
               'X-Api-Key': api_key,
               'Accept': "application/json"}

    payload = {
        "Sites": [{
            "Latitude": latitude,
            "Longitude": longitude
        }],
        "Options": {
            "OutputFields": variables,
            "SummaryOutputFields": [],  # Do not request summary/monthly data
            "SpatialResolution_Degrees": spatial_resolution,
            "TimeResolution_Minutes": time_resolution,
            "WeatherDataSource": source,
            "MissingDataHandling": missing_data,
        }
    }

    if true_dynamics:
        payload['Options']['ApplyTrueDynamics'] = True

    if probability_of_exceedance is not None:
        if type(probability_of_exceedance) != int:
            raise ValueError('`probability_of_exceedance` must be an integer')
        payload['Options']['ProbabilityOfExceedance'] = \
            probability_of_exceedance

    # Add start/end time if requesting non-TMY data
    if (('TGY' not in source) & ('TDY' not in source) & ('TMY' not in source) &
            ('POE' not in source)):
        if (start is None) or (end is None):
            raise ValueError('When requesting non-TMY data, specifying `start`'
                             ' and `end` is required.')
        # start/end are required to have an associated time zone
        if start.tz is None:
            start = start.tz_localize('UTC')
        if end.tz is None:
            end = end.tz_localize('UTC')
        payload['Options']["StartTime"] = start.isoformat()
        payload['Options']["EndTime"] = end.isoformat()

    # Convert the payload dictionary to a JSON string (uses double quotes)
    payload = json.dumps(payload)
    # Make data request
    request = requests.post(url+'/WeatherData', data=payload, headers=headers)
    # Raise error if request is not OK
    if request.ok is False:
        raise ValueError(request.json()['Message'])
    # Retrieve weather request ID
    weather_request_id = request.json()["WeatherRequestId"]

    # The SolarAnywhere API is asynchronous, hence a second request is
    # necessary to retrieve the data (WeatherDataResult).
    start_time = time.time()  # Current time in seconds since the Epoch
    # Attempt to retrieve results until the max response time has been exceeded
    while True:
        time.sleep(5)  # Sleep for 5 seconds before each data retrieval attempt
        results = requests.get(url+'/WeatherDataResult/'+weather_request_id, headers=headers)  # noqa: E501
        results_json = results.json()
        if results_json.get('Status') == 'Done':
            if results_json['WeatherDataResults'][0]['Status'] == 'Failure':
                raise RuntimeError(results_json['WeatherDataResults'][0]['ErrorMessages'])  # noqa: E501
            break
        elif results_json.get('StatusCode') == 'BadRequest':
            raise RuntimeError(f"Bad request: {results_json['Message']}")
        elif (time.time()-start_time) > max_response_time:
            raise TimeoutError('Time exceeded the `max_response_time`.')

    # Extract time series data
    data = pd.DataFrame(results_json['WeatherDataResults'][0]['WeatherDataPeriods']['WeatherDataPeriods'])  # noqa: E501
    # Set index and convert to UTC time
    data.index = pd.to_datetime(data['ObservationTime'])
    data.index = data.index.tz_convert('UTC')
    if map_variables:
        data = data.rename(columns=VARIABLE_MAP)

    # Parse metadata
    meta = results_json['WeatherDataResults'][0]['WeatherSourceInformation']
    meta['time_resolution'] = results_json['WeatherDataResults'][0]['WeatherDataPeriods']['TimeResolution_Minutes']  # noqa: E501
    # Rename and convert applicable metadata parameters to floats
    meta['latitude'] = float(meta.pop('Latitude'))
    meta['longitude'] = float(meta.pop('Longitude'))
    meta['altitude'] = float(meta.pop('Elevation_Meters'))
    return data, meta


def read_solaranywhere(filename, map_variables=True):
    """
    Read a SolarAnywhere formatted file into a pandas DataFrame.

    The SolarAnywhere file format and variables are described in [1]_. Note,
    the SolarAnywhere file format resembles the TMY3 file format but contains
    additional variables and meatadata.

    Parameters
    ----------
    fbuf: file-like object
        File-like object containing data to read.
    map_variables: bool, default: True
        When true, renames columns of the DataFrame to pvlib variable names
        where applicable. See variable :const:`VARIABLE_MAP`.

    Returns
    -------
    data: pandas.DataFrame
        Timeseries data from SolarAnywhere. Index is localized to UTC.
    metadata: dict
        Metadata available in the file.

    See Also
    --------
    pvlib.iotools.get_solaranywhere, pvlib.iotools.parse_solaranywhere

    References
    ----------
    .. [1] `SolarAnywhere historical data file formats
       <https://www.solaranywhere.com/support/historical-data/file-formats/>`_
    """
    with open(str(filename), 'r') as fbuf:
        content = parse_solaranywhere(fbuf, map_variables=map_variables)
    return content


def parse_solaranywhere(fbuf, map_variables=True):
    """
    Parse a file-like buffer with data in the format of a SolarAnywhere file.

    The SolarAnywhere file format and variables are described in [1]_. Note,
    the SolarAnywhere file format resembles the TMY3 file format but contains
    additional variables and meatadata.

    Parameters
    ----------
    fbuf: file-like object
        File-like object containing data to read.
    map_variables: bool, default: True
        When true, renames columns of the DataFrame to pvlib variable names
        where applicable. See variable :const:`VARIABLE_MAP`.

    Returns
    -------
    data: pandas.DataFrame
        Timeseries data from SolarAnywhere. Index is localized to UTC.
    metadata: dict
        Metadata available in the file.

    See Also
    --------
    pvlib.iotools.read_solaranywhere, pvlib.iotools.get_solaranywhere

    References
    ----------
    .. [1] `SolarAnywhere historical data file formats
       <https://www.solaranywhere.com/support/historical-data/file-formats/>`_
    """
    # Parse metadata contained within the first line
    firstline = fbuf.readline().strip().split(',')
    meta = {}
    meta['USAF'] = int(firstline.pop(0))
    meta['name'] = firstline.pop(0)
    meta['state'] = firstline.pop(0)
    meta['TZ'] = float(firstline.pop(0))
    meta['latitude'] = float(firstline.pop(0))
    meta['longitude'] = float(firstline.pop(0))
    meta['altitude'] = float(firstline.pop(0))

    # SolarAnywhere files contain additional metadata than the TMY3 format.
    # The additional metadata is specified as key-value pairs, where each entry
    # is separated by a slash, and the key-value pairs are separated by a
    # colon. E.g., 'Data Version: 3.4 / Type: Typical Year / ...'
    for i in ','.join(firstline).replace('"', '').split('/'):
        if ':' in i:
            k, v = i.split(':')
            meta[k.strip()] = v.strip()

    # Read remaining part of file which contains the time series data
    data = pd.read_csv(fbuf)
    # Set index to UTC
    data.index = pd.to_datetime(data['ObservationTime(GMT)'],
                                format='%m/%d/%Y %H:%M', utc=True)
    if map_variables:
        data = data.rename(columns=VARIABLE_MAP)

    return data, meta
