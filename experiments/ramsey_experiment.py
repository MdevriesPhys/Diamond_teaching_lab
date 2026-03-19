# experiments/ramsey_experiment.py
"""
Ramsey experiment for the same GUI / hardware style as pulsed_odmr.py

Sequence in signal half-cycle:
    laser init  -> wait -> pi/2 -> tau -> pi/2 -> laser readout

Sequence in reference half-cycle:
    laser init  -> wait ->      no MW      -> laser readout

CH_REF is high during signal half-cycle and low during reference half-cycle.
"""

import time
import numpy as np
from spinapi import *
from hardware.sr830_control import init_sr830, sr830_read_R
from hardware.pulseblaster_control import pb_init_simple
from hardware.windfreak_control import WindfreakSynth
from PyQt6.QtCore import QThread

# Channels
CH_REF   = (1 << 0)   # TTL to lock-in reference
CH_LASER = (1 << 1)   # TTL to laser
CH_MW_I  = (1 << 2)   # TTL to MW switch / I channel


def _ns(x_us: float) -> float:
    return float(x_us) * 1000.0


def stop_pulse():
    pb_start_programming(PULSE_PROGRAM)
    pb_inst_pbonly(0, BRANCH, 0, 100.0)
    pb_stop_programming()


def ramsey_pulse_creation(
    tref_us: float,
    pi2_us: float,
    tau_us: float,
    laser_init_us: float = 5.0,
    readout_us: float = 5.0,
    pre_wait_us: float = 1.0,
    post_wait_us: float = 1.0,
):
    """
    Build one repeating lock-in-modulated Ramsey sequence.

    Signal half:
        CH_REF high
        laser init -> wait -> pi/2 -> tau -> pi/2 -> wait -> readout laser

    Reference half:
        CH_REF low
        laser init -> same waits -> no MW -> readout laser
    """

    half_us = tref_us / 2.0

    signal_used = (
        laser_init_us
        + pre_wait_us
        + pi2_us
        + tau_us
        + pi2_us
        + post_wait_us
        + readout_us
    )

    ref_used = (
        laser_init_us
        + pre_wait_us
        + post_wait_us
        + readout_us
    )

    if signal_used >= half_us:
        raise ValueError(
            f"Signal half-cycle too short: need {signal_used:.3f} us, have {half_us:.3f} us. "
            "Increase tref_ms or reduce tau/pi2."
        )
    if ref_used >= half_us:
        raise ValueError(
            f"Reference half-cycle too short: need {ref_used:.3f} us, have {half_us:.3f} us."
        )

    signal_pad = half_us - signal_used
    ref_pad = half_us - ref_used

    pb_start_programming(PULSE_PROGRAM)

    # ----- signal half: CH_REF high -----
    pb_inst_pbonly(CH_REF | CH_LASER, CONTINUE, 0, _ns(laser_init_us))
    pb_inst_pbonly(CH_REF, CONTINUE, 0, _ns(pre_wait_us))
    pb_inst_pbonly(CH_REF | CH_MW_I, CONTINUE, 0, _ns(pi2_us))
    pb_inst_pbonly(CH_REF, CONTINUE, 0, _ns(tau_us))
    pb_inst_pbonly(CH_REF | CH_MW_I, CONTINUE, 0, _ns(pi2_us))
    pb_inst_pbonly(CH_REF, CONTINUE, 0, _ns(post_wait_us))
    pb_inst_pbonly(CH_REF | CH_LASER, CONTINUE, 0, _ns(readout_us))
    pb_inst_pbonly(CH_REF, CONTINUE, 0, _ns(signal_pad))

    # ----- reference half: CH_REF low -----
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, _ns(laser_init_us))
    pb_inst_pbonly(0, CONTINUE, 0, _ns(pre_wait_us))
    # no MW in reference half
    pb_inst_pbonly(0, CONTINUE, 0, _ns(post_wait_us + 2 * pi2_us + tau_us))
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, _ns(readout_us))
    pb_inst_pbonly(0, BRANCH, 0, _ns(ref_pad))

    pb_stop_programming()


def run(
    ax,
    emit,
    f_MHz=2870.0,
    dbm=-35.0,
    points=61,
    tref_us=1000.0,
    pi2_us=0.05,
    max_tau_us=10.0,
    loops=1,
    laser_init_us=5.0,
    readout_us=5.0,
    pre_wait_us=1.0,
    post_wait_us=1.0,
):
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    mw = WindfreakSynth()

    wait_s = max(1, 15 * float(tau_LI_s))
    taus = np.linspace(0.05, float(max_tau_us), int(points))

    ax.set_title("Ramsey")
    ax.set_xlabel("Tau (us)")
    ax.set_ylabel("R (V)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o-")

    mw.set_power(1, dbm)
    mw.set_freq(1, f_MHz * 1e6)

    tau_vals = []
    R_vals = []
    mw_on_flag = False

    try:
        pb_stop()
        pb_reset()

        loop_count = 0
        while loop_count < loops:
            for i, tau_us in enumerate(taus):
                if QThread.currentThread().isInterruptionRequested():
                    emit(line="Interrupted by user.")
                    break

                ramsey_pulse_creation(
                    tref_us=float(tref_us),
                    pi2_us=float(pi2_us),
                    tau_us=float(tau_us),
                    laser_init_us=float(laser_init_us),
                    readout_us=float(readout_us),
                    pre_wait_us=float(pre_wait_us),
                    post_wait_us=float(post_wait_us),
                )

                if not mw_on_flag:
                    mw.rf_on(1)
                    mw_on_flag = True

                pb_start()
                time.sleep(wait_s)

                R = sr830_read_R(li)
                tau_vals.append(tau_us)
                R_vals.append(R)

                line.set_data(tau_vals, R_vals)
                ax.relim()
                ax.autoscale()

                emit(
                    line=f"tau = {tau_us:.4f} us -> R = {R:.4f} V",
                    status=f"Point {(loop_count * len(taus) + i + 1)} / {(len(taus) * loops)}",
                    progress=((loop_count * len(taus)) + i + 1) / (loops * len(taus)),
                )

                pb_stop()
                pb_reset()
                stop_pulse()
                pb_start()
                time.sleep(wait_s)
                pb_stop()
                pb_reset()

            loop_count += 1

        mw.rf_off(1)
        mw_on_flag = False

    finally:
        try:
            pb_stop()
            pb_reset()
            pb_close()
        except:
            pass
        try:
            li.close()
            rm.close()
        except:
            pass
        try:
            mw.close()
        except:
            pass

    return {"tau_us": tau_vals, "R_V": R_vals}