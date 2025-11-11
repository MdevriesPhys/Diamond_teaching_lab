# experiments/t1_experiment.py
import time
import numpy as np
from spinapi import *

# If you prefer, import tiny helpers:
# from hardware.pulseblaster_control import pb_init_simple, pb_start_run, pb_stop_run, pb_reset_close
# from hardware.sr830_control import sr830_connect, sr830_read_R

# --- Channels (edit if needed) ---
CH_LASER = (1 << 0)   # TTL to AOM / laser
CH_REF   = (1 << 1)   # TTL to SR830 Ref In

# --- Defaults ---
PB_CLOCK_MHZ   = 100.0
TREF_MS        = 4.0               # 250 Hz reference
INIT_US        = 10.0              # Pulse 1 (first half)
SECOND_US      = 8.0               # Pulse 2 (second half, before τ)
READ_US        = 5.0               # Pulse 3 (after τ)
TAUS_US        = np.linspace(10, 1000, 15)

SR830_ADDR     = "GPIB0::1::INSTR"
SR830_OFLT_IDX = 6                 # 10 ms time constant
SETTLE_FACTOR  = 5.0               # ~5× τ_LI wait per τ

# --- SR830 quick helpers (inline to keep dependencies small) ---
import pyvisa
_TC_TABLE = {
    0:10e-6, 1:30e-6, 2:100e-6, 3:300e-6, 4:1e-3, 5:3e-3, 6:10e-3, 7:30e-3,
    8:100e-3, 9:300e-3, 10:1.0, 11:3.0, 12:10.0, 13:30.0, 14:100.0, 15:300.0,
    16:1000.0, 17:3000.0, 18:10000.0, 19:30000.0
}
def _sr830_connect(address=SR830_ADDR, oflt_index=SR830_OFLT_IDX):
    rm = pyvisa.ResourceManager()
    li = rm.open_resource(address, timeout=5000)
    li.write("OUTX 1"); li.write("FMOD 0"); li.write("RSLP 1"); li.write("HARM 1")
    li.write("ISRC 0"); li.write("ICPL 0"); li.write("OFSL 3"); li.write(f"OFLT {oflt_index}")
    return rm, li, _TC_TABLE.get(oflt_index, 0.010)
def _sr830_read_R(li): return float(li.query("OUTP? 3"))

# --- PulseBlaster programming: keep REF HIGH first half; in second half do SECOND + τ + READ ---
def _program_three_pulse_sequence(tau_us: float, tref_ms: float, init_us: float, second_us: float, read_us: float):
    half_us = (tref_ms * 1000.0) / 2.0
    if init_us > half_us:
        raise ValueError("INIT_US longer than first half of Tref.")
    if second_us + tau_us + read_us > half_us:
        raise ValueError("SECOND + τ + READ must fit within the second half")

    high_base_us = half_us - init_us
    low_after_read_us = half_us - (second_us + tau_us + read_us)

    pb_start_programming(PULSE_PROGRAM)
    # First half (REF HIGH): baseline, then INIT pulse
    pb_inst_pbonly(CH_REF, CONTINUE, 0, high_base_us)
    pb_inst_pbonly(CH_REF | CH_LASER, CONTINUE, 0, init_us)
    # Second half (REF LOW): SECOND, τ (dark), READ, remainder
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, second_us)
    if tau_us > 0:
        pb_inst_pbonly(0, CONTINUE, 0, tau_us)
    pb_inst_pbonly(CH_LASER, CONTINUE, 0, read_us)
    pb_inst_pbonly(0, BRANCH, 0, max(1.0, low_after_read_us))
    pb_stop_programming()

def run(ax, emit):
    """
    Experiment entry point for the T1 tab.
    `ax`: Matplotlib axes to plot into.
    `emit(...)`: call with line=..., status=..., progress=... for GUI updates.
    """
    # Init PulseBlaster
    pb_select_board(0); pb_init(); pb_core_clock(PB_CLOCK_MHZ)

    # Init SR830
    rm, li, tau_LI_s = _sr830_connect(SR830_ADDR, SR830_OFLT_IDX)
    wait_s = max(0.02, SETTLE_FACTOR * tau_LI_s)

    taus_us = np.array(TAUS_US, dtype=float)
    taus_s = taus_us * 1e-6
    Rvals = []

    # Prepare plot
    ax.clear()
    ax.set_title("All-optical T₁ (3-pulse)")
    ax.set_xlabel("τ (s)")
    ax.set_ylabel("R (V)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o-")

    try:
        # Prime with first τ
        _program_three_pulse_sequence(taus_us[0], TREF_MS, INIT_US, SECOND_US, READ_US)
        pb_start()
        time.sleep(max(wait_s, 2 * (TREF_MS / 1000.0)))

        for i, tau in enumerate(taus_us):
            if QThread.currentThread().isInterruptionRequested():
                emit(line="Interrupted by user.")
                break

            pb_stop()
            _program_three_pulse_sequence(tau, TREF_MS, INIT_US, SECOND_US, READ_US)
            pb_start()

            time.sleep(wait_s)              # let lock-in settle
            R = _sr830_read_R(li)
            Rvals.append(R)

            # Update plot incrementally
            line.set_data(taus_s[:i+1], Rvals)
            ax.relim(); ax.autoscale()
            emit(line=f"τ = {tau:.1f} µs → R = {R:.6e} V",
                 status=f"Point {i+1}/{len(taus_us)}",
                 progress=(i+1)/len(taus_us))

    finally:
        try: pb_stop()
        except: pass
        try: pb_reset()
        except: pass
        try: pb_close()
        except: pass
        try: li.close(); rm.close()
        except: pass

    return {"tau_s": taus_s.tolist(), "R_V": Rvals}
