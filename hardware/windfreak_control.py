from windfreak import SynthHD #install this!


class WindfreakSynth:

    def __init__(self, serial=None):
        """Connect to SynthHD Pro. If multiple units, specify serial number."""
        self.dev = SynthHD(serial_number=serial)
        self.dev.connect()
        # Ensure both channels start off
        for ch in (1, 2):
            self.dev.channel[ch - 1].rf_enable = False

    def set_freq(self, ch: int, freq_hz: float):
        """Set output frequency for channel `ch` (1 or 2)."""
        self.dev.channel[ch - 1].fout = freq_hz / 1e6  # MHz

    def set_power(self, ch: int, dbm: float):
        """Set output power in dBm."""
        self.dev.channel[ch - 1].power = dbm

    def rf_on(self, ch: int):
        """Turn channel ON."""
        self.dev.channel[ch - 1].rf_enable = True

    def rf_off(self, ch: int):
        """Turn channel OFF."""
        self.dev.channel[ch - 1].rf_enable = False

    def close(self):
        """Safely disable outputs and close connection."""
        for ch in (1, 2):
            self.rf_off(ch)
        self.dev.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()