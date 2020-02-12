#!/usr/bin/python
import time
from global_logger import logger
from global_param import  table
from pb_interface import PB_interface

pb = PB_interface()

keys = table.keys() 
keys.sort() 

class EVState():
    def __init__(self):
        self.door_state = "unknow"
        self.current_floor = "unknow"
        self.timeStamp = time.time()
        self.pb_state = dict()
        for i in keys:
            self.pb_state[i] = "UNKNOW"
    def is_diff_from(self, new_state): # Compare
        if self.door_state != new_state.door_state or self.current_floor != new_state.current_floor:
            return True
        for i in keys:
            if self.pb_state[i] != new_state.pb_state[i]:
                return True
        return False
    def __str__(self):
        output = ""
        for i in keys:
            msg = i
            while len(msg) < 8:
                msg += " "
            output += (msg + self.pb_state[i] + '\n')
        output += ("Door State : " +  self.door_state + '\n')
        output += ("Current Floor : " +  self.current_floor + '\n')
        return output  
ev_state = EVState()
while True:
    volatile_state = EVState()
    for i in keys:
        gpio_state = pb.EVledRead(i)
        if gpio_state == 1:
            volatile_state.pb_state[i] = "ON"
        elif gpio_state == 0:
            volatile_state.pb_state[i] = "OFF"
        if gpio_state == -1 :
            volatile_state.pb_state[i] = "ERROR"
    volatile_state.timeStamp = time.time()

    if ev_state.is_diff_from(volatile_state):
        print "==============="
        print ""
        print "Wall Time: ", volatile_state.timeStamp
        print "delta T : ", time.time() - ev_state.timeStamp
        print ""
        ev_state = volatile_state # Update state
        print ev_state
    time.sleep(0.1)
