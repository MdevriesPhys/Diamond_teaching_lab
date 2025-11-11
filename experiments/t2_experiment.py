# experiments/t2_experiment.py
"""Hahn-echo (T2) scaffold: π/2 – τ – π – τ – read; plot echo amplitude vs τ.
Insert PB programming + detector read where marked.
"""
import numpy as np, time

def run(ax, emit, tref_ms=2.0, pi_us=0.4, max_tau_us=200.0, points=80):
    taus_us = np.linspace(0.5, float(max_tau_us), int(points))
    taus_s = taus_us * 1e-6
    y = []

    ax.set_title("Hahn Echo T₂")
    ax.set_xlabel("τ (s)"); ax.set_ylabel("Echo amplitude (arb)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o-")

    for i, tau in enumerate(taus_us):
        if QThread.currentThread().isInterruptionRequested():
            emit(line="Interrupted by user.")
            break
        # TODO: PB: laser init → π/2 → τ → π → τ → laser read; read detector
        time.sleep(0.015)
        yi = 0.06*np.exp(-(taus_s[i]/120e-6)**2)
        y.append(yi)

        line.set_data(taus_s[:i+1], y)
        ax.relim(); ax.autoscale()
        emit(line=f"τ = {tau:.1f} µs → Echo = {yi:.4f}", status=f"Point {i+1}/{len(taus_us)}", progress=(i+1)/len(taus_us))

    return {"tau_s": taus_s.tolist(), "echo": y}