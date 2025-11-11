# experiments/ramsey_experiment.py
"""Ramsey scaffold: π/2 – τ – π/2 with laser init/read. Plot contrast vs τ.
Insert PB programming + detector read where marked.
"""
import numpy as np, time

def run(ax, emit, tref_ms=2.0, pi2_us=0.2, max_tau_us=50.0, points=60):
    taus_us = np.linspace(0.1, float(max_tau_us), int(points))
    taus_s = taus_us * 1e-6
    y = []

    ax.set_title("Ramsey (π/2 – τ – π/2)")
    ax.set_xlabel("τ (s)"); ax.set_ylabel("Contrast (arb)")
    ax.grid(True)
    (line,) = ax.plot([], [], "o-")

    f0 = 2.88e9; df = 30e3  # example detuning to show oscillations

    for i, tau in enumerate(taus_us):
        if QThread.currentThread().isInterruptionRequested():
            emit(line="Interrupted by user.")
            break
        # TODO: PB: laser init → MW π/2 → dark τ → MW π/2 → laser read; read detector
        time.sleep(0.01)
        yi = 0.05*np.exp(-taus_s[i]/30e-6) * (0.5*(1+np.cos(2*np.pi*df*taus_s[i])))
        y.append(yi)

        line.set_data(taus_s[:i+1], y)
        ax.relim(); ax.autoscale()
        emit(line=f"τ = {tau:.2f} µs → C = {yi:.4f}", status=f"Point {i+1}/{len(taus_us)}", progress=(i+1)/len(taus_us))

    return {"tau_s": taus_s.tolist(), "contrast": y}