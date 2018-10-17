"""Functions to read NREL MIDC data.
"""
from functools import partial
import pandas as pd


def map_midc_to_pvlib(variable_map, field_name):
    """A mapper function to rename Dataframe columns to their pvlib counterparts.

    Parameters
    ----------
    variable_map: Dictionary
        A dictionary of "MIDC field name": "pvlib variable name"

    Returns
    -------
    label: string
        The pvlib variable name associated with the MIDC field or the input if
        a mapping does not exist.
    """
    try:
        return variable_map[field_name]
    except KeyError:
        return field_name


def format_index(data):
    """Create DatetimeIndex for the Dataframe localized to the timezone provided
    as the label of the second (time) column.
    """
    timezone = data.columns[1]
    datetime = data['DATE (MM/DD/YYYY)'] + data[timezone]
    datetime = pd.to_datetime(datetime, format='%m/%d/%Y%H:%M')
    data = data.set_index(datetime)
    data = data.tz_localize(timezone)
    return data


def read_midc(filename, variable_map={}):
    """Read in NREL MIDC [1]_ weather data.

    Parameters
    ----------
    filename: string
        Filename or url of data to read.
    variable_map: dictionary
        Dictionary mapping MIDC field names to pvlib names. For a full list of
        pvlib variable names please see the `Variable Style Rules <https://pvlib-python.readthedocs.io/en/latest/variables_style_rules.html>`_.

        Example::

            { 'Temperature @ 2m [deg C]': 'air_temp'}

    Returns
    -------
    data: Dataframe
        A dataframe with DatetimeIndex localized to the provided timezone.

    References
    ----------
    .. [1] National Renewable Energy Laboratory: Measurement and Instrumentation Data Center # NOQA
        `https://midcdmz.nrel.gov/ <https://midcdmz.nrel.gov/>`_
    """
    data = pd.read_csv(filename)
    data = format_index(data)
    mapper = partial(map_midc_to_pvlib, variable_map)
    data = data.rename(columns=mapper)
    return data
