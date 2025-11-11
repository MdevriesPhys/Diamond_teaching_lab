# experiments/odmr_experiment.py
"""CW ODMR scaffold: sweeps MW frequency and plots live.
Plug in your MW source + detector calls where noted.
"""
import numpy as np, time

def run(ax, emit, f_start_GHz=2.86, f_stop_GHz=2.90, points=101):
    f = np.linspace(f_start_GHz*1e9, f_stop_GHz*1e9, int(points))
    y = []

    ax.set_title("ODMR")
    ax.set_xlabel("MW frequency (Hz)")
    ax.set_ylabel("Signal (arb)")
    ax.grid(True)
    (line,) = ax.plot([], [], "-")

    for i, fi in enumerate(f):
        if QThread.currentThread().isInterruptionRequested():
            emit(line="Interrupted by user.")
            break
        # TODO: set MW frequency to fi, wait dwell, read detector
        time.sleep(0.01)
        # Fake dip near 2.88 GHz
        yi = 1.0 - 0.02*np.exp(-((fi-2.88e9)/3e6)**2)
        y.append(yi)

        line.set_data(f[:i+1], y)
        ax.relim(); ax.autoscale()
        emit(line=f"f = {fi/1e9:.6f} GHz → {yi:.4f}", status=f"Point {i+1}/{len(f)}", progress=(i+1)/len(f))

    return {"freq_Hz": f.tolist(), "signal": y}