"""
Faster ways to calculate single diode model currents and voltages using
methods from J.W. Bishop (Solar Cells, 1988).
"""

from collections import OrderedDict
import numpy as np
try:
    from scipy.optimize import brentq, newton
except ImportError:
    brentq = NotImplemented
    newton = NotImplemented

# TODO: update pvsystem.i_from_v and v_from_i to use "gold" method by default


def est_voc(photocurrent, saturation_current, nNsVth):
    """
    Rough estimate of open circuit voltage useful for bounding searches for
    ``i`` of ``v`` when using :func:`~pvlib.pvsystem.singlediode`.

    :param numeric photocurrent: photo-generated current [A]
    :param numeric saturation_current: diode one reverse saturation current [A]
    :param numeric nNsVth: product of thermal voltage ``Vth`` [V], diode
        ideality factor ``n``, and number of series cells ``Ns``
    :returns: rough estimate of open circuit voltage [V]

    The equation is from [1].

    .. math::

        V_{oc, est}=n Ns V_{th} \\log \\left( \\frac{I_L}{I_0} + 1 \\right)

    [1] http://www.pveducation.org/pvcdrom/open-circuit-voltage
    """

    return nNsVth * np.log(photocurrent / saturation_current + 1.0)


def bishop88(vd, photocurrent, saturation_current, resistance_series,
             resistance_shunt, nNsVth, gradients=False):
    """
    Explicit calculation single-diode-model (SDM) currents and voltages using
    diode junction voltages [1].

    [1] "Computer simulation of the effects of electrical mismatches in
    photovoltaic cell interconnection circuits" JW Bishop, Solar Cell (1988)
    https://doi.org/10.1016/0379-6787(88)90059-2

    :param numeric vd: diode voltages [V]
    :param numeric photocurrent: photo-generated current [A]
    :param numeric saturation_current: diode one reverse saturation current [A]
    :param numeric resistance_series: series resitance [ohms]
    :param numeric resistance_shunt: shunt resitance [ohms]
    :param numeric nNsVth: product of thermal voltage ``Vth`` [V], diode
        ideality factor ``n``, and number of series cells ``Ns``
    :param bool gradients: default returns only i, v, and p, returns gradients
        if true
    :returns: tuple containing currents [A], voltages [V], power [W],
        gradient ``di/dvd``, gradient ``dv/dvd``, gradient ``di/dv``,
        gradient ``dp/dv``, and gradient ``d2p/dv/dvd``
    """
    a = np.exp(vd / nNsVth)
    b = 1.0 / resistance_shunt
    i = photocurrent - saturation_current * (a - 1.0) - vd * b
    v = vd - i * resistance_series
    retval = (i, v, i*v)
    if gradients:
        c = saturation_current * a / nNsVth
        grad_i = - c - b  # di/dvd
        grad_v = 1.0 - grad_i * resistance_series  # dv/dvd
        # dp/dv = d(iv)/dv = v * di/dv + i
        grad = grad_i / grad_v  # di/dv
        grad_p = v * grad + i  # dp/dv
        grad2i = -c / nNsVth  # d2i/dvd
        grad2v = -grad2i * resistance_series  # d2v/dvd
        grad2p = (
            grad_v * grad + v * (grad2i/grad_v - grad_i*grad2v/grad_v**2) + grad_i
        )  # d2p/dv/dvd
        retval += (grad_i, grad_v, grad, grad_p, grad2p)
    return retval


def slow_i_from_v(v, photocurrent, saturation_current, resistance_series,
                  resistance_shunt, nNsVth):
    """
    This is a slow but reliable way to find current given any voltage.
    """
    if brentq is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    # first bound the search using voc
    voc_est = est_voc(photocurrent, saturation_current, nNsVth)
    vd = brentq(lambda x, *a: v - bishop88(x, *a)[1], 0.0, voc_est, args)
    return bishop88(vd, *args)[0]


def fast_i_from_v(v, photocurrent, saturation_current, resistance_series,
                  resistance_shunt, nNsVth):
    """
    This is a fast but unreliable way to find current given any voltage.
    """
    if newton is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    vd = newton(func=lambda x, *a: bishop88(x, *a)[1] - v, x0=v,
                fprime=lambda x, *a: bishop88(x, *a, gradients=True)[4],
                args=args)
    return bishop88(vd, *args)[0]


