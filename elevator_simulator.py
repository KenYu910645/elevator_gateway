#!/usr/bin/python
import os
import sys
import time
import numpy 
import curses
from std_msgs.msg import String
import rospy 

class button(object):
    def __init__(self, name, upper, lower):
        self.name = name
        self.led = 0 # 0 -> low , 1 -> high
        self.switch = 0 # 0 -> low , 1 -> high
        self.upper = ''
        self.lower = ''
pb_dic = {'open' : button("open", '' , '' ) ,'close' : button('close', '' , '' ), '1' : button('1', '2', '') ,'2' : button('2', '3', '1') , '3' : button('3', '4' , '2'), '4' : button('4', '' , '3')}

# //**********************  Global variable   ****************************//
# // record elevator runtime state
state = "standing_by" # standing_by, opening, opened, closing, moving
direction = "no_assign" # no_assign, up, down
target_floor = 0 #  // Which floor does elevator plan to go. 0 means there's no target_floor.
current_floor = 1 #  // Which floor does elevator at right NOW.
# //Counters - to wait a period of time
open_lock_counter = 0
next_floor_counter = 0
exting_count = 0
door_counter = 0 # 0 ~ DOOR_COUNTER_MAX
# //Parameters
DOOR_COUNTER_MAX = 1000
NEXT_FLOOR_TIME = 200
OPENING_VEL = 4
CLOSING_VEL = 4
OPEN_LOCK_TIME = 400
LOWEST_FLOOR = 1 # // -1 -> B1, -2 -> B2
HIGHEST_FLOOR = 4

# Previous state
#pre_state = None 
#pre_current_floor = None
#pre_target_floor = None
#pre_direction = None
#pre_pb_dic = None 

# Rostopic Call back buffer
cmd_list = []

def seven_section_led_set(sec_num_list, seven_section_led):
    for sec_num in sec_num_list: 
        if sec_num == 1: 
            seven_section_led[0,:] = 1
        elif sec_num == 2:
            seven_section_led[0:3,0] = 1
        elif sec_num == 3:
            seven_section_led[0:3,4] = 1
        elif sec_num == 4:
            seven_section_led[2,:] = 1
        elif sec_num == 5: 
            seven_section_led[2:5,0] = 1
        elif sec_num == 6:
            seven_section_led[2:5,4] = 1
        elif sec_num == 7: 
            seven_section_led[4,:] = 1
        else: 
            pass
    return seven_section_led


def LED_cancel_wrong_floor():  # //TODO: alter LED board , when elevator arrived. Also use at plan()
    # // Erase current Floor Led, Erase  led  with wrong direction, and Erase current_floor LED
    # ----- Generate a List to check -------# 
    global direction, state, pb_dic, target_floor, current_floor
    checkList = []
    for i in pb_dic:
        try: 
            floor = int(i)
        except:  # 'open', 'close'
            continue
        else: 
            pass 
    if direction == "up": 
                if floor >= LOWEST_FLOOR  and floor <= current_floor:
                    checkList.append(pb_dic[i])
    elif direction == "down": 
                if floor >= current_floor  and floor <= HIGHEST_FLOOR:
                    checkList.append(pb_dic[i])
    elif direction == "no_assign": 
                if floor >= LOWEST_FLOOR  and floor <= HIGHEST_FLOOR:
                    checkList.append(pb_dic[i])
    #-------  Use checkList to cancel wrong floor ---------# 
    for i in checkList:
        i.led = 0

