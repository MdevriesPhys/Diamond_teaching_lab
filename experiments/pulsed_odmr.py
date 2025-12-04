# experiments/pulsed_odmr.py
"""Pulsed ODMR scaffold: program PB for init/read + short MW pulse, read signal.
Plug in your PB + detector calls where noted.
"""
import time
import numpy as np
from spinapi import *
from hardware.sr830_control import init_sr830, sr830_read_R
from hardware.pulseblaster_control import pb_init_simple
from hardware.windfreak_control import WindfreakSynth
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread

# Channels (edit to match wiring)
CH_REF = (1 << 0)  # TTL to LIA
CH_LASER   = (1 << 1)  # TTL to laser
CH_MW_I = (1<<2) #TTL to I channel MW

def pulse_creation(tref_us:float, pulse_us:float):
    #need values in ns, not us
    pulse_ns=pulse_us*1000
    on_selector_dict = {1:CH_LASER,-1:CH_MW_I}
    i=0
    a=1
    ref_us=tref_us/2
    N_pulse=ref_us/pulse_us
    if ref_us%pulse_us!=0:
        raise ValueError("Tref/2 is not cleanly divisible by pulse length, fix it")
    N_pulse=int(N_pulse)
    
    pb_start_programming(PULSE_PROGRAM)
    while i<N_pulse:
        pb_inst_pbonly(CH_REF|on_selector_dict[a],CONTINUE,0,pulse_ns)
        a=a*-1
        i=i+1
    i=0
    while i<N_pulse-1:
        if a==-1:
            pb_inst_pbonly(0, CONTINUE, 0, pulse_ns)
        else:
            pb_inst_pbonly(CH_LASER,CONTINUE,0, pulse_ns)
        a=a*-1
        i=i+1
    if a==-1:
        pb_inst_pbonly(0, BRANCH,0, pulse_ns)
    else:
        pb_inst_pbonly(CH_LASER,CONTINUE,0,pulse_ns)
        pb_inst_pbonly(0,BRANCH,0,pulse_ns)
    pb_stop_programming()


def run(ax, emit, f_start_MHz=2.86, f_stop_MHz=2.90,dbm=-35.0, points=61,tref_us=250., pulse_us=5, loops=1):
    # Init hardware
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    mw=WindfreakSynth()
    wait_s = max(1, 15 * float(tau_LI_s))
    
    f = np.linspace(f_start_MHz*1e6, f_stop_MHz*1e6, int(points))
    f=f[::-1]
    C = []
    ax.set_title("Pulsed ODMR")
    ax.set_xlabel("MW frequency (Hz)")
    ax.set_ylabel("Contrast (arb)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o")
    try:
        pb_stop()
        pb_reset()

        loop_count=0
        fvals=[]
        Rvals=[]
        while loop_count<loops:

            for i, fi in enumerate(f):
                if QThread.currentThread().isInterruptionRequested():
                    emit(line="Interrupted by user.")
                    break
                pulse_creation(float(tref_us),float(pulse_us))
                pb_start()
                mw.set_freq(1,fi)
                mw.set_power(1,dbm)
                mw.rf_on(1)
                time.sleep(wait_s)

                R=sr830_read_R(li)
                Rvals.append(R)
                fvals.append(fi)

                line.set_data(fvals,Rvals)
                ax.relim(); ax.autoscale()
                emit(line=f"f = {fi/1e9:.6f} GHz → R = {R:.4f} V", status=f"Point {(loop_count*len(f)+i+1)} / {(len(f)*loops)}", progress=((loop_count*len(f))+i+1)/(loops*len(f)))
                
                pb_stop()
                pb_reset()
                time.sleep(wait_s)

            loop_count=loop_count+1

    finally:
        try: pb_stop(); pb_reset(); pb_close()
        except: pass
        try: li.close(); rm.close()
        except: pass
        try: mw.close()
        except: pass

    return {"freq_Hz": fvals, "contrast": Rvals}