def slow_v_from_i(i, photocurrent, saturation_current, resistance_series,
                  resistance_shunt, nNsVth):
    """
    This is a slow but reliable way to find voltage given any current.
    """
    if brentq is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    # first bound the search using voc
    voc_est = est_voc(photocurrent, saturation_current, nNsVth)
    vd = brentq(lambda x, *a: i - bishop88(x, *a)[0], 0.0, voc_est, args)
    return bishop88(vd, *args)[1]


def fast_v_from_i(i, photocurrent, saturation_current, resistance_series,
                  resistance_shunt, nNsVth):
    """
    This is a fast but unreliable way to find voltage given any current.
    """
    if newton is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    # first bound the search using voc
    voc_est = est_voc(photocurrent, saturation_current, nNsVth)
    vd = newton(func=lambda x, *a: bishop88(x, *a)[0] - i, x0=voc_est,
                fprime=lambda x, *a: bishop88(x, *a, gradients=True)[3],
                args=args)
    return bishop88(vd, *args)[1]


def slow_mppt(photocurrent, saturation_current, resistance_series,
              resistance_shunt, nNsVth):
    """
    This is a slow but reliable way to find mpp.
    """
    if brentq is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    # first bound the search using voc
    voc_est = est_voc(photocurrent, saturation_current, nNsVth)
    vd = brentq(lambda x, *a: bishop88(x, *a, gradients=True)[6], 0.0, voc_est,
                args)
    return bishop88(vd, *args)


def fast_mppt(photocurrent, saturation_current, resistance_series,
              resistance_shunt, nNsVth):
    """
    This is a fast but unreliable way to find mpp.
    """
    if newton is NotImplemented:
        raise ImportError('This function requires scipy')
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    # first bound the search using voc
    voc_est = est_voc(photocurrent, saturation_current, nNsVth)
    vd = newton(
        func=lambda x, *a: bishop88(x, *a, gradients=True)[6], x0=voc_est,
        fprime=lambda x, *a: bishop88(x, *a, gradients=True)[7], args=args
    )
    return bishop88(vd, *args)


def slower_way(photocurrent, saturation_current, resistance_series,
               resistance_shunt, nNsVth, ivcurve_pnts=None):
    """
    This is the slow but reliable way.
    """
    # collect args
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)
    v_oc = slow_v_from_i(0.0, *args)
    i_mp, v_mp, p_mp = slow_mppt(*args)
    out = OrderedDict()
    out['i_sc'] = slow_i_from_v(0.0, *args)
    out['v_oc'] = v_oc
    out['i_mp'] = i_mp
    out['v_mp'] = v_mp
    out['p_mp'] = p_mp
    out['i_x'] = slow_i_from_v(v_oc / 2.0, *args)
    out['i_xx'] = slow_i_from_v((v_oc + v_mp) / 2.0, *args)
    # calculate the IV curve if requested using bishop88
    if ivcurve_pnts:
        vd = v_oc * (
            (11.0 - np.logspace(np.log10(11.0), 0.0, ivcurve_pnts)) / 10.0
        )
        i, v, p = bishop88(vd, *args)
        out['i'] = i
        out['v'] = v
        out['p'] = p
    return out


def faster_way(photocurrent, saturation_current, resistance_series,
               resistance_shunt, nNsVth, ivcurve_pnts=None):
    """a faster way"""
    args = (photocurrent, saturation_current, resistance_series,
            resistance_shunt, nNsVth)  # collect args
    v_oc = fast_v_from_i(0.0, *args)
    i_mp, v_mp, p_mp = fast_mppt(*args)
    out = OrderedDict()
    out['i_sc'] = fast_i_from_v(0.0, *args)
    out['v_oc'] = v_oc
    out['i_mp'] = i_mp
    out['v_mp'] = v_mp
    out['p_mp'] = p_mp
    out['i_x'] = fast_i_from_v(v_oc / 2.0, *args)
    out['i_xx'] = fast_i_from_v((v_oc + v_mp) / 2.0, *args)
    # calculate the IV curve if requested using bishop88
    if ivcurve_pnts:
        vd = v_oc * (
            (11.0 - np.logspace(np.log10(11.0), 0.0, ivcurve_pnts)) / 10.0
        )
        i, v, p = bishop88(vd, *args)
        out['i'] = i
        out['v'] = v
        out['p'] = p
    return out
