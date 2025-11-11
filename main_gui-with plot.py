# main_gui.py (PyQt6)
import sys, traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QPushButton, QLabel, QTextEdit, QHBoxLayout
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread

from experiments.mpl_canvas import MplCanvas

# Import your experiment runners (same signature: run(ax, emit))
try:
    from experiments.t1_experiment import run as run_t1
    from experiments.odmr_experiment import run as run_odmr
    from experiments.pulsed_odmr import run as run_podmr
except ImportError:
    # Dummy fallback functions for now so GUI can run without errors
    def run_t1(): return "T1 placeholder (no experiment connected)"
    def run_odmr(): return "ODMR placeholder (no experiment connected)"
    def run_podmr(): return "Pulsed ODMR placeholder (no experiment connected)"


class EmitProxy(QObject):
    """Signal interface passed to experiment code for safe UI updates."""
    message  = pyqtSignal(str)         # plain log line
    status   = pyqtSignal(str)         # status line (one-liner)
    progress = pyqtSignal(float)       # 0..1 (optional)
    finished = pyqtSignal(object)      # payload/result object
    error    = pyqtSignal(str)         # error text


class Worker(QThread):
    """Runs a callable in a thread, giving it (ax, emit)."""
    def __init__(self, fn, ax):
        super().__init__()
        self.fn = fn
        self.ax = ax
        self.emitter = EmitProxy()

    def run(self):
        try:
            # Give experiments a simple emitter; wrap their messages into signals
            def emit(**kwargs):
                if "line" in kwargs:
                    self.emitter.message.emit(kwargs["line"])
                if "status" in kwargs:
                    self.emitter.status.emit(kwargs["status"])
                if "progress" in kwargs:
                    self.emitter.progress.emit(float(kwargs["progress"]))
            # Clear axes before starting
            self.ax.clear()
            result = self.fn(self.ax, emit)
            self.emitter.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.emitter.error.emit(f"{e}\n{tb}")


class ExperimentTab(QWidget):
    """Reusable tab with: title, Run/Stop, canvas, log."""
    def __init__(self, title: str, runner):
        super().__init__()
        self.runner = runner
        self.setObjectName(title)

        # UI
        v = QVBoxLayout(self)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = MplCanvas(self, width=6, height=4, dpi=100)

        # Buttons row
        h = QHBoxLayout()
        self.btn_run  = QPushButton("Run")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        h.addWidget(self.btn_run)
        h.addWidget(self.btn_stop)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.status_lbl = QLabel("Idle")

        v.addWidget(title_lbl)
        v.addLayout(h)
        v.addWidget(self.canvas)
        v.addWidget(self.status_lbl)
        v.addWidget(self.log)

        # Worker placeholder
        self.worker: Worker | None = None

        # Connect buttons
        self.btn_run.clicked.connect(self.start_experiment)
        self.btn_stop.clicked.connect(self.stop_experiment)

    def start_experiment(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.log.append("Starting...")
        self.status_lbl.setText("Running...")
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker = Worker(self.runner, self.canvas.ax)

        # Wire signals
        self.worker.emitter.message.connect(self.on_message)
        self.worker.emitter.status.connect(self.on_status)
        self.worker.emitter.progress.connect(self.on_progress)
        self.worker.emitter.finished.connect(self.on_finished)
        self.worker.emitter.error.connect(self.on_error)

        # Redraw on a small cadence from experiment code by calling canvas.draw()
        self.worker.start()

    def stop_experiment(self):
        if self.worker and self.worker.isRunning():
            # Gentle stop: not all instrument loops are interruptible.
            # You can add a shared flag if needed; for now we just request termination.
            self.worker.requestInterruption()
            self.log.append("Stop requested (may take a moment)...")

    # Slots
    def on_message(self, text: str):
        self.log.append(text)
        # Allow experiment to refresh plot
        self.canvas.draw()

    def on_status(self, text: str):
        self.status_lbl.setText(text)

    def on_progress(self, frac: float):
        self.status_lbl.setText(f"Running... {int(frac*100)}%")

    def on_finished(self, result):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_lbl.setText("Done")
        self.log.append("Finished.")
        self.canvas.draw()

    def on_error(self, text: str):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_lbl.setText("Error")
        self.log.append(f"<pre>{text}</pre>")
        self.canvas.draw()


class NVGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NV Center Experiment Controller")
        self.setGeometry(100, 100, 1000, 700)

        tabs = QTabWidget()
        tabs.addTab(ExperimentTab("T1 (3-pulse)", run_t1), "T1")
        tabs.addTab(ExperimentTab("ODMR", run_odmr), "ODMR")
        tabs.addTab(ExperimentTab("Pulsed ODMR", run_podmr), "Pulsed ODMR")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = NVGui()
    w.show()
    sys.exit(app.exec())
