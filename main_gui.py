# main_gui.py (PyQt6)
import sys, traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from experiments.mpl_canvas import MplCanvas
import numpy as np
import csv

# Experiment runners (signature: run(ax, emit, **params))
# try:
from experiments.t1_experiment import run as run_t1
from experiments.pulsed_odmr import run as run_podmr
from experiments.rabi_experiment import run as run_rabi
from experiments.ramsey_experiment import run as run_ramsey
# from experiments.ramseyXY_experiment import run as run_ramseyXY
from experiments.hahn_experiment import run as run_hahn

# except ImportError:
#     # Dummy fallback functions for now so GUI can run without errors
#     def run_t1(): return "T1 placeholder (no experiment connected)"
#     def run_odmr(): return "ODMR placeholder (no experiment connected)"
#     def run_podmr(): return "Pulsed ODMR placeholder (no experiment connected)"
    # def run_rabi(): return "no"
    # def run_hahn(): return "no"


class EmitProxy(QObject):
    message  = pyqtSignal(str)
    status   = pyqtSignal(str)
    progress = pyqtSignal(float)
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)


class Worker(QThread):
    def __init__(self, fn, ax, params):
        super().__init__()
        self.fn = fn
        self.ax = ax
        self.params = params
        self.emitter = EmitProxy()

    def run(self):
        try:
            def emit(**kwargs):
                if "line" in kwargs:
                    self.emitter.message.emit(kwargs["line"])  # log line
                if "status" in kwargs:
                    self.emitter.status.emit(kwargs["status"])  # status text
                if "progress" in kwargs:
                    self.emitter.progress.emit(float(kwargs["progress"]))  # 0..1
            # Fresh axes each run
            self.ax.clear()
            result = self.fn(self.ax, emit, **self.params)
            self.emitter.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.emitter.error.emit(f"{e}\n{tb}")


