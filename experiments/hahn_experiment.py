# experiments/hahn_experiment.py
"""
Hahn echo experiment for the same GUI / hardware style as pulsed_odmr.py

Signal half-cycle:
    laser init -> wait -> pi/2 -> tau -> pi -> tau -> pi/2 -> readout laser

Reference half-cycle:
    same timing envelope, but no MW pulses
"""

import time
import numpy as np
from spinapi import *
from hardware.sr830_control import init_sr830, sr830_read_R
from hardware.pulseblaster_control import pb_init_simple
from hardware.windfreak_control import WindfreakSynth
from PyQt6.QtCore import QThread

# Channels
CH_REF   = (1 << 0)
CH_LASER = (1 << 1)
CH_MW_I  = (1 << 2)


def _ns(x_us: float) -> float:
    return float(x_us) * 1000.0


def stop_pulse():
    pb_start_programming(PULSE_PROGRAM)
    pb_inst_pbonly(0, BRANCH, 0, 100.0)
    pb_stop_programming()


def hahn_pulse_creation(
    laser_pulse_us: float,
    pad_ns: float,
    pi_ns: float,
    tau_us: float,
    N:int
    ):

    #PB needs things in ns, Hahn uses pi/2 pulses, we'll define tau as the total delay so need to halve it
    laser_pulse_ns=laser_pulse_us*1000
    tau_ns=tau_us*1000
    tau2_ns=tau_ns/2.0
    pi2_ns=pi_ns/2.0
    
    pb_start_programming(PULSE_PROGRAM)
    # ----- signal half: CH_REF high -----
    i=0
    while i<N:
        pb_inst_pbonly(CH_REF | CH_LASER, CONTINUE, 0, laser_pulse_ns)
        pb_inst_pbonly(CH_REF, CONTINUE, 0, pad_ns)
        pb_inst_pbonly(CH_REF | CH_MW_I, CONTINUE, 0, pi2_ns)
        pb_inst_pbonly(CH_REF, CONTINUE, 0, tau2_ns)
        pb_inst_pbonly(CH_REF|CH_MW_I, CONTINUE, 0, pi_ns)
        pb_inst_pbonly(CH_REF, CONTINUE, 0, tau2_ns)
        pb_inst_pbonly(CH_REF | CH_MW_I, CONTINUE, 0, pi2_ns)
        pb_inst_pbonly(CH_REF, CONTINUE, 0, pad_ns)
        i=i+1
    # ----- reference half: CH_REF low -----
    i=0
    while i<N-1:
        pb_inst_pbonly(CH_LASER, CONTINUE, 0, laser_pulse_ns)
        pb_inst_pbonly(0, CONTINUE, 0, (pad_ns+pi2_ns+tau2_ns+pi_ns+tau2_ns+pi2_ns+pad_ns))
        i=i+1
    pb_inst_pbonly(CH_LASER,CONTINUE,0,las_pulse_ns)
    pb_inst_pbonly(0, BRANCH, 0, (pad_ns+pi2_ns+tau2_ns+pi_ns+tau2_ns+pi2_ns+pad_ns))
    pb_stop_programming()


def run(ax,
        emit,
        f_MHz=2870.0,
        dbm=-35.0,
        N=250,
        laser_pulse_us=10.0,
        pad_us=5.0,
        pi_ns=800.0,
        max_tau_us=50.0,
        points=51,
        loops=3
        ):
    
    #init hardware
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    mw = WindfreakSynth()
    wait_s = max(1, 15 * float(tau_LI_s))

    #set up variables
    tau_space_us = np.linspace(0.05, float(max_tau_us), int(points))

    #set up plot
    ax.set_title("Hahn")
    ax.set_xlabel("Tau (us)")
    ax.set_ylabel("R (V)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o")

    #Do the experiment
    try:
        pb_stop()
        pb_reset()

        loop_count=0
        tau_vals = []
        R_vals = []

        mw.set_power(1, dbm)
        mw.set_freq(1, f_MHz * 1e6)
        mw.rf_on(1)

        while loop_count<loops:
            for i,ti in enumerate(tau_space_us):
                if QThread.currentThread().isInterruptionRequested():
                    emit(line="Interrupted by user.")
                    break
                
                tau_us=ti
                pulse_creation(laser_pulse_us,pad_us,pi_ns,tau_us,N)
                pb_start()
                time.sleep(wait_s)

                R=sr830_read_R(li)
                R_vals.append(R)
                tau_vals.append(ti)

                line.set_data(tau_vals,Rvals)
                ax.relim(); ax.autoscale()
                emit(line=f"{ti:.6f} us → R = {R:.4f} V", status=f"Point {(loop_count*len(tau_space_us)+i+1)} / {(len(tau_space_us)*loops)}", progress=((loop_count*len(tau_space_us))+i+1)/(loops*len(tau_space_us)))

                pb_stop()
                pb_reset()
                stop_pulse()
                pb_start()
                time.sleep(wait_s)
                pb_stop()
                pb_reset

            loop_count=loop_count+1

    finally:
        try:pb_stop();pb_reset(); pb_close()
        except:pass
        try: li.close();rm.close()
        except:pass
        try: mw.close()
        except:pass

    return {"tau_us": tau_vals, "R_V": R_vals}