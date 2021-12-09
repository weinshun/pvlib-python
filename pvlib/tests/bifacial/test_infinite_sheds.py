"""
test infinite sheds
"""

import os
import numpy as np
import pandas as pd
from pvlib.bifacial import infinite_sheds

import pytest
from ..conftest import DATA_DIR


TESTDATA = os.path.join(DATA_DIR, 'infinite_sheds.csv')

# location and irradiance
LAT, LON, TZ = 37.85, -122.25, -8  # global coordinates

# PV module orientation
#   tilt: positive = facing toward sun, negative = backward
#   system-azimuth: positive counter-clockwise from north
TILT, SYSAZ = 20.0, 250.0
GCR = 0.5  # ground coverage ratio
HEIGHT = 1  # height above ground
PITCH = 4  # row spacing

# IAM parameters
B0 = 0.05
MAXAOI = 85

# backside
BACKSIDE = {'tilt': 180.0 - TILT, 'sysaz': (180.0 + SYSAZ) % 360.0}

# TESTDATA
TESTDATA = pd.read_csv(TESTDATA, parse_dates=True)
GHI, DHI = TESTDATA.ghi, TESTDATA.dhi
# convert #DIV/0 to np.inf, 0/0 to NaN, then convert to float
DF = np.where(GHI > 0, TESTDATA.df, np.inf)
DF = np.where(DHI > 0, DF, np.nan).astype(np.float64)
TESTDATA.df = DF
F_GND_BEAM = TESTDATA['Fsky-gnd']
BACK_POA_GND_SKY = TESTDATA['POA_gnd-sky_b']
FRONT_POA_GND_SKY = TESTDATA['POA_gnd-sky_f']
BACK_TAN_PSI_TOP = np.tan(TESTDATA.psi_top_b)
FRONT_TAN_PSI_TOP = np.tan(TESTDATA.psi_top_f)

TAN_PSI_TOP0_F = np.tan(0.312029739)  # GCR*SIN(TILT_f)/(1-GCR*COS(TILT_f))
TAN_PSI_TOP0_B = np.tan(0.115824807)  # GCR*SIN(TILT_b)/(1-GCR*COS(TILT_b))
TAN_PSI_BOT1_F = np.tan(0.115824807)  # SIN(TILT_f) / (COS(TILT_f) + 1/GCR)
TAN_PSI_BOT1_B = np.tan(0.312029739)  # SIN(TILT_b) / (COS(TILT_b) + 1/GCR)

# radians
SOLAR_ZENITH_RAD = np.radians(TESTDATA.apparent_zenith)
SOLAR_AZIMUTH_RAD = np.radians(TESTDATA.azimuth)
SYSAZ_RAD = np.radians(SYSAZ)
BACK_SYSAZ_RAD = np.radians(BACKSIDE['sysaz'])
TILT_RAD = np.radians(TILT)
BACK_TILT_RAD = np.radians(BACKSIDE['tilt'])

ARGS = (GCR, HEIGHT, TILT, PITCH)


gcr, height, surface_tilt, pitch = ARGS

def test__gcr_prime():
    result = infinite_sheds._gcr_prime(gcr=0.5, height=1, surface_tilt=20,
                                       pitch=4)
    assert np.isclose(result, 1.2309511000407718)


# calculated ground-sky angles at panel edges
# gcr_prime = infinite_sheds._gcr_prime(*ARGS)
# back_tilt_rad = np.pi - tilt_rad
# psi_0_x0 = back_tilt_rad
# psi_1_x0 = np.arctan2(
#     gcr_prime * np.sin(back_tilt_rad), 1 - gcr_prime * np.cos(back_tilt_rad))
PSI_0_X0, PSI_1_X0 = 2.792526803190927, 0.19278450775754705
# psi_0_x1 = np.arctan2(
#     gcr_prime * np.sin(tilt_rad), 1 - gcr_prime * np.cos(tilt_rad))
# psi_1_x1 = tilt_rad
PSI_0_X1, PSI_1_X1 = 1.9271427336418656, 0.3490658503988659


@pytest.fixture
def test_system():
    syst = {'height': 1.,
           'pitch': 4.,
           'surface_tilt': 30}
    syst['gcr'] = 2.0 / syst['pitch']
    return syst