class ExperimentTab(QWidget):
    """Reusable tab: parameters panel + run/stop + plot + log."""
    def __init__(self, title: str, runner, form_widget: QWidget):
        super().__init__()
        self.runner = runner
        self.form_widget = form_widget  # provides get_params()

        v = QVBoxLayout(self)
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Parameters box
        params_box = QGroupBox("Parameters")
        pv = QVBoxLayout(); pv.addWidget(self.form_widget); params_box.setLayout(pv)

        # Plot canvas
        self.canvas = MplCanvas(self, width=6, height=4, dpi=100)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_run = QPushButton("Run")
        self.btn_stop = QPushButton("Stop")
        self.btn_save = QPushButton("Save .csv")
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(False)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_stop)
        btn_row.addWidget(self.btn_save)

        # Status + log
        self.status_lbl = QLabel("Idle")
        self.log = QTextEdit(); self.log.setReadOnly(True)

        v.addWidget(title_lbl)
        v.addWidget(params_box)
        v.addLayout(btn_row)
        v.addWidget(self.canvas)
        v.addWidget(self.status_lbl)
        v.addWidget(self.log)

        self.worker: Worker | None = None
        self.btn_run.clicked.connect(self.start_experiment)
        self.btn_stop.clicked.connect(self.stop_experiment)
        self.btn_save.clicked.connect(self.save_csv)

    def save_csv(self):
        if self.last_result is None:
            self.log.append("No data to save.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        # Try to infer data format (x, y)
        try:
            
            if isinstance(self.last_result, dict):
                keys = list(self.last_result.keys())
                # Handle dict-like results (e.g., {'x': [...], 'y': [...]})
                x = np.array(self.last_result.get(keys[0], []))
                y = np.array(self.last_result.get(keys[1], []))
            elif isinstance(self.last_result, (list, tuple)) and len(self.last_result) == 2:
                x, y = map(np.array, self.last_result)
            else:
                self.log.append("Unsupported data format for CSV export.")
                return

            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                try:
                    writer.writerow(keys)
                except:
                    writer.writerow("x","y")
                for xi, yi in zip(x, y):
                    writer.writerow([xi, yi])

            self.log.append(f"Saved CSV to {path}")
        except Exception as e:
            self.log.append(f"Error saving CSV: {e}")


    def start_experiment(self):
        if self.worker is not None and self.worker.isRunning():
            return
        params = self.form_widget.get_params()
        self.log.append(f"Starting with params: {params}")
        self.status_lbl.setText("Running…")
        self.btn_run.setEnabled(False); self.btn_stop.setEnabled(True)

        self.worker = Worker(self.runner, self.canvas.ax, params)
        self.worker.emitter.message.connect(self.on_message)
        self.worker.emitter.status.connect(self.on_status)
        self.worker.emitter.progress.connect(self.on_progress)
        self.worker.emitter.finished.connect(self.on_finished)
        self.worker.emitter.error.connect(self.on_error)
        self.worker.start()

    def stop_experiment(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.log.append("Stop requested (will finish current step)…")

    # Slots
    def on_message(self, text: str):
        if text:
            self.log.append(text)
            self.canvas.draw()

    def on_status(self, text: str):
        self.status_lbl.setText(text)

    def on_progress(self, frac: float):
        self.status_lbl.setText(f"Running… {int(frac*100)}%")

    def on_finished(self, result):
        self.btn_run.setEnabled(True); self.btn_stop.setEnabled(False)
        self.status_lbl.setText("Done")
        self.log.append("Finished.")
        self.last_result = result
        self.btn_save.setEnabled(True)
        self.canvas.draw()

    def on_error(self, text: str):
        self.btn_run.setEnabled(True); self.btn_stop.setEnabled(False)
        self.status_lbl.setText("Error")
        self.log.append(f"<pre>{text}</pre>")
        self.canvas.draw()


# -------- Parameter Forms (per tab) --------
class T1Form(QWidget):
    def __init__(self):
        super().__init__()
        f = QFormLayout(self)
        self.tref_ms = QDoubleSpinBox(); self.tref_ms.setRange(0.2, 100.0); self.tref_ms.setValue(20.0); self.tref_ms.setSuffix(" ms")
        self.init_us = QDoubleSpinBox(); self.init_us.setRange(0.1, 5000.0); self.init_us.setValue(20.0); self.init_us.setSuffix(" µs")
        self.second_us = QDoubleSpinBox(); self.second_us.setRange(0.1, 5000.0); self.second_us.setValue(20.0); self.second_us.setSuffix(" µs")
        self.read_us = QDoubleSpinBox(); self.read_us.setRange(0.1, 5000.0); self.read_us.setValue(20.0); self.read_us.setSuffix(" µs")
        self.max_tau_us = QDoubleSpinBox(); self.max_tau_us.setRange(10.0, 1e6); self.max_tau_us.setValue(4000.0); self.max_tau_us.setSuffix(" µs")
        self.points = QSpinBox(); self.points.setRange(1, 2000); self.points.setValue(15)
        self.loops= QSpinBox(); self.loops.setRange(1,1000); self.loops.setValue(1)
        for label, w in [("Tref", self.tref_ms),("Init", self.init_us),("Second", self.second_us),("Read", self.read_us),("Max τ", self.max_tau_us),("Points", self.points),("Loops",self.loops)]:
            f.addRow(QLabel(label+":"), w)
    def get_params(self):
        return dict(tref_ms=self.tref_ms.value(), init_us=self.init_us.value(), second_us=self.second_us.value(), read_us=self.read_us.value(), max_tau_us=self.max_tau_us.value(), points=int(self.points.value()), loops=int(self.loops.value()))

class PulsedODMRForm(QWidget):
    def __init__(self):
        super().__init__()
        f = QFormLayout(self)
        self.f_start = QDoubleSpinBox(); self.f_start.setRange(1000, 4000); self.f_start.setValue(2860); self.f_start.setSuffix(" MHz")
        self.f_stop  = QDoubleSpinBox(); self.f_stop .setRange(1000, 4000); self.f_stop .setValue(2880); self.f_stop .setSuffix(" MHz")
        self.points  = QSpinBox(); self.points .setRange(1, 2001);   self.points .setValue(31)
        self.dbm = QDoubleSpinBox(); self.dbm.setRange(-40.0,10.0); self.dbm.setValue(-20.0); self.dbm.setSuffix(" dBm")
        self.tref_us = QDoubleSpinBox(); self.tref_us.setRange(0.2, 1000000.0); self.tref_us.setValue(5000.0); self.tref_us.setSuffix(" µs")
        self.pulse_us   = QDoubleSpinBox(); self.pulse_us  .setRange(0.01, 1000.0); self.pulse_us.setValue(25); self.pulse_us.setSuffix(" µs")
        self.loops= QSpinBox(); self.loops.setRange(1,1000); self.loops.setValue(3)
        for label, w in [("Start f", self.f_start),("Stop f", self.f_stop),("f points", self.points),("MW power", self.dbm),("Tref", self.tref_us),("Laser/MW pulse", self.pulse_us),("Loops",self.loops)]:
            f.addRow(QLabel(label+":"), w)
    def get_params(self):
        return dict(f_start_MHz=self.f_start.value(), f_stop_MHz=self.f_stop.value(), points=int(self.points.value()), dbm=self.dbm.value(), tref_us=self.tref_us.value(), pulse_us=self.pulse_us.value(), loops=int(self.loops.value()))

class RabiForm(QWidget):
    def __init__(self):
        super().__init__()
        f= QFormLayout(self)
        self.mw_freq = QDoubleSpinBox(); self.mw_freq.setRange(1000,4000); self.mw_freq.setValue(2870); self.mw_freq.setSuffix(" MHz")
        self.dbm = QDoubleSpinBox(); self.dbm.setRange(-40.0,15.0); self.dbm.setValue(-20.0); self.dbm.setSuffix(" dBm")
        self.N = QSpinBox(); self.N.setRange(1,500); self.N.setValue(250)
        self.max_mw_tau_us = QDoubleSpinBox(); self.max_mw_tau_us.setRange(0.01,10); self.max_mw_tau_us.setValue(5.0); self.max_mw_tau_us.setSuffix(" µs")
        self.min_pad_tau_us = QDoubleSpinBox(); self.min_pad_tau_us.setRange(0.01,10); self.min_pad_tau_us.setValue(5.0); self.min_pad_tau_us.setSuffix(" µs")
        self.laser_pulse_us = QDoubleSpinBox(); self.laser_pulse_us.setRange(5,50); self.laser_pulse_us.setValue(10); self.laser_pulse_us.setSuffix(" µs")
        self.points  = QSpinBox(); self.points .setRange(1, 2001);   self.points .setValue(31)
        self.loops= QSpinBox(); self.loops.setRange(1,1000); self.loops.setValue(3)
        for label,w in [("MW freq", self.mw_freq), ("MW power", self.dbm), ("N", self.N), ("Max MW τ", self.max_mw_tau_us), ("Padding", self.min_pad_tau_us), ("Laser pulse",self.laser_pulse_us),("Points",self.points),("Loops",self.loops)]:
            f.addRow(QLabel(label+":"), w)
    def get_params(self):
        return dict(mw_freq_MHz=self.mw_freq.value(), dBm=self.dbm.value(),N=int(self.N.value()),max_mw_tau_us=self.max_mw_tau_us.value(), min_padding_us=self.min_pad_tau_us.value(), las_pulse_us=self.laser_pulse_us.value(), points=int(self.points.value()),loops=int(self.loops.value()))

class RamseyForm(QWidget):
    def __init__(self):
        super().__init__()
        f = QFormLayout(self)
        self.tref_ms = QDoubleSpinBox(); self.tref_ms.setRange(0.2, 100.0); self.tref_ms.setValue(2.0); self.tref_ms.setSuffix(" ms")
        self.pi2_us  = QDoubleSpinBox(); self.pi2_us .setRange(0.01, 5000.0); self.pi2_us.setValue(0.2); self.pi2_us.setSuffix(" µs")
        self.max_tau_us = QDoubleSpinBox(); self.max_tau_us.setRange(0.1, 1e6); self.max_tau_us.setValue(50.0); self.max_tau_us.setSuffix(" µs")
        self.points = QSpinBox(); self.points.setRange(3, 5000); self.points.setValue(60)
        for label, w in [("Tref", self.tref_ms),("π/2", self.pi2_us),("Max τ", self.max_tau_us),("Points", self.points)]:
            f.addRow(QLabel(label+":"), w)
    def get_params(self):
        return dict(tref_ms=self.tref_ms.value(), pi2_us=self.pi2_us.value(), max_tau_us=self.max_tau_us.value(), points=int(self.points.value()))

class RamseyXYForm(QWidget):
    def __init__(self):
        super():__init__()
        #put shit here
    def get_params(self):
        return #shit here

class T2Form(QWidget):
    def __init__(self):
        super().__init__()
        f = QFormLayout(self)
        self.tref_ms = QDoubleSpinBox(); self.tref_ms.setRange(0.2, 100.0); self.tref_ms.setValue(2.0); self.tref_ms.setSuffix(" ms")
        self.pi_us   = QDoubleSpinBox(); self.pi_us  .setRange(0.01, 5000.0); self.pi_us.setValue(0.4); self.pi_us.setSuffix(" µs")
        self.max_tau_us = QDoubleSpinBox(); self.max_tau_us.setRange(0.1, 1e6); self.max_tau_us.setValue(200.0); self.max_tau_us.setSuffix(" µs")
        self.points = QSpinBox(); self.points.setRange(3, 5000); self.points.setValue(80)
        for label, w in [("Tref", self.tref_ms),("π", self.pi_us),("Max τ", self.max_tau_us),("Points", self.points)]:
            f.addRow(QLabel(label+":"), w)
    def get_params(self):
        return dict(tref_ms=self.tref_ms.value(), pi_us=self.pi_us.value(), max_tau_us=self.max_tau_us.value(), points=int(self.points.value()))


class NVGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NV Center Experiment Controller")
        self.setGeometry(100, 100, 1100, 800)

        tabs = QTabWidget()
        tabs.addTab(ExperimentTab("T1 (3-pulse)", run_t1, T1Form()), "T1")
        tabs.addTab(ExperimentTab("Pulsed ODMR", run_podmr, PulsedODMRForm()), "Pulsed ODMR")
        tabs.addTab(ExperimentTab("Rabi", run_rabi, RabiForm()), "Rabi")
        tabs.addTab(ExperimentTab("Ramsey", run_ramsey, RamseyForm()), "Ramsey")
        tabs.addTab(ExperimentTab("Hahn", run_hahn, T2Form()), "Hahn")

        self.last_result = None
        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = NVGui()
    w.show()
    sys.exit(app.exec())