def plan(): 
        global direction, state, pb_dic, target_floor, current_floor
        # //  Prupose : To get direction and target floor
        target_floor = 0 # ;//  # MUST TO BE 0, BEFORE PLANNING
        # ----- Generate a List to check -------# 
        checkList = []
        for i in pb_dic:
            try: 
                floor = int(i)
            except:  # 'open', 'close'
                continue
            else: 
                pass 
            if direction == "up": 
                    if floor >= current_floor+1  and floor <= HIGHEST_FLOOR:
                        checkList.append(pb_dic[i])
            elif direction == "down":
                if floor >= current_floor-1  and floor <= LOWEST_FLOOR:
                    checkList.append(pb_dic[i])
            elif direction == "no_assign": 
                if floor >= LOWEST_FLOOR  and floor <= HIGHEST_FLOOR:
                    checkList.append(pb_dic[i])

        if direction == "up" or direction == "down":
            for i in checkList:
                if i.led: # (led_arr[i])
                    target_floor = int(i.name) 
        elif direction == "no_assign":
                if target_floor == 0:  #  //: # Can't find any target floor in my direction
                    direction = "no_assign"
                # ------    Try to find assign floor at every direction  -------# 
                for i in pb_dic:
                    try: 
                        floor = int(i)
                    except:  # 'open', 'close'
                        continue
                    else: 
                        if pb_dic[i].led : # (led_arr[i])
                            # CHeck current floor 
                            if pb_dic[i].name == str(current_floor):  #  // nasty exception TODO maybe don't add this is find
                                continue
                            else:
                                target_floor = floor 
                    if target_floor != 0: #  // You DID find a floor to go
                        # //update direction
                        if target_floor - current_floor > 0: #  // go up 
                                direction = "up"
                        else: #  // GO down
                            direction = "down" # ;}
                    else: #  {;} // Still can't find any target floor to go , Should be switch to standing by 
                        pass 
# } end of plan()

def resetCounter():
    global opening_counter,  open_lock_counter, closing_counter, next_floor_counter
    opening_counter = 0
    open_lock_counter = 0
    closing_counter = 0
    next_floor_counter = 0