def test__ground_sky_angles(test_system):
    x = np.array([0.0, 0.5, 1.0])
    psi0, psi1 = infinite_sheds._ground_sky_angles(x, **test_system)
    expected_psi0 = np.array([150., 126.2060231, 75.])
    expected_psi1 = np.array([15., 20.10390936, 30.])
    assert np.allclose(psi0, expected_psi0)
    assert np.allclose(psi1, expected_psi1)


FZ0_LIMIT = 1.4619022000815438  # infinite_sheds.f_z0_limit(*ARGS)
# np.arctan2(GCR * np.sin(TILT_RAD), (1.0 - GCR * np.cos(TILT_RAD)))
PSI_TOP = 0.3120297392978313


def test__ground_sky_angles_prev(test_system):
    x = np.array([0.0, 1.0])
    psi0, psi1 = infinite_sheds._ground_sky_angles_prev(x, **test_system)
    expected_psi0 = np.array([75., 23.7939769])
    expected_psi1 = np.array([30., 180. - 23.7939769])
    assert np.allclose(psi0, expected_psi0)
    assert np.allclose(psi1, expected_psi1)


FZ1_LIMIT = 1.4619022000815427  # infinite_sheds.f_z1_limit(*ARGS)
# np.arctan2(GCR * np.sin(BACK_TILT_RAD), (1.0 - GCR * np.cos(BACK_TILT_RAD)))
PSI_TOP_BACK = 0.11582480672702507


def test__ground_sky_angles_next(test_system):
    x = np.array([0., 1.0])
    psi0, psi1 = infinite_sheds._ground_sky_angles_next(x, **test_system)
    expected_psi0 = np.array([180 - 9.8960906389, 150.])
    expected_psi1 = np.array([9.8960906389, 15.])
    assert np.allclose(psi0, expected_psi0)
    assert np.allclose(psi1, expected_psi1)


def test__sky_angle(test_system):
    x = np.array([0., 1.0])
    angle, tan_angle = infinite_sheds._sky_angle(
        test_system['gcr'], test_system['surface_tilt'], x)
    exp_tan_angle = np.array([1. / (4 - np.sqrt(3)), 0.])
    exp_angle = np.array([23.79397689, 0.])
    assert np.allclose(angle, exp_angle)
    assert np.allclose(tan_angle, exp_tan_angle)


def test__f_z0_limit(test_system):
    result = infinite_sheds._f_z0_limit(**test_system)
    expected = 1.0
    assert np.isclose(result, expected)

    
VF_GND_SKY = 0.5184093800689326
FZ_SKY = np.array([
    0.37395996, 0.37985504, 0.38617593, 0.39294621, 0.40008092,
    0.40760977, 0.41546240, 0.42363368, 0.43209234, 0.44079809,
    0.44974664, 0.45887908, 0.46819346, 0.47763848, 0.48719477,
    0.49682853, 0.50650894, 0.51620703, 0.52589332, 0.53553353,
    0.54510461, 0.55457309, 0.56391157, 0.57309977, 0.58209408,
    0.59089589, 0.59944489, 0.60775144, 0.61577071, 0.62348812,
    0.63089212, 0.63793327, 0.64463809, 0.65092556, 0.65683590,
    0.66231217, 0.66735168, 0.67194521, 0.67603859, 0.67967459,
    0.68274901, 0.68532628, 0.68733124, 0.68876957, 0.68962743,
    0.68984316, 0.68953528, 0.68867052, 0.68716547, 0.68492226,
    0.68196156, 0.67826724, 0.67378014, 0.66857561, 0.66252116,
    0.65574207, 0.64814205, 0.63978082, 0.63066636, 0.62078878,
    0.61025517, 0.59900195, 0.58719184, 0.57481610, 0.56199241,
    0.54879229, 0.53530254, 0.52163859, 0.50789053, 0.49417189,
    0.48059555, 0.46725727, 0.45425705, 0.44170686, 0.42964414,
    0.41822953, 0.40742909, 0.39738731, 0.38808373, 0.37957663,
    0.37191014, 0.36503340, 0.35906878, 0.35388625, 0.34959679,
    0.34610681, 0.34343945, 0.34158818, 0.34047992, 0.34019127,
    0.34058737, 0.34174947, 0.34357674, 0.34608321, 0.34924749,
    0.35300886, 0.35741583, 0.36235918, 0.36789933, 0.37394838])


