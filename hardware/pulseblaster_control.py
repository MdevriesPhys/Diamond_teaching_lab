from spinapi import *

CLOCK_MHZ = 100.0

def pb_init_simple(board=0, clock_mhz=CLOCK_MHZ):
    pb_select_board(board)
    pb_init()
    pb_core_clock(clock_mhz)

def pb_start_run():
    pb_start()

def pb_stop_run():
    pb_stop()

def pb_reset_close():
    try:
        pb_reset()
    finally:
        try:
            pb_close()
        except:
            pass