def main(win):
    global direction, state, pb_dic, target_floor, current_floor,exting_count , pb_dic, open_lock_counter,DOOR_COUNTER_MAX, NEXT_FLOOR_TIME
    global reply_pub, cmd_list, OPENING_VEL, CLOSING_VEL, OPEN_LOCK_TIME, LOWEST_FLOOR, HIGHEST_FLOOR, pre_state
    global pre_current_floor, pre_target_floor, pre_direction, is_running_simu, next_floor_counter, door_counter

    #------- init switch -------# 
    for i in pb_dic: 
        pb_dic[i].switch = 0
    
    #------- Check cmd from elevator_server ----------# 
    if cmd_list != []: # New cmd to do 
        cmd = str(cmd_list[0]).split()
        del cmd_list[0]

        # ------- Write Cmd --------#
        if cmd[0] == 'w': 
            if cmd[1] in pb_dic and (cmd[2] == '1' or cmd[2] == '0' ): 
                print str(cmd) 
                pb_dic[cmd[1]].switch = int(cmd[2])
        # ------- Read  Cmd --------#  
        elif cmd[0] == 'r':
            if cmd[1] in pb_dic: 
                ans = pb_dic[cmd[1]].led
                reply_pub.publish(str(ans))
        else: # Error cmd 
            pass 

    #------  Key board detection -----# 
    key=""
    try:                 
        win.nodelay(True)
        key = win.getkey()
        if key == 'o':
            pb_dic['open'].switch = 1
        elif key == 'c':
            pb_dic['close'].switch = 1
        elif key == 'q':
            is_running_simu = False # Exit 
        else:
            pass
        #--- Check floor -----# 
        for i in pb_dic:
            try: 
                if key == i:
                    pb_dic[i].switch = 1
            except: 
                pass   
        # win.clear()                
        # win.addstr("Detected key:")
        # win.addstr(str(key))
        if key == os.linesep:
            return            
    except Exception as e:
        # No input   
        pass 
    
    for i in pb_dic:  # // default to be record
        if pb_dic[i].name == str(current_floor):
            continue
        if pb_dic[i].switch == 1:
            pb_dic[i].led = 1

    is_floor_LED = False
    for i in pb_dic: 
        if pb_dic[i].name != 'open' and pb_dic[i].name != 'close' and pb_dic[i].led == 1:
            is_floor_LED = True
    
    ########################
    ###   State Machine  ###
    ########################
    if state == "standing_by":
        if pb_dic['open'].switch == 1 : # // switch to "opening" state
            resetCounter()
            state = "opening"
        elif pb_dic['close'].switch == 1 : # if (switch_close)
            pass #  // do nothing
        if is_floor_LED: 
            plan()
            LED_cancel_wrong_floor()
            if target_floor != 0:
                state = "moving"
            else: # {;}// # No avalible floor to go
                pass 
    elif state == "opening":
        if pb_dic['open'].switch == 1 :
            pass 
            # {;} // do nothing
        elif pb_dic['close'].switch == 1 :
            resetCounter()
            state = "closing" # // do nothing
        if is_floor_LED:
            pass # // Record LED, but do nothing
        # Opening Counting
        if door_counter < DOOR_COUNTER_MAX:#   // Keep opening door. 
            door_counter += OPENING_VEL
        elif door_counter >= DOOR_COUNTER_MAX :# //if door is finished open,  switch to "opened" state
            door_counter = DOOR_COUNTER_MAX
            resetCounter()
            state = "opened"

    elif state == "opened":
        if pb_dic['open'].switch == 1 : # { // Reset opening counter
            open_lock_counter = 0
        elif pb_dic['close'].switch == 1 : #  // Switch to closing
            pb_dic['open'].led = 0
            resetCounter()
            state = "closing"
        if is_floor_LED:
            pass # {;} // Record LED, but do nothing
        if open_lock_counter < OPEN_LOCK_TIME: #  // Keep wait. 
            open_lock_counter += 1
        else:# // switch to closing
            pb_dic['open'].led = 0
            resetCounter()
            state = "closing"
    
    elif state == "closing":
        if pb_dic['open'].switch == 1 : # // Reset opening counter
            resetCounter()
            state = "opening"
        elif pb_dic['close'].switch == 1 : #  //Do nothing
            pass
        if is_floor_LED : 
            pass # Record LED, but do nothing
        if door_counter > 0: #  // Keep closing door 
            door_counter -= CLOSING_VEL
        elif door_counter <= 0: # Switch to "moving state" or "standing_by "
            door_counter = 0 
            resetCounter()
            if is_floor_LED: #  //# switch to moving
                plan() # ; // get target_floor and direction
                if target_floor == 0 :# )// nasty exception TODO
                    direction = "no_assign"
                    plan()
                LED_cancel_wrong_floor()
                if target_floor != 0 : # 
                    state = "moving"
                else : # // # No avalible floor to go
                    direction = "no_assign"
                    state = "standing_by"
            else: #  // switch to standing_by
                pb_dic['close'].led = 0
                direction = "no_assign"
                state = "standing_by"
    elif state == "moving":
            if pb_dic['open'].switch == 1 : #  // # do nothing
                pass # {;}
            elif pb_dic['close'].switch == 1 : #  // do nothing
                pass # {;}
            if is_floor_LED: #  // # TODO : Record LED, Middle way interupt!!
                pass # {;}
            if next_floor_counter < NEXT_FLOOR_TIME: #  // #Keep going 
                next_floor_counter += 1
            else : # //# reached a new floor
                resetCounter()
                # // change current_floor
                if direction == "up": # ){
                    current_floor += 1
                elif direction == "down" : 
                    current_floor -= 1
                # // Check if target_floor arrived.
                if current_floor == target_floor: #  //: # elevator Arrived !!! settlement_LED, and switch to "opening" state
                    LED_cancel_wrong_floor() # // # Erase dirrent direction and 
                    pb_dic[str(target_floor)].led = 0
                    target_floor = 0 # ; // DON"T RESET DIRECTION
                    state = "opening"
                else: # need to go to next floor.
                    pass # {;}
    
    #################################
    ###  Simulation to shandi EV  ###
    #################################
    # //Add this block to sim shandi Ev, open and close 
    if state == "opening" :
        pb_dic['open'].led = 1
        pb_dic['close'].led = 0
    elif state == "closing":
        pb_dic['open'].led = 0
        pb_dic['close'].led = 1
    else:
        pb_dic['open'].led = 0
        pb_dic['close'].led = 0
    
    # // Add this block to sim shangdi ev, current floor cancel led
    if pb_dic[str(current_floor)].switch == 1: # switch_arr[current_floor] == 1:
        pb_dic[str(current_floor)].led = 1
        exting_count = 1
    if exting_count > 0 and exting_count < 150:
        pb_dic[str(current_floor)].led = 1
        exting_count += 1
    elif exting_count >= 150: # // 1.5 sec 
        pb_dic[str(current_floor)].led = 0
        exting_count = 0

    #############################################
    ###  Draw out ev information at terminal  ###
    #############################################
    win.clear()

    #--------- Print out basic info. of EV ------------# 
    win.addstr(0,0,"state : "+ state)
    win.addstr(1,0,"direction : "+ direction)
    win.addstr(2,0, "target_floor : "+ str(target_floor))
    win.addstr(3,0 ,"current_floor")

    #---------  dazzling LED  display -----------#  
    seven_section_led = numpy.array([[0,0,0,0,0], [0,0,0,0,0] ,[0,0,0,0,0] ,[0,0,0,0,0] ,[0,0,0,0,0]])
    if current_floor == 1 :
        seven_section_led_set([3,6],seven_section_led )
    elif current_floor == 2:
        seven_section_led_set([1,3,4,5,7],seven_section_led )
    elif current_floor == 3:
        seven_section_led_set([1,3,4,6,7],seven_section_led )
    elif current_floor == 4:
        seven_section_led_set([2,4,3,6],seven_section_led )
    seven_section_led_msg = "" 
    for i in seven_section_led:
        for j in i:
            if j == 0:
                seven_section_led_msg += " "
            else: 
                seven_section_led_msg += "*"
        seven_section_led_msg += '\n'
    win.addstr(4,0, seven_section_led_msg)
    
    #---------   Draw door -----------# 
    DOOR_WIDTH = 50  # Must be odd.
    DOOR_LENTH = 10
    msg_door = ""
    #---- Cal door position ----# 
    door_pos = int(round((1 - door_counter / float(DOOR_COUNTER_MAX)) * ( DOOR_WIDTH / 2 - 1))) + 1

    # -------   Left -----------#
    l_msg = ""
    for j in range(DOOR_WIDTH /2 + 1): # Left 
        if j == 0 : # Leftest
            l_msg += "|"
        elif j == door_pos: 
            l_msg += "$"
        else:  
            l_msg += " "
    # -------   Right -----------#  # right is sysmatrix to left 
    r_msg = l_msg[::-1] # Reverse string 
    #--------   End of line -----# 
    msg_door += l_msg + r_msg

    for i in range(DOOR_LENTH): # How many line 
        win.addstr(10+i, 7, msg_door)
    

    ######################
    ###   LED Status   ###
    ######################
    pb_sort = [(k,pb_dic[k]) for k in sorted(pb_dic.keys())]
    count  = 0 
    for i in pb_sort:
        if i[1].led: 
            win.addstr (13+count,68,i[0] + " *")
        else:  
            win.addstr (13+count,68,i[0])
        count += 1
    ###########################
    ###  Update pre state   ###
    ###########################
    #pre_state = state
    #pre_current_floor = current_floor
    #pre_target_floor = target_floor
    #pre_direction = direction
    #pre_pb_dic = pb_dic

def ev_sim_cmd_CB(msg):
    '''
    Call back function of topic '/ev_sim/cmd'
    '''
    cmd_list.append(msg.data)

    
if __name__ == '__main__':
    rospy.init_node('elevator_simulator')
    rospy.Subscriber('ev_sim/cmd', String, ev_sim_cmd_CB)
    reply_pub = rospy.Publisher('ev_sim/reply', String, queue_size=10)
    # curses.wrapper(main)
    r = rospy.Rate(100.0)
    stdscr = curses.initscr()
    win = curses.newwin(100, 100, 0, 0)
    while not rospy.is_shutdown():
        main(win)
        r.sleep()

