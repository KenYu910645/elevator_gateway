#!/usr/bin/python3
# For TK GUI
import tkinter as tk
import tkinter.messagebox
from PIL import Image
from PIL import ImageTk
import queue
import os
import time
import threading # get rid of counters, use timer
# For IPC # message queue
import posix_ipc
#-------  Elevator Parameters   ---------# 
LOOP_PERIOD       = 0.01 # sec
DOOR_OPENING_TIME = 2 # sec
DOOR_CLOSING_TIME = 2 # sec
OPEN_LOCK_TIME    = 3 # sec
NEXT_FLOOR_TIME   = 2 # sec
EV_LOCATION_MAX = 1000 # 0~1000
DOOR_SENSOR_MAX = 1000 # 0~1000
LED_SUSTAIN_TIME = 1   # sec
PRESS_BT_TIME    = 0.5 # sec 

#------- Tkinter  parameter   -------# 
EV_PANEL_BTS_SIZE  = 3
EV_PANEL_TOTAL_ROW = 4 # add 1 row for led 
EV_PANEL_TOTAL_COL = 2
# space between buttons
EV_PANEL_PADX  = 0
EV_PANEL_PADY  = 0
# space between text and button's broards, will change size of buttons
EV_PANEL_IPADX = 1
EV_PANEL_IPADY = 1
#
EV_STATE_CANVAS_PERIOD = 100 # for animation
#
BUTTON_HIGHLIGHT_COLOR = "yellow"
BUTTON_COLOR = "light gray"

class ev_panel_bts(object):
    def __init__(self,frame, name, row ,column, command, pic_path):
        # Create a button object on tk
        self.bt = tk.Button(frame, text=name ,command = command , height = EV_PANEL_BTS_SIZE, width = EV_PANEL_BTS_SIZE)
        # where to put this button respect to panel
        self.bt.grid(row = row , column = column, padx = EV_PANEL_PADX , pady = EV_PANEL_PADY,\
                                                 ipadx = EV_PANEL_IPADX, ipady = EV_PANEL_IPADY)
        # Name of this button
        self.name   = name # '1F' , '2F' , 'open', 'close'
        # simulate ev button led, 0 -> led stay low , 1 -> led is on 
        self.led    = 0
        # simulate ev panel button, 0 -> button not pressed , 1 -> button pressed
        self.switch = 0
        # simulate elevator press button 
        self.switch_server = 0 
        # picture path of this floor 
        self.pic_path = pic_path
