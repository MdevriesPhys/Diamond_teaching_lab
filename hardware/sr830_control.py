import pyvisa

# SR830 settings

VISA_ADDR = "GPIB0::1::INSTR"
TIME_CONST_S = 0.01       # lock-in time constant = 10 ms
SETTLE_FACTOR = 5         # wait ~5× time constant before reading

TC_TABLE={0:10e-6, 1:30e-6, 2:100e-6, 3:300e-6, 4:1e-3, 5:3e-3, 6:10e-3, 7:30e-3, 8:100e-3, 9:300e-3, 10:1, 11:3, 12:10, 13:30, 14:100, 15:300}


def init_sr830(VISA_ADDR = "GPIB0::1::INSTR"):
    rm = pyvisa.ResourceManager()
    li = rm.open_resource(VISA_ADDR, timeout=5000)
    li.clear()
    idn = li.query("*IDN?").strip()
    tc= int(li.query("OFLT?"))
    # print(f"Connected to {idn}")

    # Basic setup
    li.write("OUTX 1")      # GPIB
    li.write("FMOD 0")      # external reference
    li.write("RSLP 1")      # rising edge
    li.write("HARM 1")      # fundamental
    li.write("ISRC 0")      # input A
    # li.write("ICPL 0")      # AC coupling
    # li.write("OFSL 2")      # 24 dB/oct
    # li.write(f"OFLT {oflt_index}")      # time constant
    li.write("PHAS 0")      # phase adjust manually if needed
    return rm, li, TC_TABLE.get(tc)

def sr830_read_R(li):
    """Read lock-in magnitude R (volts)."""
    val = float(li.query("OUTP? 3"))
    return val