def test__vf_ground_sky():
    vf_gnd_sky, fz_sky = infinite_sheds._vf_ground_sky(*ARGS)
    assert np.isclose(vf_gnd_sky, VF_GND_SKY)
    assert np.allclose(fz_sky, FZ_SKY)


def test__poa_ground_sky():
    # front side
    poa_gnd_sky_f = infinite_sheds._poa_ground_sky(
        TESTDATA.poa_ground_diffuse_f, F_GND_BEAM, DF, 1.0)
    # CSV file decimals are truncated
    assert np.allclose(
        poa_gnd_sky_f, FRONT_POA_GND_SKY, equal_nan=True, atol=1e-6)
    # backside
    poa_gnd_sky_b = infinite_sheds._poa_ground_sky(
        TESTDATA.poa_ground_diffuse_b, F_GND_BEAM, DF, 1.0)
    assert np.allclose(poa_gnd_sky_b, BACK_POA_GND_SKY, equal_nan=True)


def test__sky_angle_tangent():
    # frontside
    tan_psi_top_f = infinite_sheds._sky_angle_tangent(
        GCR, TILT_RAD, TESTDATA.Fx_f)
    assert np.allclose(tan_psi_top_f, FRONT_TAN_PSI_TOP)
    # backside
    tan_psi_top_b = infinite_sheds._sky_angle_tangent(
        GCR, BACK_TILT_RAD, TESTDATA.Fx_b)
    assert np.allclose(tan_psi_top_b, BACK_TAN_PSI_TOP)
    tan_psi_top_f = infinite_sheds._sky_angle_tangent(GCR, TILT_RAD, 0.0)
    assert np.allclose(tan_psi_top_f, TAN_PSI_TOP0_F)
    # backside
    tan_psi_top_b = infinite_sheds._sky_angle_tangent(
        GCR, BACK_TILT_RAD, 0.0)
    assert np.allclose(tan_psi_top_b, TAN_PSI_TOP0_B)


if __name__ == '__main__':
    from matplotlib import pyplot as plt
    plt.ion()
    plt.plot(*infinite_sheds.ground_sky_diffuse_view_factor(*ARGS))
    plt.title(
        'combined sky view factor, not including horizon and first/last row')
    plt.xlabel('fraction of pitch from front to back')
    plt.ylabel('view factor')
    plt.grid()
    fig, ax = plt.subplots(2, 1, figsize=(6, 8))
    fx = np.linspace(0, 1, 100)
    fskyz = [infinite_sheds.calc_fgndpv_zsky(x, *ARGS) for x in fx]
    fskyz, fgnd_pv = zip(*fskyz)
    ax[0].plot(fx, fskyz/(1-np.cos(TILT_RAD))*2)
    ax[0].plot(fx, fgnd_pv/(1-np.cos(TILT_RAD))*2)
    ax[0].grid()
    ax[0].set_title('frontside integrated ground reflected')
    ax[0].set_xlabel('fraction of PV surface from bottom ($F_x$)')
    ax[0].set_ylabel('adjustment to $\\frac{1-\\cos(\\beta)}{2}$')
    ax[0].legend(('blocked', 'all sky'))
    fskyz = [
        infinite_sheds.calc_fgndpv_zsky(
            x, GCR, HEIGHT, BACK_TILT_RAD, PITCH) for x in fx]
    fskyz, fgnd_pv = zip(*fskyz)
    ax[1].plot(fx, fskyz/(1-np.cos(BACK_TILT_RAD))*2)
    ax[1].plot(fx, fgnd_pv/(1-np.cos(BACK_TILT_RAD))*2)
    ax[1].grid()
    ax[1].set_title('backside integrated ground reflected')
    ax[1].set_xlabel('fraction of PV surface from bottom ($F_x$)')
    ax[1].set_ylabel('adjustment to $\\frac{1-\\cos(\\beta)}{2}$')
    ax[1].legend(('blocked', 'all sky'))
    plt.tight_layout()
