# experiments/t1_experiment.py
"""
Three-pulse all-optical T1 using PulseBlaster + SR830.
First half (Ref HIGH): one laser pulse (INIT)
Second half (Ref LOW): second laser pulse, then dark τ, then read pulse
Reads SR830 R per τ and plots live.
"""
import time
import numpy as np
from spinapi import *
from hardware.sr830_control import init_sr830, sr830_read_R, sr830_read_X
from hardware.pulseblaster_control import pb_init_simple
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread

# Channels (edit to match wiring)
CH_REF = (1 << 0)  # TTL to LIA
CH_LASER   = (1 << 1)  # TTL to laser

# Internal helpers
def _program_three_pulse_sequence(tau_us: float, tref_ms: float, init_us: float, second_us: float, read_us: float):
    half_ns = (tref_ms * 1000000.0) / 2.0
    init_ns=init_us*1000
    second_ns=second_us*1000
    read_ns=read_us*1000
    tau_ns=tau_us*1000
    if init_ns > half_ns:
        raise ValueError("INIT longer than first half")
    if second_ns + tau_ns + read_ns > half_ns:
        raise ValueError("SECOND + τ + READ must fit in second half")

    high_base_ns = half_ns - init_ns
    low_after_read_ns = half_ns - (second_ns + tau_ns + read_ns)

    pb_start_programming(PULSE_PROGRAM)
    pb_inst_pbonly(CH_LASER|CH_REF, CONTINUE, 0, init_ns)
    pb_inst_pbonly(CH_REF,CONTINUE,0,high_base_ns)
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, second_ns)
    if tau_ns > 0:
        pb_inst_pbonly(0, CONTINUE, 0, tau_ns)
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, read_ns)
    pb_inst_pbonly(0, BRANCH, 0, max(1.0, low_after_read_ns))
    pb_stop_programming()

def run(ax, emit, tref_ms=20, init_us=20.0, second_us=20.0, read_us=20.0, max_tau_us=4000.0, points=15,loops=1):
    # Init hardware
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    wait_s = max(1, 15* float(tau_LI_s))

    taus_us = np.linspace(float(init_us), float(max_tau_us), int(points))
    taus_s = taus_us * 1e-6
    Rvals = []
    tauvals=[]
    Rerrs=[]

    # Plot setup
    ax.set_title("All-optical T₁ (3-pulse)")
    ax.set_xlabel("τ (s)"); ax.set_ylabel("R (V)"); ax.grid(True)
    (line,) = ax.plot([], [], "o")
    # (errbars,) = ax.errorbars([],[],[],"+")
    loop_counter=0
    try:
        # Prime sequence
        # _program_three_pulse_sequence(taus_us[0], tref_ms, init_us, second_us, read_us)
        # time.sleep(max(wait_s, 2 * (tref_ms / 1000.0)))
        while loop_counter<loops:
            for i, tau in enumerate(taus_us):
                if QThread.currentThread().isInterruptionRequested():
                    emit(line="Interrupted by user.")
                    break

                pb_stop()
                pb_reset()
                # pb_inst_pbonly(CH_REF,CONTINUE, 0, (tref_ms * 1000000.0) / 2.0)
                # pb_inst_pbonly(0,BRANCH,0,(tref_ms * 1000000.0) / 2.0)
                time.sleep(wait_s/1.5)
                pb_stop()
                pb_reset()
                _program_three_pulse_sequence(float(tau), tref_ms, init_us, second_us, read_us)
                pb_start()
                # loop_counter=0
                # r_av=[]
                # while loop_counter<loops:
                    # time.sleep(wait_s)
                    # R = sr830_read_R(li)
                    # r_av.append(R)

                    # loop_counter=loop_counter+1

                time.sleep(wait_s)
                R=sr830_read_R(li)
                Rvals.append(R)
                # Rvals.append(np.average(r_av))
                # Rerrs.append(np.std(r_av))
                tauvals.append(tau)

                # Live plot
                line.set_data(tauvals, Rvals)
                # errbars.set_data(tauvals, Rvals,Rerrs)
                ax.relim(); ax.autoscale()
                emit(line=f"τ = {tau:.1f} µs → R = {R:.6e} V", status=f"Point {i+1}/{(len(taus_us)*loops)}", progress=((loop_counter*len(taus_us))+i+1)/(loops*len(taus_us)))
            loop_counter=loop_counter+1

    finally:
        try: pb_stop(); pb_reset(); pb_close()
        except: pass
        try: li.close(); rm.close()
        except: pass

    # return {"tau_s": taus_s.tolist(), "R_V": Rvals}
    return {"tau_s": tauvals, "R_V": Rvals}

