# experiments/ramsey_experiment.py
# experiments/rabi_experiment.py
"""Rabi measurement
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

def pulse_creation(tref_us:float, tau_mw_us:float, tau_pad_us:float, pulse_us:float):
    #need values in ns, not us

    pb_stop_programming()


def run(ax, emit, f_start_MHz=2.86, f_stop_MHz=2.90,dbm=-35.0, points=61,tref_us=250., pulse_us=5, loops=1):
    # Init hardware
    pb_init_simple()
    rm, li, tau_LI_s = init_sr830()
    mw=WindfreakSynth()
    wait_s = max(1, 15 * float(tau_LI_s))
    
    f = np.linspace(f_start_MHz*1e6, f_stop_MHz*1e6, int(points))
    C = []
    ax.set_title("Ramsey")