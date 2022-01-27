"""
Bifacial Modeling - procedural
==============================

Example of bifacial modeling using procedural method
"""

# %%
# This example shows how to complete a bifacial modeling example using the
# :py:class:`pvlib.modelchain.ModelChain` with the
# :py:func:`pvlib.bifacial.pvfactors_timeseries` function to transpose
# GHI data to both front and rear Plane of Array (POA) irradiance.

import pandas as pd
from pvlib import location
from pvlib import solarposition
from pvlib import tracking
from pvlib import bifacial
from pvlib import temperature
from pvlib import pvsystem
import matplotlib.pyplot as plt

# using Greensboro, NC for this example
lat, lon = 36.084, -79.817
tz = 'Etc/GMT+5'
times = pd.date_range('2021-06-21', '2021-6-22', freq='1T', tz=tz)

# create location object and get clearsky data
site_location = location.Location(lat, lon, tz=tz, name='Greensboro, NC')
cs = site_location.get_clearsky(times)

# get solar position data
solar_position = solarposition.get_solarposition(cs.index,
                                                 lat,
                                                 lon
                                                 )

# set ground coverage ratio and max_angle to 
# pull orientation data for a single-axis tracker
gcr = 0.35
max_phi = 60
orientation = tracking.singleaxis(solar_position['apparent_zenith'],
                                  solar_position['azimuth'],
                                  max_angle=max_phi,
                                  backtrack=True,
                                  gcr=gcr
                                  )

# set axis_azimuth, albedo, pvrow width and height, and use
# the pvfactors  engine for both front and rear-side absorbed irradiance
axis_azmuth = 180
pvrow_height = 3
pvrow_width = 4
albedo = 0.2
irrad = bifacial.pvfactors_timeseries(solar_position['azimuth'],
                                      solar_position['apparent_zenith'],
                                      orientation['surface_azimuth'],
                                      orientation['surface_tilt'],
                                      axis_azmuth,
                                      cs.index,
                                      cs['dni'],
                                      cs['dhi'],
                                      gcr,
                                      pvrow_height,
                                      pvrow_width,
                                      albedo
                                      )

# using bifaciality factor and pvfactors results, create effective
# irradiance data
bifaciality = 0.75
effective_irrad_bifi = irrad[2] + (irrad[3] * bifaciality)
effective_irrad_mono = irrad[2]

# get cell temperature using the Faiman model
temp_cell = temperature.faiman(irrad[0], 25, 1)

# using the pvwatts_dc model and parameters detailed above,
# set pdc0 and return DC power for both bifacial and monofacial
pdc0 = 1
gamma_pdc = -0.0043
pdc_bifi = pvsystem.pvwatts_dc(effective_irrad_bifi,
                               temp_cell,
                               pdc0,
                               gamma_pdc=gamma_pdc
                               ).fillna(0)

pdc_mono = pvsystem.pvwatts_dc(effective_irrad_mono,
                               temp_cell, 
                               pdc0,
                               gamma_pdc=gamma_pdc
                               ).fillna(0)

# plot results
plt.figure()
plt.title('Bifacial vs Monofacial Simulation on Clearsky Day')
plt.plot(pdc_bifi)
plt.plot(pdc_mono)
plt.legend(['bifacial', 'monofacial'])
plt.ylabel('DC Power')