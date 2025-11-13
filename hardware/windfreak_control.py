from windfreak import SynthHD #install this!


class WindfreakSynth:

    def __init__(self, serial="COM3"):
        """Connect to SynthHD Pro. If multiple units, specify serial number."""
        self.dev= SynthHD(serial)
        self.dev.init()
        # Ensure both channels start off
        for ch in (1, 2):
            self.dev[ch - 1].enable = False

    def set_freq(self, ch: int, freq_hz: float):
        """Set output frequency for channel `ch` (1 or 2)."""
        self.dev[ch - 1].frequency = freq_hz

    def set_power(self, ch: int, dbm: float):
        """Set output power in dBm."""
        self.dev[ch - 1].power = dbm

    def rf_on(self, ch: int):
        """Turn channel ON."""
        self.dev[ch - 1].enable = True

    def rf_off(self, ch: int):
        """Turn channel OFF."""
        self.dev[ch - 1].enable = False

    def close(self):
        """Safely disable outputs and close connection."""
        for ch in (1, 2):
            self.rf_off(ch)
        self.dev.close()
        

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()