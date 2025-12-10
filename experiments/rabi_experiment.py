# experiments/rabi_experiment.py
"""Rabi experiment: program PB for varying length MW pulse (MW tau) with laser init/readout
"""
import time
import numpy as np
from spinapi import *
from hardware.sr830_control import init_sr830, sr830_read_R
from hardware.pulseblaster_control import pb_init_simple
from hardware.windfreak_control import WindfreakSynth
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread

# Channels
CH_REF = (1 << 0)  # TTL to LIA
CH_LASER   = (1 << 1)  # TTL to laser
CH_MW_I = (1<<2) #TTL to I channel MW

def pulse_creation(las_pulse_us:float, tau_us:float, padding_us:float, N:int):
    #PB needs times in ns, not us
    las_pulse_ns=las_pulse_us*1000
    tau_ns=tau_us*1000
    padding_ns=padding_us*1000

    pb_start_programming(PULSE_PROGRAM)
    i=0
    while i<N:
        pb_inst_pbonly(CH_REF|CH_LASER,CONTINUE,0,las_pulse_ns)
        pb_inst_pbonly(CH_REF|CH_MW_I,CONTINUE,0,tau_ns)
        pb_inst_pbonly(CH_REF,CONTINUE,0,padding_ns)
        i=i+1
    i=0
    while i<N-1:
        pb_inst_pbonly(CH_LASER,CONTINUE,0,las_pulse_ns)
        pb_inst_pbonly(0,CONTINUE,0,tau_ns+padding_ns)
        i=i+1
    pb_inst_pbonly(CH_LASER,CONTINUE,0,las_pulse_ns)
    pb_inst_pbonly(0,BRANCH,0,padding_ns+tau_ns)
    pb_stop_programming()
    # return

def run(ax, emit, mw_freq_MHz=2870, dBm=-20.0, N=250, max_mw_tau_us=5.0, min_padding_us=5.0, las_pulse_us=10.0, points=31, loops=3):
    #init hardware
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    mw=WindfreakSynth()
    wait_s=max(1,15*float(tau_LI_s))

    tau_space_us = np.linspace(0.05,max_mw_tau_us, int(points))
    tref_us = N*(max_mw_tau_us+min_padding_us+las_pulse_us)



    ax.set_title("Rabi")
    ax.set_xlabel(r"τ ($\mu$s)")
    ax.set_ylabel("R (V)")
    ax.grid(True)
    (line,)=ax.plot([],[],"o")

    try:
        pb_stop()
        pb_reset()

        loop_count=0
        tau_vals=[]
        Rvals=[]
        while loop_count<loops:
            for i, ti in enumerate(tau_space_us):
                if QThread.currentThread().isInterruptionRequested():
                    emit(line="Interrupted by user.")
                    break

                tau_us=ti
                # padding_us=(tref_us/N)-las_pulse_us-tau_us    
                padding_us=min_padding_us
                pulse_creation(las_pulse_us,tau_us,padding_us,N)
                pb_start()

                mw.set_freq(1,mw_freq_MHz*1e6)
                mw.set_power(1,dBm)
                mw.rf_on(1)

                time.sleep(wait_s)

                R=sr830_read_R(li)
                Rvals.append(R)
                tau_vals.append(ti)

                line.set_data(tau_vals,Rvals)
                ax.relim(); ax.autoscale()
                emit(line=f"{ti:.6f} us → R = {R:.4f} V", status=f"Point {(loop_count*len(tau_space_us)+i+1)} / {(len(tau_space_us)*loops)}", progress=((loop_count*len(tau_space_us))+i+1)/(loops*len(tau_space_us)))

                pb_stop()
                pb_reset()
                time.sleep(wait_s)
            
            loop_count=loop_count+1

    finally:
        try:pb_stop(); pb_reset(); pb_close()
        except:pass
        try: li.close();rm.close()
        except:pass
        try: mw.close()
        except:pass

    return {"tau_us":tau_vals, "R_V":Rvals}