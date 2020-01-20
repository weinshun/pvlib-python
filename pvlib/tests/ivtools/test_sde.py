import numpy as np
import pytest
from pvlib import pvsystem
from pvlib.ivtools import sde
from pvlib.tests.conftest import requires_scipy


@pytest.fixture
def get_test_iv_params():
    return {'IL': 8.0, 'I0': 5e-10, 'Rsh': 1000, 'Rs': 0.2, 'nNsVth': 1.61864}


@pytest.fixture
def get_cec_params_cansol_cs5p_220p():
    return {'input': {'V_mp_ref': 46.6, 'I_mp_ref': 4.73, 'V_oc_ref': 58.3,
                      'I_sc_ref': 5.05, 'alpha_sc': 0.0025,
                      'beta_voc': -0.19659, 'gamma_pmp': -0.43,
                      'cells_in_series': 96},
            'output': {'a_ref': 2.3674, 'I_L_ref': 5.056, 'I_o_ref': 1.01e-10,
                       'R_sh_ref': 837.51, 'R_s': 1.004, 'Adjust': 2.3}}


@requires_scipy
def test_fit_sandia_simple(get_test_iv_params, get_bad_iv_curves):
    test_params = get_test_iv_params
    testcurve = pvsystem.singlediode(photocurrent=test_params['IL'],
                                     saturation_current=test_params['I0'],
                                     resistance_shunt=test_params['Rsh'],
                                     resistance_series=test_params['Rs'],
                                     nNsVth=test_params['nNsVth'],
                                     ivcurve_pnts=300)
    expected = tuple(test_params[k] for k in ['IL', 'I0', 'Rsh', 'Rs',
                     'nNsVth'])
    result = sde.fit_sandia_simple(voltage=testcurve['v'],
                                   current=testcurve['i'])
    assert np.allclose(result, expected, rtol=5e-5)
    result = sde.fit_sandia_simple(voltage=testcurve['v'],
                                   current=testcurve['i'],
                                   v_oc=testcurve['v_oc'],
                                   i_sc=testcurve['i_sc'])
    assert np.allclose(result, expected, rtol=5e-5)
    result = sde.fit_sandia_simple(voltage=testcurve['v'],
                                   current=testcurve['i'],
                                   v_oc=testcurve['v_oc'],
                                   i_sc=testcurve['i_sc'],
                                   v_mp_i_mp=(testcurve['v_mp'],
                                   testcurve['i_mp']))
    assert np.allclose(result, expected, rtol=5e-5)
    result = sde.fit_sandia_simple(voltage=testcurve['v'],
                                   current=testcurve['i'], vlim=0.1)
    assert np.allclose(result, expected, rtol=5e-5)


@requires_scipy
def test_fit_sandia_simple_bad_iv(get_bad_iv_curves):
    # bad IV curves for coverage of if/then in sde._sandia_simple_params
    v1, i1, v2, i2 = get_bad_iv_curves
    result = sde.fit_sandia_simple(voltage=v1, current=i1)
    assert np.allclose(result, (-2.4322856072799985, 8.854688976836396,
                                -63.56227601452038, 111.18558915546389,
                                -137.9965046659527))
    result = sde.fit_sandia_simple_params(voltage=v2, current=i2)
    assert np.allclose(result, (2.62405311949227, 1.8657963912925288,
                                110.35202827739991, -65.652554411442,
                                174.49362093001415))


@pytest.mark.parametrize('i,v,nsvth,expected',  [
    (np.array(
        [4., 3.95, 3.92, 3.9, 3.89, 3.88, 3.82, 3.8, 3.75, 3.7, 3.68, 3.66,
         3.65, 3.5, 3.2, 2.7, 2.2, 1.3, .6, 0.]),
     np.array(
        [0., .2, .4, .6, .8, 1., 1.2, 1.4, 1.6, 1.8, 2., 2.2, 2.4, 2.6, 2.7,
         2.76, 2.78, 2.81, 2.85, 2.88]),
     2.,
     (-96695.792, 96699.876, 7.4791, .0288, -.1413)),
    (np.array([3., 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 1.7, 0.8, 0.]),
     np.array([0., 0.2, 0.4, 0.6, 0.8, 1., 1.2, 1.4, 1.45, 1.5]),
     10.,
     (2.3392, 11.6865, -.232, -.2596, -.7119)),
    (np.array(
        [5., 4.9, 4.8, 4.7, 4.6, 4.5, 4.4, 4.3, 4.2, 4.1, 4., 3.8, 3.5, 1.7,
         0.]),
     np.array(
        [0., .1, .2, .3, .4, .5, .6, .7, .8, .9, 1., 1.1, 1.18, 1.2, 1.22]),
     15.,
     (-22.0795, 27.1196, -4.2076, -.0056, -.0498))])
def test__fit_sandia_cocontent(i, v, nsvth, expected):
    # test confirms agreement with Matlab code. The returned parameters
    # are nonsense
    iph, io, rs, rsh, n = sde._fit_sandia_cocontent(v, i, nsvth)
    np.testing.assert_allclose(iph, np.array(expected[0]), atol=.0001)
    np.testing.assert_allclose(io, np.array([expected[1]]), atol=.0001)
    np.testing.assert_allclose(rsh, np.array([expected[2]]), atol=.0001)
    np.testing.assert_allclose(rs, np.array([expected[3]]), atol=.0001)
    np.testing.assert_allclose(n, np.array([expected[4]]), atol=.0001)


