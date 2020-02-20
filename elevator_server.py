#!/usr/bin/python
import os
import sys
import time
import json
import signal
from cmd_struct import cmdStruct
from global_var.global_logger import logger
from elevator_cmd import ElevatorCmd
from global_var.global_param import table, IS_SIMULATION, IS_USING_MQTT, AMR_MQTT_NAME, IS_USING_HTTP, is_using_rss, IS_USING_XBEE

#---- weixin alarm to cell phone -----# 
if is_using_rss: 
    from weixin_alarm import alarm
#---- XBEE globaly import -----# 
if IS_USING_XBEE:
    from global_var.global_xbee import xbee_obj 
    # os.system("pppd /dev/xbee 9600 lock nodetach noauth crtscts mtu 576 persist maxfail 0 holdoff 1 195.0.0.13:195.0.0.12")
#----- MQTT globaly import -----# 
if IS_USING_MQTT:
    from global_var.global_mqtt import mqtt_obj, CLIENT_NAME
#----- HTTP globaly import -----# 
if IS_USING_HTTP:
    import cherrypy
    from cherrypy.process.plugins import SimplePlugin

class TaskManager():
    '''
    This class should pull out to be a .py file, if there is any need of centeral control mission.
    '''
    def __init__(self):
        self.req_list = []
        self.is_sudo_release = False
    def addTask(self, cmd):
        self.req_list.append(cmd)
        #self.printReq()
    def delTask(self, idx):
        del self.req_list[idx]
        #self.printReq()
    def printReq(self):
        '''
        Lazy fucntion, print out req_list
        '''
        for i in self.req_list:
            logger.info("type: " +str(i.type)+"     robot_id: "+ str(i.robot_id)+"     tid: " + str(i.tid) + "     current_floor: " + str(i.current_floor) +"    target_floor: " + str(i.target_floor))

# Task arrangement
EC = ElevatorCmd()
TM = TaskManager()