class app():
    def __init__(self):
        #-----------    Elevator State    ------------# 
        # Elevator state : standing_by, opening, opened, closing, moving
        self.state = "standing_by"
        # Elevator moving direction : no_assign, up, down
        self.direction = "no_assign"
        # Elevator currently at which floor 
        self.current_floor = "1"
        # Elevator target floor. Which floor does elevator plan to go? "" means no target_floor.
        self.target_floor  = "" 
        
        #IPC cmd from elevator server 
        self.queue = queue.Queue()
        # For opened door timer
        self.timer = None
        
        # ----------   Counters/Sensor ------------  #
        # Show how much does elevator's door opened
        # 0 ~ DOOR_COUNTER_MAX ,  0 means door fully close , DOOR_COUNTER_MAX means door fully open 
        self.door_sensor = 0.0
        # Show where is elevator among these floors
        # 0 ~ EV_LOCATION_MAX   , 0 means ev at lowest floor , EV_LOCATION_MAX means eleevator at highest floor
        self.ev_location_sensor = 0.0

        # counter for canvas_state 
        self.animate_counter = 0 

        # ----------   Tk window and frame------------  #
        self.window = tk.Tk()
        self.window.title("Elevator Simulator")# title of window
        self.window.iconphoto(False, tk.PhotoImage(file='pic/icon.png'))# icon of window
        # self.window.geometry('500x800') # dont specify, tk will automatic assign a proper size.
        # window.resizable(0,0) # disable resize window 

        # Group frame
        self.ev_bts = tk.Frame(self.window)
        self.ev_bts.pack(side = tk.LEFT)

        # ----------   elevator_panel_buttonr ------------  # 
        '''
        define elevator button 
        '''
        self.bt_dic = {"1"    : ev_panel_bts(self.ev_bts, "1F",     EV_PANEL_TOTAL_ROW-2 ,0, self.cb_bt_1f,    "pic/1_digit.pgm"),\
                       "2"    : ev_panel_bts(self.ev_bts, "2F",     EV_PANEL_TOTAL_ROW-3 ,0, self.cb_bt_2f,    "pic/2_digit.pgm"),\
                       "3"    : ev_panel_bts(self.ev_bts, "3F",     EV_PANEL_TOTAL_ROW-2 ,1, self.cb_bt_3f,    "pic/3_digit.pgm"),\
                       "4"    : ev_panel_bts(self.ev_bts, "4F",     EV_PANEL_TOTAL_ROW-3 ,1, self.cb_bt_4f,    "pic/4_digit.pgm"),\
                       "close" : ev_panel_bts(self.ev_bts, "close", EV_PANEL_TOTAL_ROW-1 ,0, self.cb_bt_close, None),\
                       "open"  : ev_panel_bts(self.ev_bts, "open",  EV_PANEL_TOTAL_ROW-1 ,1, self.cb_bt_open , None)}
        #define relationship among these floors, lowest floor is bt_list[0], hightest floor is bt_list[-1]
        self.bt_list = ["1" , "2" , "3" , "4"] 

        ##############################
        ###   elevator_led canvas  ###
        ##############################
        #------ Floor LED indicator --------# 
        self.canvas_floor = tk.Canvas(self.ev_bts,bg = "white", height = 50 , width = 50)
        self.canvas_floor.grid(row = 0 , column = 0, padx = EV_PANEL_PADX , pady = EV_PANEL_PADY\
                                                , ipadx = EV_PANEL_IPADX, ipady = EV_PANEL_IPADY)
        #------ EV state LED indicator --------# opening, closing , moving up , moving down 
        self.canvas_state = tk.Canvas(self.ev_bts,bg = "white", height = 50 , width = 50)
        self.canvas_state.grid(row = 0 , column = 1, padx = EV_PANEL_PADX , pady = EV_PANEL_PADY\
                                                , ipadx = EV_PANEL_IPADX, ipady = EV_PANEL_IPADY)
        
        ##############################
        ###   Draw TK object       ###
        ##############################
        ###----------   Text box  ----------###
        self.text = tk.Text(self.window,height = 10, width = 20)
        self.text.pack(side = tk.TOP)

        ###----------   cartoon canvas  ----------###
        # User adjustable parameter
        # frame size 
        total_height = 600
        total_width  = 300
        # elevator size 
        ev_width     = 80
        ev_height    = 100
        # amr robot size 
        amr_height   = 30
        amr_width    = 60
        #
        gap          = 5  # gap width between elevator and elevator well
        canvas_edge  = 3  # gap width between elevator well and canvas edge
        floor_thick  = 5  # thickness of floor
        
        # location of amr, change in runtime (animation)
        self.amr_location_x = 0
        self.amr_location_y = 0
        
        ev_well_width  = 2*gap + ev_width
        ev_well_height = total_height - canvas_edge
        ev_well_x = total_width - ev_well_width - canvas_edge
        
        max_ev_movement = ev_well_height - ev_height - 2*gap
        floor_height = max_ev_movement / (len(self.bt_list)-1)

        #------ cartoon canvas --------#
        self.canvas_cartoon = tk.Canvas(self.window,bg = "white", height = total_height , width = total_width)
        # self.canvas_state.grid(row = 0 , column = 1, padx = EV_PANEL_PADX , pady = EV_PANEL_PADY, ipadx = EV_PANEL_IPADX, ipady = EV_PANEL_IPADY)
        self.canvas_cartoon.pack(side = tk.LEFT)
        
        #----------   Draw elevator well ----------#
        ev_well_an1 = (ev_well_x               , canvas_edge)
        ev_well_an2 = (ev_well_x+ev_well_width , ev_well_height)
        self.ev_well = self.canvas_cartoon.create_rectangle(ev_well_an1[0],ev_well_an1[1],ev_well_an2[0],ev_well_an2[1], fill = "pink")
        #----------   Draw elevator ----------#
        ev_an2      = (ev_well_an2[0] - gap , ev_well_an2[1] - gap)
        ev_an1      = (ev_an2[0] - ev_width , ev_an2[1] - ev_height)
        self.ev      = self.canvas_cartoon.create_rectangle(ev_an1[0]     ,ev_an1[1]     ,ev_an2[0]     ,ev_an2[1]     , fill = "orange")
        #----------   Draw floors ----------#
        floors_an_list = []
        for i in range(len(self.bt_list)):
            floor_an1   =  (0              , ev_an2[1]      - i*floor_height)
            floor_an2   =  (ev_well_an1[0] , ev_well_an2[1] + floor_thick - i*floor_height)
            floors_an_list.append([floor_an1,floor_an2])
            self.canvas_cartoon.create_rectangle(floor_an1[0]     ,floor_an1[1]     ,floor_an2[0]     ,floor_an2[1]     , fill = "black")
        
        #----------   Draw elevator door ----------#
        # These doors should tranvel along with elevator 
        self.left_door  = self.canvas_cartoon.create_rectangle(ev_an1[0],ev_an1[1], ev_an1[0] + ev_width/2  ,ev_an2[1], fill = "brown")
        self.right_door = self.canvas_cartoon.create_rectangle(ev_an2[0],ev_an1[1], ev_an1[0] + ev_width/2  ,ev_an2[1], fill = "brown")
        
        #----------   Draw amr  ----------#
        self.amr_location_x = total_width/2 -100
        self.amr_location_y = floors_an_list[0][0][1] - amr_height
        self.canvas_cartoon.create_rectangle(self.amr_location_x,self.amr_location_y,self.amr_location_x+amr_width,self.amr_location_y + amr_height, fill = "yellow")
        
        # helper variable for cute cartoon 
        self.CARTOON_EV_MOVING_VEL    =   max_ev_movement/((NEXT_FLOOR_TIME/LOOP_PERIOD)*(len(self.bt_list) - 1))
        self.CARTOON_DOOR_OPENING_VEL =  (ev_width/2)/(DOOR_OPENING_TIME/LOOP_PERIOD)
        self.CARTOON_DOOR_CLOSING_VEL =  (ev_width/2)/(DOOR_CLOSING_TIME/LOOP_PERIOD)
        # helper variable for counters
        self.MOVING_VEL  = EV_LOCATION_MAX/((NEXT_FLOOR_TIME/LOOP_PERIOD)*(len(self.bt_list) - 1))
        self.OPENING_VEL = DOOR_SENSOR_MAX/(DOOR_OPENING_TIME/LOOP_PERIOD)
        self.CLOSING_VEL = DOOR_SENSOR_MAX/(DOOR_CLOSING_TIME/LOOP_PERIOD)
        
        #------ Dark Magic ------#
        os.system("gnome-terminal -e 'python3 elevator_server.py'")
        os.system("gnome-terminal -e 'python3 fake_amr_navi_center.py'")
        #------ message queue for IPC -------# 
        self.mq_send = posix_ipc.MessageQueue('/simu_IPC_reply', posix_ipc.O_CREAT)
        self.mq_send.block = False # non-blocking recv , send
        self.mq_recv = posix_ipc.MessageQueue('/simu_IPC_cmd'  , posix_ipc.O_CREAT)
        self.mq_recv.block = False # non-blocking recv , send
        ###-----------   start main loop   -------------###
        self.main() # Recursive call main()
        self.window.mainloop()

    def LED_cancel_wrong_floor(self):
        '''
        Toggle Led status to cancel illegal bts led
        DON"T erase current_floor Led, erase led on oppisite direction
        called when elevator arrived target floor and plan()
        '''
        current_idx = self.bt_list.index(self.current_floor)
        if self.direction == "up":
            for bt_key in self.bt_list[:current_idx]: # Don't include current floor
                self.bt_dic[bt_key].led = 0

        elif self.direction == "down": 
            for bt_key in self.bt_list[current_idx+1:]:# Don't include current floor
                self.bt_dic[bt_key].led = 0
        
        elif self.direction == "no_assign": # Don't include current floor
            for bt_key in self.bt_list:
                if bt_key != self.current_floor:
                    self.bt_dic[bt_key].led = 0
    
    def plan(self):
        '''
        To get direction and target floor
        '''
        self.target_floor = "" # MUST BE "" BEFORE PLANNING
        # ----- Generate a List to pick out target floor -------# 
        candidate_floor = []
        current_idx = self.bt_list.index(self.current_floor) 
        if self.direction == "up": 
            for bt in self.bt_list[current_idx+1:]: # Don't include current 
                candidate_floor.append(bt)
        elif self.direction == "down":
            for bt in self.bt_list[:current_idx]: # Don't include current 
                candidate_floor.append(bt)
        elif self.direction == "no_assign": 
            for bt in self.bt_list: # Don't include current 
                candidate_floor.append(bt)
        
        # ------ Get a target floor from candidate_floor list -------# 
        # Find a target floor at current direction
        if self.direction != 'no_assign':
            for bt in candidate_floor:
                if self.bt_dic[bt].led:
                    self.target_floor = bt
        else:  #  self.direction == "no_assign":
            if self.target_floor == "": # Can't find any target floor in my direction
                self.direction = "no_assign"
            # ------    Try to find target floor in all floors  -------# 
            for bt in self.bt_list:
                if self.bt_dic[bt].led and self.current_floor != bt: # if led is on and it's not current floor
                    ###------  Found a floor to go !! -------###
                    # update target floor
                    self.target_floor = bt
                    # update direction
                    if self.bt_list.index(self.target_floor) - self.bt_list.index(self.current_floor) > 0: # go up
                        self.direction = "up"
                    else: # go down
                        self.direction = "down"
    
    def opened_timer_cb(self):
        '''
        Reach OPEN_DOOR_LOCK time, should close the door now.
        '''
        self.timer = None # Reset timer
        self.state = "closing"
    
    def led_sustain_timer_cb(self, bt):
        '''
        Current floor led will sustain a bit while after being pressed
        '''
        bt.led = 0
    
    def main(self): # main loop 
        #------- Check cmd from elevator_server ----------# 
        # if not self.queue.empty(): # New cmd to do 
        try: 
            cmd = self.mq_recv.receive()[0].decode().split() # non-blocking receiver
        #cmd = self.queue.get().decode().split()# pop out one cmd to do 
        except posix_ipc.BusyError:
            pass # queue empty
        else:
            print ("cmd:" + str(cmd))
            # ------- Write Cmd --------#(toggle switch)
            if cmd[0] == 'w':
                if cmd[1] in self.bt_dic and (cmd[2] == '1' or cmd[2] == '0'):
                    self.bt_dic[cmd[1]].switch_server = int(cmd[2])
            # ------- Read  Cmd --------#  
            elif cmd[0] == 'r':
                if cmd[1] in self.bt_dic:
                    ans = self.bt_dic[cmd[1]].led
                    # Output ans through IPC 
                    print ("reply:" + str(ans))
                    # self.mqtt_ipc.publish(topic = "/simu_IPC/reply" , payload = str(ans), qos = 0, retain = True)
                    try:
                        self.mq_send.send(str(ans), priority=9)
                    except posix_ipc.BusyError: # queue full
                        pass 
            else: # Error cmd 
                pass 
        
        # Privilage switch server 
        for bt_key in self.bt_dic:
            if self.bt_dic[bt_key].switch_server: # privilage switch is on! 
                self.bt_dic[bt_key].switch = 1 


        #-----  Turn on led if switch is on -------# 
        for bt in self.bt_dic: 
            #if bt == self.current_floor:
            #    continue
            if  self.bt_dic[bt].switch == 1:
                self.bt_dic[bt].led = 1

        #-----   Check if any floor button is on -------# 
        is_floor_LED = False
        for bt in self.bt_dic:
            if bt != 'open' and bt != 'close' and self.bt_dic[bt].led == 1:
                is_floor_LED = True
        
        ########################
        ###   State Machine  ###
        ########################
        if self.state == "standing_by":
            if self.bt_dic['open'].switch == 1 : # switch to "opening" state
                self.state = "opening"
            if is_floor_LED:
                self.plan()
                self.LED_cancel_wrong_floor()
                if self.target_floor != "":
                    self.state = "moving"
                else: # No avalible floor to go
                    pass 
        elif self.state == "opening":
            if self.bt_dic['close'].switch == 1 :
                self.state = "closing"
            
            # Opening Counting
            if self.door_sensor < DOOR_SENSOR_MAX:#  Keep opening door. 
                self.door_sensor += self.OPENING_VEL
                self.cartoon_move_door(-self.CARTOON_DOOR_OPENING_VEL)

            elif self.door_sensor >= DOOR_SENSOR_MAX :#if door is fully open,  switch to "opened" state
                self.door_sensor = DOOR_SENSOR_MAX
                self.timer = threading.Timer(OPEN_LOCK_TIME,self.opened_timer_cb)
                self.timer.start()
                self.state = "opened"
        elif self.state == "opened":
            if self.bt_dic['open'].switch == 1 : # Reset opening timer
                self.timer.cancel()
                self.timer = threading.Timer(OPEN_LOCK_TIME,self.opened_timer_cb)
                self.timer.start()
            elif self.bt_dic['close'].switch == 1 : # Switch to closing
                self.timer.cancel()
                self.bt_dic['open'].led = 0
                self.state = "closing"
        elif self.state == "closing":
            if self.bt_dic['open'].switch == 1 : #Reset opening counter
                self.state = "opening"
            
            if self.door_sensor > 0: # Keep closing door 
                self.door_sensor -= self.CLOSING_VEL
                self.cartoon_move_door(self.CARTOON_DOOR_OPENING_VEL)
            elif self.door_sensor <= 0: # Switch to "moving state" or "standing_by "
                self.door_sensor = 0 
                # TODO I think its OK to switch to "standing_by first"

                if is_floor_LED: # switch to moving
                    self.plan() # get target_floor and direction
                    if self.target_floor == "" :# nasty exception TODO
                        self.direction = "no_assign"
                        self.plan()
                    self.LED_cancel_wrong_floor()
                    if self.target_floor != "" : # 
                        self.state = "moving"
                    else : # No avalible floor to go
                        self.direction = "no_assign"
                        self.state = "standing_by"
                
                else: # switch to standing_by
                    self.bt_dic['close'].led = 0
                    self.direction = "no_assign"
                    self.state = "standing_by"
        elif self.state == "moving":
            # keep moving
            if self.direction == "up":# elevator asending
                self.ev_location_sensor += self.MOVING_VEL
                self.cartoon_move_ev(-self.CARTOON_EV_MOVING_VEL)
            elif self.direction == "down":# elevator desending
                self.ev_location_sensor -= self.MOVING_VEL
                self.cartoon_move_ev(self.CARTOON_EV_MOVING_VEL)

            d   = EV_LOCATION_MAX/(len(self.bt_list)-1)# divisor
            q   = int(self.ev_location_sensor  //d)# quotient
            r   =     self.ev_location_sensor  % d # reminder

            if r >= 0 and r <= self.MOVING_VEL*1.1:# ev is passing a floor rightnow
                self.current_floor = self.bt_list[q]
            
            # Check if target_floor arrived.
            if self.current_floor == self.target_floor: #  elevator Arrived !!! settlement_LED, and switch to "opening" state
                self.LED_cancel_wrong_floor() #  Erase dirrent direction and 
                self.bt_dic[self.target_floor].led = 0
                self.target_floor = "" # DON"T RESET DIRECTION
                self.state = "opening"
        
        # Add this block to sim shandi Ev
        # open and close directly indicate ev state 
        if self.state == "opening" :
            self.bt_dic['open'].led = 1
            self.bt_dic['close'].led = 0
        elif self.state == "closing":
            self.bt_dic['open'].led = 0
            self.bt_dic['close'].led = 1
        else:
            self.bt_dic['open'].led = 0
            self.bt_dic['close'].led = 0
        
        # speical treat to current floor button, elevator server use this led pattern to 
        # determine weather ev arrive target floor 
        bt = self.bt_dic[self.current_floor]
        if bt.switch == 1 and self.state != "moving": # Don't cancel any led at moving state
            bt.led = 1 # sustain led light for LED_SUSTAIN_TIME sec 
            t = threading.Timer(LED_SUSTAIN_TIME, self.led_sustain_timer_cb, args=[bt])
            t.start()

        #------- Reset switch -------# I trust these switch has been used.
        for bt in self.bt_dic:
            self.bt_dic[bt].switch = 0 

        #############################
        ###   Show Floor canvas   ###
        #############################
        '''
        current_floor  show on floor canvas
        '''
        self.window.after(0,self.change_pic_canvas_floor(self.bt_dic[self.current_floor].pic_path))
        
        #############################
        ###   Show state canvas   ###
        #############################
        if self.state == "opened":
            self.window.after(0,self.change_pic_canvas_state("pic/open_4.jpeg"))
        elif self.state == "standing_by":
            self.window.after(0,self.change_pic_canvas_state("pic/blank.jpeg"))
        elif self.state == "opening": # opening animation
            self.canvas_animate(EV_STATE_CANVAS_PERIOD , ["pic/open_1.jpeg",\
                                                          "pic/open_2.jpeg",\
                                                          "pic/open_3.jpeg",\
                                                          "pic/open_4.jpeg"])
        elif self.state == "closing":# closing animation
            self.canvas_animate(EV_STATE_CANVAS_PERIOD , ["pic/close_1.jpeg",\
                                                          "pic/close_2.jpeg",\
                                                          "pic/close_3.jpeg",\
                                                          "pic/close_4.jpeg"])
        elif self.state == "moving":
            if self.direction == "up":
                self.canvas_animate(EV_STATE_CANVAS_PERIOD , ["pic/up_1.jpeg",\
                                                              "pic/up_2.jpeg",\
                                                              "pic/up_3.jpeg"])
            elif self.direction == "down":
                self.canvas_animate(EV_STATE_CANVAS_PERIOD , ["pic/down_1.jpeg",\
                                                              "pic/down_2.jpeg",\
                                                              "pic/down_3.jpeg"])
        else:
            pass
        
        ###########################
        ###   Show LED Status   ###
        ###########################
        '''
        If led = 1  ->  button highlight
        If led = 0  ->  button don't highlight
        '''
        for bt_key in self.bt_dic:
            bt = self.bt_dic[bt_key]
            if bt.led == 1: # led of button is on 
                bt.bt.configure(bg = BUTTON_HIGHLIGHT_COLOR)
                bt.bt.configure(activebackground = bt.bt.cget('background'))
            else: # led of button is off 
                bt.bt.configure(bg = BUTTON_COLOR)
                bt.bt.configure(activebackground = bt.bt.cget('background'))
        
        ###########################
        ###   Text show state   ###
        ###########################
        self.text.delete(1.0,tk.END)
        self.text.insert("insert","state :" + self.state + '\n')
        self.text.insert("insert","direction :" + self.direction + '\n')
        self.text.insert("insert","current floor :" + self.current_floor+ '\n')
        self.text.insert("insert","target  floor :" + self.target_floor + '\n')
        
        #----- Recursive call main() --------# 
        self.window.after(int(LOOP_PERIOD*1000),self.main)


    def canvas_animate(self,period,pic_list):
        '''
        create a animate on canvas
        Input : 
            period : value , how long will it take to go thought whole animation
            pic_list : str , picture path that will play in sequence.
        Dependence : 
            self.animate_counter 
        '''
        num_pic = len(pic_list)
        self.animate_counter += 1
        try: 
            pic_path = pic_list[self.animate_counter//(period//num_pic)]
        except: # counter exceed period, Reset !!
            self.animate_counter = 0
        else:
            self.window.after(0,self.change_pic_canvas_state(pic_path))

    def change_pic_canvas_floor(self,new_pic_path):
        '''
        Change picture inside canvas_floor to new picture
        Input : 
            new_pic_path : str , new picture path 
        '''
        self.img_floor =  ImageTk.PhotoImage(Image.open(new_pic_path).resize((35,50), Image.ANTIALIAS))
        self.canvas_floor.create_image (27,30,anchor = 'center', image = self.img_floor) # where to put pic on canvas

    def change_pic_canvas_state(self,new_pic_path):
        '''
        Change picture inside canvas_state to new picture
        Input : 
            new_pic_path : str , new picture path 
        '''
        self.img_arrow =  ImageTk.PhotoImage(Image.open(new_pic_path).resize((50,50), Image.ANTIALIAS))
        self.canvas_state.create_image (27,30,anchor = 'center', image = self.img_arrow) # where to put pic on canvas
    
    def cartoon_move_ev(self,increment):
        '''
        Moving elevator by one increment 
        Input :
            increment : positive ->  moving down
                        negative ->  moving up
        '''
        self.canvas_cartoon.move(self.ev        , 0, increment)
        self.canvas_cartoon.move(self.left_door , 0, increment)
        self.canvas_cartoon.move(self.right_door, 0, increment)
    
    def cartoon_move_door(self,increment):
        '''
        Opening door or Closing door by one increment 
        Input :
            increment : positive ->  close door 
                        negative ->  open  door
        '''
        # Increment left door 
        an1_x, an1_y, an2_x, an2_y = self.canvas_cartoon.coords(self.left_door)
        an2_x += increment
        self.canvas_cartoon.coords(self.left_door, an1_x, an1_y, an2_x, an2_y)
        # Increment right door 
        an1_x, an1_y, an2_x, an2_y = self.canvas_cartoon.coords(self.right_door)
        an1_x -= increment
        self.canvas_cartoon.coords(self.right_door, an1_x, an1_y, an2_x, an2_y)

    
    ######################################
    ###   buttons callback fucntion    ###
    ######################################
    def cb_bt_1f(self):
        self.bt_dic['1'].switch = 1
    def cb_bt_2f(self):
        self.bt_dic['2'].switch = 1
    def cb_bt_3f(self):
        self.bt_dic['3'].switch = 1
    def cb_bt_4f(self):
        self.bt_dic['4'].switch = 1
    def cb_bt_open(self):
        self.bt_dic['open'].switch = 1
    def cb_bt_close(self):
        self.bt_dic['close'].switch = 1
app()