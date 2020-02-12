import time
import yaml
import threading
import os
from global_var.global_logger import logger

from notify_agent import notify_agent
from global_var.global_param import is_using_rss, table,CLIENT_NAME,ENABLE_VERIFY_DOOR_STATUS , CLOSE_EYE_WAIT_DOOR_SEC, DOOR_OPEN_LIMIT_TIME, WAIT_REACH_LIMIT_TIME, SLIENCE_MIN_COUNTER, FLOOR_LED_CONFIRMATION_MAX_TIME, FLOOR_LED_CONFIRMATION_MIN_TIME, WAIT_DOOR_LIMIT, IS_SIMULATION

if is_using_rss: 
    from weixin_alarm import alarm

if IS_SIMULATION:
    from pb_interface import PB_interface_simu
else:
    from pb_interface import PB_interface

class ElevatorCmd(object):
    def __init__(self):
        # Use timer to countdown.
        self.open_moment = None
        if IS_SIMULATION: 
            self.pb = PB_interface_simu()
        else: 
            self.pb = PB_interface()
    
    def door_release_checker(self):
        '''
        Return True : TIMEOUT RELEASE ! 
        Return False : normal
        '''
        if self.open_moment != None:
            if time.time() - self.open_moment > DOOR_OPEN_LIMIT_TIME:
                logger.warning("[door_release_checker] timeout release !")
                if is_using_rss: 
                    alarm.sent("TIMEOUT RELEASE ! Door opened for " + str(DOOR_OPEN_LIMIT_TIME) + "sec")
                return True
            else: # Door is open but doesn't timeout
                return False
        else: # Door is not opened
            return False

    def floor_confirm(self, floor_led_record):
        '''
        Output: 
            True: confirm
            False: not
        '''
        for i in range(len(floor_led_record)): # in floor_led_record:
            # Check list_size
            if i + len(FLOOR_LED_CONFIRMATION_MAX_TIME) > len(floor_led_record):
                return False
            for ii in range(len(FLOOR_LED_CONFIRMATION_MAX_TIME)):
                if floor_led_record[i+ii] <= FLOOR_LED_CONFIRMATION_MAX_TIME[ii] and floor_led_record[i+ii] >= FLOOR_LED_CONFIRMATION_MIN_TIME[ii]:
                    if ii == len(FLOOR_LED_CONFIRMATION_MAX_TIME)-1:
                        return True
                else:
                    break
            # logger.debug("[call:"+call_state+"]" + msg)
        return False

    def call_iterateOnce(self, cmd):
        '''
        This is a non-blocking function
        '''
        if not cmd.is_release:
            #######################################
            #########    Loop routine     #########
            #######################################
            ###### Door monitor, door_state could be 'closed', 'opened', 'closing', 'opening' ,'unknown'
            if ENABLE_VERIFY_DOOR_STATUS: 
                open_key_state = self.pb.EVledRead('open')
                close_key_state = self.pb.EVledRead('close')
                if open_key_state == 0 and close_key_state == 0: # opened or closed # Exit for this function !!
                    if cmd.door_state == 'opening':
                        cmd.door_state = 'opened'
                        logger.info("[Door State] |<--      -->|  Fully Open.")
                    if cmd.door_state == 'closing':
                        cmd.door_state = 'closed'
                        logger.info("[Door State]    -->||<--     Fully Closed.")
                elif open_key_state == 1 and close_key_state == 0:
                    if not cmd.door_state == 'opening':
                        logger.info("[Door State]  <<<--  -->>>    Opening.")
                    cmd.door_state = 'opening'
                elif open_key_state == 0 and close_key_state == 1:
                    if not cmd.door_state == "closing":
                        logger.info("[Door State]  -->>>  <<<--    Closing.")
                    cmd.door_state = 'closing'
                elif open_key_state == 1 and close_key_state == 1:
                    logger.error("[Door State] Both open and close are high, can't decide door state.")
                else: #ST ERROR
                    logger.warning("[Door State] ST Read ERROR, can't confirm door status")
            else: # Not able to verify door status, so we could only close eye and wait for door open, pity...
                pass
                
            #######################################
            #########      AMR Notify     #########
            #######################################
            '''
            TODO : This block should be written as a state
            '''
            if cmd.na.state == "stand_by": # Nothing to notify
                pass
            else: 
                cmd.na.notify_iterateOnce()
                if cmd.na.state == "completed":
                    if cmd.na.payload['cmd'] == "cancel":
                        cmd.total_logger.append(("notify_cancel_success", time.time()))
                        cmd.state = "finish"
                    elif cmd.na.payload['cmd'] == "reached":
                        cmd.total_logger.append(("notify_reached_success", time.time()))
                        if cmd.pre_state == "moving2current":
                            cmd.switch_state("enteringEV") # switch state will auto clear notify_agent 
                        elif cmd.pre_state == "moving2target":
                            cmd.switch_state("alightingEV")# switch state will auto clear notify_agent 
                elif cmd.na.state == "abort":
                    cmd.total_logger.append(("netowork_abort", time.time()))
                    cmd.state = "finish"
                elif cmd.na.state == "trying":
                    pass
                else:
                    pass
                return  # When something to notify, only doing notify
            
            # First Init 
            if cmd.state == "":
                cmd.switch_state("wait_vacancy")
            
            #######################################
            #########    Wait vacancy    ########## 
            #######################################
            if cmd.state == "wait_vacancy":
                if time.time() - cmd.t_into_state > WAIT_REACH_LIMIT_TIME:
                    logger.warning("[call:"+cmd.state +"] wait vacancy for " + str(WAIT_REACH_LIMIT_TIME) +"sec , timeout!")
                    # Notify
                    cmd.na.set_notify({'cmd' : "cancel", 'robot_id' : cmd.robot_id}, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
                if not self.is_human_override([]): # no human is using EV. # OR opend OR waiting for door open
                    if cmd.slience_counter >= SLIENCE_MIN_COUNTER:
                        cmd.switch_state("moving2current")
                        # t_into_state = time.time() # avoid a endless loop # TODO Human override bug
                    else:
                        cmd.slience_counter += 1
                        logger.debug("[call:"+cmd.state +"] Slience, " + str(cmd.slience_counter) + " / " + str(SLIENCE_MIN_COUNTER))
                else: # HUMAN
                    logger.debug("[call:"+cmd.state +"] Human detected, reset slience counter")
                    cmd.slience_counter = 0 # Keep waiting
            #####################################################
            #########    moving2current and  moving2target  #####
            #####################################################
            elif cmd.state == "moving2current" or cmd.state == "moving2target":
                if cmd.state == "moving2current":
                    push_floor = cmd.current_floor
                    if self.is_human_override([cmd.current_floor, 'open', 'close']): # Go back to wait_vacancy 
                        logger.info("[call:"+cmd.state +"]  Human detected, go back to wait vacanccy")
                        # t_into_state = time.time() # avoid endless loop # TODO Human override bug
                        cmd.switch_state("wait_vacancy")
                elif cmd.state == "moving2target":
                    push_floor = cmd.target_floor
                if time.time() - cmd.t_into_state > WAIT_REACH_LIMIT_TIME:
                    logger.warning("[call:"+cmd.state +"] EV not reach exceed "+ str(WAIT_REACH_LIMIT_TIME) + " sec, timeout")
                    if is_using_rss:
                        alarm.sent("EV Moving for " + str(WAIT_REACH_LIMIT_TIME) + "sec, but still can't arrived floor, MISSON ABORT !")
                    cmd.na.set_notify({'cmd' : "cancel", 'robot_id' : cmd.robot_id}, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
                
                GPIO_state = self.pb.EVledRead(push_floor, retryTime=3)
                if GPIO_state == 0: # led off
                    if cmd.t_start_hit_floor == 0: # First push button.
                        self.single_hit(push_floor, 0.2)
                        cmd.t_start_hit_floor = time.time()
                        logger.info("[call:"+cmd.state +"] Pushed " + str(push_floor) + " F button.")
                    else:
                        # logger.info("[call:"+cmd.state +"] Takes " + str(time.time() - cmd.t_start_hit_floor) + " sec to extinguish floor button LED.")
                        cmd.floor_led_record.append( round(time.time() - cmd.t_start_hit_floor, 2)) # 10Hz while loop, it's enough
                        logger.info("[call:"+cmd.state +"] Led_record: " + str(cmd.floor_led_record))
                        if not self.floor_confirm(cmd.floor_led_record): # Repush button
                            time.sleep(0.2)
                            self.single_hit(push_floor, 0.2)
                            cmd.t_start_hit_floor = time.time()
                            logger.info("[call:"+cmd.state +"] "+ str(push_floor) + "F  push.")
                        else: # confirm Arried 
                            logger.info("[call:"+cmd.state +"] Arrived "+ str(push_floor) + " F, takes  "+str(round(time.time() - cmd.t_into_state,2))+" sec. (" + str(WAIT_REACH_LIMIT_TIME) + ")")
                            self.open()
                            cmd.switch_state("waitDoorOpen")
                elif GPIO_state == 1: # led on , Keep waiting
                    logger.debug("[call:"+cmd.state +"]"+ str(push_floor) + "F LED is still on.( "+str(time.time()-cmd.t_into_state)+"/"+ str(WAIT_REACH_LIMIT_TIME)+")")
                else: # "Err"
                    logger.warning("[call:"+cmd.state +"] Get error from ST read.")
            
            #####################################
            #########    waitDoorOpen  ##########
            #####################################
            elif cmd.state == "waitDoorOpen":
                dT = time.time() - cmd.t_into_state
                if dT >= WAIT_DOOR_LIMIT: # Can't wait timeout
                    cmd.switch_state(cmd.pre_state)
                if not ENABLE_VERIFY_DOOR_STATUS: 
                    if dT >= CLOSE_EYE_WAIT_DOOR_SEC: 
                        cmd.door_state = 'opened'

                if not cmd.door_state == 'opened':
                    logger.debug("[call:"+cmd.state +"] wait for door opened.")
                else: # cmd.door_state == 'opened'
                    if not ENABLE_VERIFY_DOOR_STATUS: # if is close-eyes wait for door, need to switch flag back.
                        cmd.door_state = 'closed'
                    if   cmd.pre_state == "moving2current":
                        cmd.na.set_notify({'cmd' : "reached", 'robot_id' : cmd.robot_id, 'floor' : cmd.current_floor}, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
                    elif cmd.pre_state == "moving2target":
                        cmd.na.set_notify({'cmd' : "reached", 'robot_id' : cmd.robot_id, 'floor' : cmd.target_floor }, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
            #####################################
            #########    enteringEV    ########## 
            #####################################
            elif cmd.state == "enteringEV":
                if cmd.is_timeout_release:
                    cmd.na.set_notify({'cmd' : "cancel", 'robot_id' : cmd.robot_id}, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
                if cmd.is_entering_done:
                    logger.info("[call:"+cmd.state +"] get entering_done."+"("+ str(round(time.time()-cmd.t_into_state,2))+"/"+str(DOOR_OPEN_LIMIT_TIME)+" sec)")
                    self.close()
                    cmd.is_entering_done = False
                    cmd.switch_state("moving2target")
                else:
                    logger.debug("[call:"+cmd.state +"] Wait for entering done. takes " + str(time.time()-cmd.t_into_state) + " sec.")
            #####################################
            #########    alightingEV    #########
            #####################################
            elif cmd.state == "alightingEV":
                if cmd.is_timeout_release:
                    cmd.na.set_notify({'cmd' : "cancel", 'robot_id' : cmd.robot_id}, topic = cmd.robot_id+"/"+CLIENT_NAME+"/reply" , qos = 2, retain = False )
                else:
                    logger.debug("[call:"+cmd.state +"] Wait for release. ( " + str(round(time.time()-cmd.t_into_state,2)) + "/" + str(DOOR_OPEN_LIMIT_TIME)+" )")
        else:
            cmd.state = "finish"
        return
    def is_human_override(self, omit):
        '''
        Input:
            omit[] : buttons that don't want to check(usually are button EVB pushed) 
        Output:
            return True : HUMAN
            return False : human non-detected
        '''
        return False
        for i in table:
            if i not in omit and self.pb.EVledRead(i, retryTime=1)==1:
               return True
        return False
    
    def precall(self, floor=0):
        '''
        Push floor button when EV is not using.
        Input:
            floor: Which floor you want to call (cmd.target_floor) 
        '''
        if floor in table:
            if not self.is_human_override([]):
                self.single_hit(floor) #hit with 0.2sec
                logger.info("[precall] Successfully push "+ str(floor) + " floor button.")
            else:
                logger.info("[precall] Fail to push "+ str(floor) + "floor button, Ev is not vacanccy.")
            return
        else:
            logger.error("[precall] "+str(floor)+" floor is not available!")
            # return "precall push floor button,  ", msg

    def open(self):
        self.pb.EVledWrite('open', 'high')
        self.pb.EVledWrite('close', 'low')
        if self.open_moment == None: # Timer not start yet.
            self.open_moment = time.time()
            logger.debug("[open] Start door release countdown. (0 / " +str(DOOR_OPEN_LIMIT_TIME) + " )")
        else: # Timer already started , reset it.
            logger.debug("[open] Reset door release countdown. (" +str(time.time() - self.open_moment)+ " / " + str(DOOR_OPEN_LIMIT_TIME) + ")")
            self.open_moment = time.time()
        logger.info("[open]")
        return

    def close(self):
        self.pb.EVledWrite('open', 'low')
        self.single_hit('close', 0.2)# press 'close' button for 0.2 sec
        if self.open_moment != None:
            logger.debug("[close] Cancel door release countdown. (" +str(time.time() - self.open_moment)+ " / " + str(DOOR_OPEN_LIMIT_TIME) + ")")
            self.open_moment = None
        logger.info("[close]")
        return
    
    def single_hit(self, button, t=0.2):
        '''
        Hit button for t sec.
        '''
        self.pb.EVledWrite(button, 'high')
        time.sleep(t)
        self.pb.EVledWrite(button, 'low')
        return 
        
    def reboot(self):
        os.system('sync;sync;')
        # Cut L432KC power off 
        #os.system('echo "odroid" | sudo -S ./utility/hub-ctrl -h 0 -P 2 -p 0')
        #time.sleep(1)
        os.system('sync;sync;')
        # Reboot R-pi
        os.system('echo "odroid" | sudo -S reboot')
        return 
        
    def release_button(self):
        self.pb.EVledWrite('open', 'low')
        self.pb.EVledWrite('close', 'low')
        if self.open_moment != None:
            logger.debug("[release_button] Cancel door release countdown. (" +str(time.time() - self.open_moment)+ " / " + str(DOOR_OPEN_LIMIT_TIME) + ")")
            self.open_moment = None
        logger.info("[release_button]")
        return