class Elevator_server(object):
    '''
    Check Cmd is valid or not, if not Reject it. Put Cmd into  TM to let elevertor_cmd.py execute it.
    '''
    #####################
    ###  Utility cmd  ###
    #####################
    def index(self):
        msg = 'EV_board server start!'
        logging.info(msg)
        return msg
    def open(self,robot_id=1, tid=0):
        '''
        Open elevator door (This function will keep door open until DOOR_OPEN_LIMIT_TIME is reached.)
        '''
	    #TOOD check
        cmd = cmdStruct('open', robot_id, tid, 0, 0)
        TM.addTask(cmd)
        return str(tid)
    def release_button(self,robot_id=0, tid=0):
	    #TOOD check
        cmd = cmdStruct('release_button', robot_id, tid, 0, 0)
        TM.addTask(cmd)
        return str(tid)
    def close(self,robot_id=0, tid=0):
        #TOOD check
        cmd = cmdStruct('close', robot_id, tid, 0, 0)
        TM.addTask(cmd)
        return str(tid)
    
    ########################
    ###  Often Used cmd  ###
    ########################
    def call(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
        '''
        AMR call elevator to carry AMR from current_floor to target_floor.
        '''
        if current_floor in table and target_floor in table:
            # Check if same cmd is working
            for i in TM.req_list:
                if i.tid == tid: # Already have same tid in req_list
                    logger.warning("[call] REJECT call. Already have same tid in req_list. tid: " + str(tid))
                    return str(tid) # ignore this cmd
            cmd = cmdStruct('call', robot_id, tid, current_floor, target_floor)
            logger.info("[call] Accpeted call. "+ str(current_floor) +"F --> "+ str(target_floor) + "F, tid: " + str(tid) + ", robot_id: " + str(robot_id))
            TM.addTask(cmd)# There is no identical cmd, add it!
        else:
            return "Invalid floor request."
        return str(tid)
    
    def precall(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
        '''
        Push floor button only 
        '''
        cmd = cmdStruct('precall', robot_id, tid, current_floor, target_floor)
        TM.addTask(cmd)
        return str(tid) 
    
    def entering_done(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
        try:
            if   TM.req_list[0].type     != 'call':
                logger.error("[entering_done] REJECT entering_done. No matched cmd.")
            elif TM.req_list[0].robot_id != robot_id:
                logger.error("[entering_done] REJECT entering_done. robot_id not matched.")
                TM.req_list[0].total_logger.append(("cmd_entering_done_reject", time.time()))
            elif TM.req_list[0].tid      != tid:           
                logger.error("[entering_done] REJECT entering_done. tid not matched.")
                TM.req_list[0].total_logger.append(("cmd_entering_done_reject", time.time()))
            else: 
                logger.info("[entering_done] Accpeted entering_done cmd. Match tid: "+ str(tid))
                TM.req_list[0].total_logger.append(("cmd_entering_done_accpet", time.time()))
                TM.req_list[0].is_entering_done = True
        except:
            logger.error("[entering_done] REJECT entering_done. No matched cmd.")
        return str(tid)
    
    def release(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
        '''
        release current mission
        '''
        try:
            if   TM.req_list[0].type     != 'call':
                logger.error("[release] REJECT release. No matched cmd.")
            elif TM.req_list[0].robot_id != robot_id:
                logger.error("[release] REJECT release. robot_id not matched.")
                TM.req_list[0].total_logger.append(("cmd_release_reject", time.time()))
            elif TM.req_list[0].tid      != tid:
                logger.error("[release] REJECT release. tid not matched.")
                TM.req_list[0].total_logger.append(("cmd_release_reject", time.time()))
            else: 
                logger.info("[release] Accpeted release cmd. Match tid: "+ str(tid))
                TM.req_list[0].total_logger.append(("cmd_release_accpet", time.time()))
                TM.req_list[0].is_release = True
        except:
            logger.error("[release] REJECT release. No matched cmd.")
        return str(tid)
    
    ##################
    ###  Test Cmd  ###
    ##################
    def EVledWrite(self,key=0, d=0):
        '''
        Expose for elevator testing and tuning, DO NOT use this in normal process.
        '''
        if key in table:
            if d == "high" or d == "low":
                return str(EC.pb.EVledWrite(str(key), str(d)))
            else:
                return "invalid digital assign"
        else:
            return "REJECT! Can't find key. Do you type it right?"
    
    def EVledRead(self,key=0):
        '''
        Expose for elevator testing and tuning, DO NOT use this in normal process.
        '''
        if key in table:
            return str(EC.pb.EVledRead(str(key)))
        else:
            return "REJECT! Can't find key. Do you type it right?"
    
    def reboot(self, robot_id=0, tid=0, pw=0):
        '''
        Reboot Raspberry-Pi and L432KC. L432KC power will be cut before Raspberry-Pi, to make sure "deep reboot" of MCU.
        '''
        if pw=='elevator_server':
            cmd = cmdStruct('reboot', robot_id, tid,0, 0)
            TM.addTask(cmd)
            return str(tid)
        else:
            return "Wrong password, permission denied."
    
    def sudo_release(self):
        '''
        for Test
        '''
        TM.is_sudo_release = True
        return "OK"

    def weixin_test(self):
        '''
        for rss Test
        '''
        if is_using_rss:
            alarm.sent("[elevator_server] WeiXin Test !!! ")
        else: 
            logger.info("weixin alarm is not allow, please go to parma.yaml and switch is_using_rss to True.")
        return "OK"


######################
###  Cmd CallBack  ###
######################
Ele_Ser = Elevator_server()

if IS_USING_XBEE: 
    def xbee_cmd_CB(msg):
        # logger.info("Get msg from main : " + msg) 
        '''
        This is a cmd_CB from MQTT subscribe topic 
        '''
        logger.info("[XBEE] xbee_cmd_CB :  " + str(msg))
        # Parse payload and Add task to req_list[]
        cmd_dict = json.loads(msg)
        # ------ Utility cmd ------# 
        if  cmd_dict['cmd'] == 'open':
            Ele_Ser.open(cmd_dict['robot_id'], cmd_dict['tid'])
        elif cmd_dict['cmd'] == 'close':
            Ele_Ser.close(cmd_dict['robot_id'], cmd_dict['tid'])
        elif cmd_dict['cmd'] == 'release_button':
            Ele_Ser.release_button(cmd_dict['robot_id'], cmd_dict['tid'])
        # ------ Often Used cmd ------# 
        elif cmd_dict['cmd'] == 'call':
            Ele_Ser.call(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'precall':
            Ele_Ser.precall(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'reboot':
            Ele_Ser.reboot(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['pw'])
        elif cmd_dict['cmd'] == 'entering_done':
            Ele_Ser.entering_done(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'release':
            Ele_Ser.release(cmd_dict['robot_id'], cmd_dict['tid'])
            #----   Test cmd   -----# TODO TODO 
            '''
            elif cmd_dict['cmd'] == 'EVledWrite':
                ans = Ele_Ser.EVledWrite(cmd_dict['key'], cmd_dict['d'])
                topic_list = message.topic.split("/")
                mqtt_obj.publish(topic_list[0]+"/"+topic_list[1]+"/reply", ans, qos = 1, retain = False)
            elif cmd_dict['cmd'] == 'EVledRead':
                ans = Ele_Ser.EVledRead(cmd_dict['key'])
                topic_list = message.topic.split("/")
                mqtt_obj.publish(topic_list[0]+"/"+topic_list[1]+"/reply", ans, qos = 1, retain = False)
            elif cmd_dict['cmd'] == 'sudo_release':
                Ele_Ser.sudo_release()
            elif cmd_dict['cmd'] == 'weixin_test':
                Ele_Ser.weixin_test()
            '''
        else: 
            logger.error("[MQTT_cmd_CM] unknow cmd ") 

if IS_USING_MQTT:
    def mqtt_cmd_CB(client, userdata, message):
        '''
        This is a cmd_CB from MQTT subscribe topic
        '''
        logger.info("[MQTT] cmd_CB :  " + str(message.payload) + "(Q" + str(message.qos) + ", R" + str(message.retain) + ")")
        # Parse payload and Add task to req_list[]
        try: 
            cmd_dict = json.loads(message.payload.decode())
        except:
            logger.error("[MQTT_cmd_CM] invalid cmd formet ")
            return 
        # ------ Utility cmd ------# 
        if   cmd_dict['cmd'] == 'open':
            Ele_Ser.open(cmd_dict['robot_id'], cmd_dict['tid'])
        elif cmd_dict['cmd'] == 'close':
            Ele_Ser.close(cmd_dict['robot_id'], cmd_dict['tid'])
        elif cmd_dict['cmd'] == 'release_button':
            Ele_Ser.release_button(cmd_dict['robot_id'], cmd_dict['tid'])
        # ------ Often Used cmd ------# 
        elif cmd_dict['cmd'] == 'call':
            Ele_Ser.call(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'precall':
            Ele_Ser.precall(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'reboot':
            Ele_Ser.reboot(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['pw'])
        elif cmd_dict['cmd'] == 'entering_done':
            Ele_Ser.entering_done(cmd_dict['robot_id'], cmd_dict['tid'], cmd_dict['current_floor'],cmd_dict['target_floor'])
        elif cmd_dict['cmd'] == 'release':
            Ele_Ser.release(cmd_dict['robot_id'], cmd_dict['tid'])
        #----   Test cmd   -----# 
        elif cmd_dict['cmd'] == 'EVledWrite':
            ans = Ele_Ser.EVledWrite(cmd_dict['key'], cmd_dict['d'])
            topic_list = message.topic.split("/")
            mqtt_obj.publish(topic_list[0]+"/"+topic_list[1]+"/reply", ans, qos = 1, retain = False)
        elif cmd_dict['cmd'] == 'EVledRead':
            ans = Ele_Ser.EVledRead(cmd_dict['key'])
            topic_list = message.topic.split("/")
            mqtt_obj.publish(topic_list[0]+"/"+topic_list[1]+"/reply", ans, qos = 1, retain = False)
        elif cmd_dict['cmd'] == 'sudo_release':
            Ele_Ser.sudo_release()
        elif cmd_dict['cmd'] == 'weixin_test':
            Ele_Ser.weixin_test()
        else: 
            logger.error("[MQTT_cmd_CM] good cmd forment, but don't know this cmd.") 

        
if IS_USING_HTTP: 
    class cherrypy_cmd_CB(object):
        @cherrypy.expose
        def index(self):
            msg = "[Cherrypy] EV_board server start!"
            logging.info(msg)
            return msg
        @cherrypy.expose
        def open(self,robot_id=1, tid=0):
            return Ele_Ser.open(robot_id, tid)
        @cherrypy.expose
        def release_button(self,robot_id=0, tid=0):
            return Ele_Ser.release_button(robot_id, tid)
        @cherrypy.expose
        def close(self,robot_id=0, tid=0):
            return Ele_Ser.close(robot_id, tid)
        
        ########################
        ###  Often Used cmd  ###
        ########################
        @cherrypy.expose
        def call(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
            return Ele_Ser.call(robot_id, tid, current_floor, target_floor)
        @cherrypy.expose
        def precall(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
            return Ele_Ser.precall(robot_id, tid, current_floor, target_floor)
        @cherrypy.expose
        def entering_done(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
            return Ele_Ser.entering_done(robot_id, tid, current_floor, target_floor)
        @cherrypy.expose
        def release(self, robot_id=0, tid=0, current_floor=0, target_floor=0):
            return Ele_Ser.release(robot_id, tid, current_floor, target_floor)
        
        ##################
        ###  Test Cmd  ###
        ##################
        @cherrypy.expose
        def EVledWrite(self,key=0, d=0):
            return Ele_Ser.EVledWrite(key,d)
        @cherrypy.expose
        def EVledRead(self,key=0):
            return Ele_Ser.EVledRead(key)
        @cherrypy.expose
        def reboot(self, robot_id=0, tid=0, pw=0):
            return Ele_Ser.reboot(robot_id, tid, pw)
        @cherrypy.expose
        def sudo_release(self):
            return Ele_Ser.sudo_release()
        @cherrypy.expose
        def weixin_test(self):
            return Ele_Ser.weixin_test()
    
def main():
    global EC, TM
    if TM.is_sudo_release:
        logger.error("[cherrpy_expose] SUDO RELEASE ACCPECT!!")
        EC.release_button()
        TM.is_sudo_release = False
        TM.req_list = []
    # Routine check DOOR OPEN TIMEOUT
    if EC.door_release_checker(): # TIMEOUT
        EC.release_button()
        if len(TM.req_list) != 0 and TM.req_list[0].type == 'call':
            TM.req_list[0].is_timeout_release = True

    if len(TM.req_list) == 0: # Nothing to do
        pass
    else: # Keep doing cmd
        if TM.req_list[0].type == 'open':
            EC.open()
            TM.delTask(0)
        elif TM.req_list[0].type == 'close':
            EC.close()
            TM.delTask(0)
        elif TM.req_list[0].type == 'release_button':
            EC.release_button()
            TM.delTask(0)
        elif TM.req_list[0].type == 'call':
            EC.call_iterateOnce(TM.req_list[0])
            # Check Finish
            if TM.req_list[0].state == "finish":
                logger.info("[Main] END CALL(tid: " + str(TM.req_list[0].tid) + ")")
                TM.req_list[0].total_logger.append(("end", time.time()))
                TM.req_list[0].total_logging()
                EC.release_button()
                TM.delTask(0)
        elif TM.req_list[0].type == 'precall':
            EC.precall(TM.req_list[0].target_floor)
            TM.delTask(0)
        elif TM.req_list[0].type == 'reboot':
            EC.reboot()
            TM.delTask(0)
        else:
            pass

is_running = True 
def sigint_handler(signum, frame):
    global is_running
    is_running = False
    logger.warning('[sigint_handler] catched interrupt signal!')
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


if __name__ == '__main__':
    #----- Simulation -----#
    if IS_SIMULATION:
        pass 
    if IS_USING_MQTT:
        # ------- Subcriber  ----------#
        sub_list = [] 
        for i in AMR_MQTT_NAME: # Add all AMR cmd topic into subscribe
            sub_list.append(( i+"/"+CLIENT_NAME+"/cmd", 2, mqtt_cmd_CB))
        mqtt_obj.add_subscriber(sub_list)
    if IS_USING_HTTP:
        # MainPlugin(cherrypy.engine).subscribe()
        cherrypy.config.update({# 'server.socket_host': os.popen('hostname -I').readlines()[0].strip(),
                                'server.socket_host': '0.0.0.0' ,  
                                'server.socket_port': 8080,
                            })
        cherrypy.tree.mount(cherrypy_cmd_CB(), "")
        cherrypy.engine.start()
    if IS_USING_XBEE:
        xbee_obj.add_cmd_CB(xbee_cmd_CB)
        xbee_obj.server_engine_start()
    ##########################
    ###   Main While Loop  ###
    ##########################
    logger.info("[main] Successfully boot elevator server")
    while is_running: # Will switch to False, by SIGTERM, SIGINT, SIGHUP
        #try:
        main()
        #except: 
        #    logger.error("[main] Something Wrong at main()")
        time.sleep(0.1)# 10HZ
    # If program is terminated
    if IS_USING_HTTP:
        cherrypy.engine.stop() # Remember to stop cherrypy engine, to avoid blocking thread.
    if IS_USING_XBEE:
        xbee_obj.server_engine_stop()
