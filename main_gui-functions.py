# main_gui.py (PyQt6 version)
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget,QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import Qt

# Import experiment functions
# (You can comment these out if the experiment modules aren't ready yet)
try:
    from experiments.t1_experiment import run_t1_experiment
    from experiments.odmr_experiment import run_odmr_experiment
    from experiments.pulsed_odmr import run_pulsed_odmr_experiment
except ImportError:
    # Dummy fallback functions for now so GUI can run without errors
    def run_t1_experiment(): return "T1 placeholder (no experiment connected)"
    def run_odmr_experiment(): return "ODMR placeholder (no experiment connected)"
    def run_pulsed_odmr_experiment(): return "Pulsed ODMR placeholder (no experiment connected)"

# try:
#     from hardware.PB24 import *
#     from hardware.SR830 import *
#     from hardware.Windfreak import *
# except ImportError:
#     def 

class NVGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NV Center Experiment Controller")
        self.setGeometry(100, 100, 900, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Tabs ---
        self.t1_tab = self.create_tab("T1 Measurement", run_t1_experiment)
        self.odmr_tab = self.create_tab("ODMR", run_odmr_experiment)
        self.podmr_tab = self.create_tab("Pulsed ODMR", run_pulsed_odmr_experiment)

        # Add tabs to the tab widget
        self.tabs.addTab(self.t1_tab, "T1")
        self.tabs.addTab(self.odmr_tab, "ODMR")
        self.tabs.addTab(self.podmr_tab, "Pulsed ODMR")

    def create_tab(self, name, func):
        """Creates one experiment tab with a run button and live output box."""
        tab = QWidget()
        layout = QVBoxLayout()

        label = QLabel(f"{name}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        run_button = QPushButton("Run")
        output = QTextEdit()
        output.setReadOnly(True)

        def run_clicked():
            output.append(f"Running {name} experiment...")
            try:
                data = func()
                output.append("Experiment complete!\n")
                output.append(str(data))
            except Exception as e:
                output.append(f"Error: {e}\n")

        run_button.clicked.connect(run_clicked)
        layout.addWidget(label)
        layout.addWidget(run_button)
        layout.addWidget(output)
        tab.setLayout(layout)
        return tab


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NVGui()
    window.show()
    sys.exit(app.exec())