@pytest.fixture
def get_bad_iv_curves():
    # v1, i1 produces a bad value for I0_voc
    v1 = np.array([0, 0.338798867469060, 0.677597734938121, 1.01639660240718,
                   1.35519546987624, 1.69399433734530, 2.03279320481436,
                   2.37159207228342, 2.71039093975248, 3.04918980722154,
                   3.38798867469060, 3.72678754215966, 4.06558640962873,
                   4.40438527709779, 4.74318414456685, 5.08198301203591,
                   5.42078187950497, 5.75958074697403, 6.09837961444309,
                   6.43717848191215, 6.77597734938121, 7.11477621685027,
                   7.45357508431933, 7.79237395178839, 8.13117281925745,
                   8.46997168672651, 8.80877055419557, 9.14756942166463,
                   9.48636828913369, 9.82516715660275, 10.1639660240718,
                   10.5027648915409, 10.8415637590099, 11.1803626264790,
                   11.5191614939481, 11.8579603614171, 12.1967592288862,
                   12.5355580963552, 12.8743569638243, 13.2131558312934,
                   13.5519546987624, 13.8907535662315, 14.2295524337005,
                   14.5683513011696, 14.9071501686387, 15.2459490361077,
                   15.5847479035768, 15.9235467710458, 16.2623456385149,
                   16.6011445059840, 16.9399433734530, 17.2787422409221,
                   17.6175411083911, 17.9563399758602, 18.2951388433293,
                   18.6339377107983, 18.9727365782674, 19.3115354457364,
                   19.6503343132055, 19.9891331806746, 20.3279320481436,
                   20.6667309156127, 21.0055297830817, 21.3443286505508,
                   21.6831275180199, 22.0219263854889, 22.3607252529580,
                   22.6995241204270, 23.0383229878961, 23.3771218553652,
                   23.7159207228342, 24.0547195903033, 24.3935184577724,
                   24.7323173252414, 25.0711161927105, 25.4099150601795,
                   25.7487139276486, 26.0875127951177, 26.4263116625867,
                   26.7651105300558, 27.1039093975248, 27.4427082649939,
                   27.7815071324630, 28.1203059999320, 28.4591048674011,
                   28.7979037348701, 29.1367026023392, 29.4755014698083,
                   29.8143003372773, 30.1530992047464, 30.4918980722154,
                   30.8306969396845, 31.1694958071536, 31.5082946746226,
                   31.8470935420917, 32.1858924095607, 32.5246912770298,
                   32.8634901444989, 33.2022890119679, 33.5410878794370])
    i1 = np.array([3.39430882774470, 2.80864492110761, 3.28358165429196,
                   3.41191190551673, 3.11975662808148, 3.35436585834612,
                   3.23953272899809, 3.60307083325333, 2.80478101508277,
                   2.80505102853845, 3.16918996870373, 3.21088388439857,
                   3.46332865310431, 3.09224155015883, 3.17541550741062,
                   3.32470179290389, 3.33224664316240, 3.07709000050741,
                   2.89141245343405, 3.01365768561537, 3.23265176770231,
                   3.32253647634228, 2.97900657569736, 3.31959549243966,
                   3.03375461550111, 2.97579298978937, 3.25432831375159,
                   2.89178382564454, 3.00341909207567, 3.72637492250097,
                   3.28379856976360, 2.96516169245835, 3.25658381110230,
                   3.41655911533139, 3.02718097944604, 3.11458376760376,
                   3.24617304369762, 3.45935502367636, 3.21557333256913,
                   3.27611176482650, 2.86954135732485, 3.32416319254657,
                   3.15277467598732, 3.08272557013770, 3.15602202666259,
                   3.49432799877150, 3.53863997177632, 3.10602611478455,
                   3.05373911151821, 3.09876772570781, 2.97417228624287,
                   2.84573593699237, 3.16288578405195, 3.06533173612783,
                   3.02118336639575, 3.34374977225502, 2.97255164138821,
                   3.19286135682863, 3.10999753817133, 3.26925354620079,
                   3.11957809501529, 3.20155017481720, 3.31724984405837,
                   3.42879043512927, 3.17933067619240, 3.47777362613969,
                   3.20708912539777, 3.48205761174907, 3.16804363684327,
                   3.14055472378230, 3.13445657434470, 2.91152696252998,
                   3.10984113847427, 2.80443349399489, 3.23146278164875,
                   2.94521083406108, 3.17388903141715, 3.05930294897030,
                   3.18985234673287, 3.27946609274898, 3.33717523113602,
                   2.76394303462702, 3.19375132937510, 2.82628616689450,
                   2.85238527394143, 2.82975892599489, 2.79196912313914,
                   2.72860792049395, 2.75585977414140, 2.44280222448805,
                   2.36052347370628, 2.26785071765738, 2.10868255743462,
                   2.06165739407987, 1.90047259509385, 1.39925575828709,
                   1.24749015957606, 0.867823806536762, 0.432752457749993, 0])
    # v2, i2 produces a bad value for I0_vmp
    v2 = np.array([0, 0.365686097622586, 0.731372195245173, 1.09705829286776,
                   1.46274439049035, 1.82843048811293, 2.19411658573552,
                   2.55980268335810, 2.92548878098069, 3.29117487860328,
                   3.65686097622586, 4.02254707384845, 4.38823317147104,
                   4.75391926909362, 5.11960536671621, 5.48529146433880,
                   5.85097756196138, 6.21666365958397, 6.58234975720655,
                   6.94803585482914, 7.31372195245173, 7.67940805007431,
                   8.04509414769690, 8.41078024531949, 8.77646634294207,
                   9.14215244056466, 9.50783853818725, 9.87352463580983,
                   10.2392107334324, 10.6048968310550, 10.9705829286776,
                   11.3362690263002, 11.7019551239228, 12.0676412215454,
                   12.4333273191679, 12.7990134167905, 13.1646995144131,
                   13.5303856120357, 13.8960717096583, 14.2617578072809,
                   14.6274439049035, 14.9931300025260, 15.3588161001486,
                   15.7245021977712, 16.0901882953938, 16.4558743930164,
                   16.8215604906390, 17.1872465882616, 17.5529326858841,
                   17.9186187835067, 18.2843048811293, 18.6499909787519,
                   19.0156770763745, 19.3813631739971, 19.7470492716197,
                   20.1127353692422, 20.4784214668648, 20.8441075644874,
                   21.2097936621100, 21.5754797597326, 21.9411658573552,
                   22.3068519549778, 22.6725380526004, 23.0382241502229,
                   23.4039102478455, 23.7695963454681, 24.1352824430907,
                   24.5009685407133, 24.8666546383359, 25.2323407359585,
                   25.5980268335810, 25.9637129312036, 26.3293990288262,
                   26.6950851264488, 27.0607712240714, 27.4264573216940,
                   27.7921434193166, 28.1578295169392, 28.5235156145617,
                   28.8892017121843, 29.2548878098069, 29.6205739074295,
                   29.9862600050521, 30.3519461026747, 30.7176322002973,
                   31.0833182979198, 31.4490043955424, 31.8146904931650,
                   32.1803765907876, 32.5460626884102, 32.9117487860328,
                   33.2774348836554, 33.6431209812779, 34.0088070789005,
                   34.3744931765231, 34.7401792741457, 35.1058653717683,
                   35.4715514693909, 35.8372375670135, 36.2029236646360])
    i2 = np.array([6.49218806928330, 6.49139336899548, 6.17810697175204,
                   6.75197816263663, 6.59529074137515, 6.18164578868300,
                   6.38709397931910, 6.30685422248427, 6.44640615548925,
                   6.88727230397772, 6.42074852785591, 6.46348580823746,
                   6.38642309763941, 5.66356277572311, 6.61010381702082,
                   6.33288284311125, 6.22475343933610, 6.30651399433833,
                   6.44435022944051, 6.43741711131908, 6.03536180208946,
                   6.23814639328170, 5.97229140403242, 6.20790000748341,
                   6.22933550182341, 6.22992127804882, 6.13400871899299,
                   6.83491312449950, 6.07952797245846, 6.35837746415450,
                   6.41972128662324, 6.85256717258275, 6.25807797296759,
                   6.25124948151766, 6.22229212812413, 6.72249444167406,
                   6.41085549981649, 6.75792874870056, 6.22096181559171,
                   6.47839564388996, 6.56010208597432, 6.63300966556949,
                   6.34617546039339, 6.79812221146153, 6.14486056194136,
                   6.14979256889311, 6.16883037644880, 6.57309183229605,
                   6.40064681038509, 6.18861448239873, 6.91340138179698,
                   5.94164388433788, 6.23638991745862, 6.31898940411710,
                   6.45247884556830, 6.58081455524297, 6.64915284801713,
                   6.07122119270245, 6.41398258148256, 6.62144271089614,
                   6.36377197712687, 6.51487678829345, 6.53418950147730,
                   6.18886469125371, 6.26341063475750, 6.83488211680259,
                   6.62699397226695, 6.41286837534735, 6.44060085001851,
                   6.48114130629288, 6.18607038456406, 6.16923370572396,
                   6.64223126283631, 6.07231852289266, 5.79043710204375,
                   6.48463886529882, 6.36263392044401, 6.11212476454494,
                   6.14573900812925, 6.12568047243240, 6.43836230231577,
                   6.02505694060219, 6.13819468942244, 6.22100593815064,
                   6.02394682666345, 5.89016573063789, 5.74448527739202,
                   5.50415294280017, 5.31883018164157, 4.87476769510305,
                   4.74386713755523, 4.60638346931628, 4.06177345572680,
                   3.73334482123538, 3.13848311672243, 2.71638862600768,
                   2.02963773590165, 1.49291145092070, 0.818343889647352, 0])

    return v1, i1, v2, i2
