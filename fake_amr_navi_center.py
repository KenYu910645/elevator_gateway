#!/usr/bin/env python
import time
import sys
import signal
import posix_ipc
import paho.mqtt.client as mqtt
from global_var.global_logger import logger
import json
from MQTT.mqtt_template import MQTT_OBJ
from global_var.global_param import BROKER_IP, AMR_MQTT_NAME, IS_SIMULATION

CLIENT_NAME = "test" # Tow different mqtt client MUST have different name. '#' , '+' , '/' are NOT allow in topic name
is_ev_available = ""

is_running = True 
def sigint_handler(signum, frame):
    # mq_recv.close()
    global is_running
    is_running = False
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

############################
###  CallBack functions  ###
############################

def ev_status_CB(client, userdata, message):
    logger.info("[MQTT] ev_status_CB :  " + str(message.payload) + "(Q" + str(message.qos) + ", R" + str(message.retain) + ")")
    # TODO 

def elevator_server_available_CB(client, userdata, message):
    global is_ev_available
    logger.info("[MQTT] elevator_server_available_CB :  " + str(message.payload) + "(Q" + str(message.qos) + ", R" + str(message.retain) + ")")
    is_ev_available = message.payload

def ev_reply_CB(client, userdata, message):
    logger.info("[MQTT] ev_reply_CB :  " + str(message.payload) + "(Q" + str(message.qos) + ", R" + str(message.retain) + ")")
    # TODO 

if __name__ == '__main__':
    #########################
    ###  MQTT Connection  ###
    #########################
    '''
    Init MQTT_OBJ will automative connect to broker and start a background thread for mqtt network
    client_id , broker_ip , logger  : should be setup right.
        logger is a python logging handle, if you don't want to use it , pass None . (logger = None)
    '''
    mqtt_obj = MQTT_OBJ(client_id=CLIENT_NAME, broker_ip=BROKER_IP, port=1883, keepalive=10, clean_session=True, logger = logger)
        # Wait for connection Accpeted by broker (Optional) 
    while mqtt_obj.available != "online":
        time.sleep(0.1)
    #########################
    ###      Subcriber    ###
    #########################
    '''
    Add your subcribe topic  in this function  [ (topic1, qos,  Callback_fun1),  (topic2, qos, Callback_fun2), (...) , .... ]
    '''
    mqtt_obj.add_subscriber([ (CLIENT_NAME+"/elevator_server/status", 2, ev_status_CB) , (CLIENT_NAME+"/elevator_server/reply", 2, ev_reply_CB) , ("elevator_server/available", 2, elevator_server_available_CB)])

    if IS_SIMULATION: 
        mq_recv = posix_ipc.MessageQueue('/button_IPC', posix_ipc.O_CREAT)
        mq_recv.block = True  # non-blocking recv , send
    
    while is_running:
        # --------- Check Mqtt Connection ---------# 
        # User should always check current connection status, before publishing any message.
        
        user_type = ""
        if IS_SIMULATION:
            r = mq_recv.receive() # blocking
            user_type = r[0].decode()
        else:
            try:
                user_type = input("Type Cmd: ")
            except: 
                print ("ERROR on input ()")
            else:
                if user_type == 'q':
                    break
        
        if mqtt_obj.available == "offline":
            logger.warn("[MQTT] No Mqtt Connection")
            # TODO 
        else: # Online
            ##################################################
            ###  Publish something don't need to track   #####
            ##################################################
            # Non-blocking publish , suitable for qos0.
            # mqtt_obj.publish(topic = CLIENT_NAME+"/position", payload = "432", qos = 1, retain = False)
            #### Blocking publish
            # mqtt_obj.publish_blocking(topic = "elevator/status", payload = "test test test ", qos = 1, retain = False, timeout = 10)
            
            #############################
            ###  Publish with track   ###
            #############################
            # Using publish result to track publish handshake is completed or not.
            # if is_ev_available == "online" and mqtt_obj.available == "online":  # TODO 
            if True : 
                robot_id = CLIENT_NAME
                tid = "7777.8888"
                current_floor = "1"
                target_floor = "4"
                paylaod_dict = {}
                user_type_list = user_type.split()
                print (user_type_list)
                try: 
                    cmd_type = user_type_list[0]
                except:
                    continue
                # ------ Utility cmd ------# 
                # open -> open elevator door
                # close -> close elevator door 
                if  cmd_type == 'open' or cmd_type == 'close' or cmd_type == 'release_button' :
                    paylaod_dict  = json.dumps({"cmd" : cmd_type , "robot_id" : robot_id , "tid" : tid})
                # ------ Often Used cmd ------# 
                # call X Y, AMR call elevator to pick up AMR at X floor and put down AMR at Y floor  
                elif cmd_type == 'call':
                    try: 
                        current_floor = user_type_list[1]
                        target_floor  = user_type_list[2]
                        paylaod_dict  = json.dumps({"cmd" : cmd_type , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
                    except:
                        logger.error("[MQTT_cmd_CM] unknow cmd ")
                        continue
                # Press floor button 
                # 'precall 1' -> press floor 1 button ,  'precall 4' -> press floor 4 button
                elif cmd_type == 'precall':
                    try: 
                        target_floor = user_type_list[1]
                        paylaod_dict  = json.dumps({"cmd" : cmd_type , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
                    except:
                        logger.error("[MQTT_cmd_CM] unknow cmd ")
                        continue
                # Tell elevator server AMR has already enter elevator
                elif cmd_type == 'enter':
                    paylaod_dict  = json.dumps({"cmd" : "entering_done" , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
                # Release control over elevator
                elif cmd_type == 'rele':
                    paylaod_dict  = json.dumps({"cmd" : "release" , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
                # Reboot elevator server 
                elif cmd_type == 'reboot':
                    paylaod_dict  = json.dumps({"cmd" : cmd_type , "robot_id" : robot_id , "tid" : tid , "pw" : "elevator_server"})
                #----   Test cmd   -----# 
                # 'w 1 0' => write key 1 to low , 'w 4 1' -> write key 4 to high
                elif cmd_type == 'w':
                    try: 
                        key = user_type_list[1]
                        d   = user_type_list[2]
                        paylaod_dict  = json.dumps({"cmd" : "EVledWrite" , "key" : key , "d" : d })
                    except:
                        logger.error("[MQTT_cmd_CM] unknow cmd ") 
                # 'r 1' -> read key 1 is high or low , 'r 3' -> read key 3 is high or low
                elif cmd_type == 'r':
                    try: 
                        key = user_type_list[1]
                        paylaod_dict  = json.dumps({"cmd" : "EVledRead" , "key" : key })
                    except:
                        logger.error("[MQTT_cmd_CM] unknow cmd ")
                # manditory release control over elevator
                elif cmd_type == 'sudo_release':
                    paylaod_dict  = json.dumps({"cmd" : cmd_type })
                # 
                elif cmd_type == 'reached':
                    mqtt_obj.publish(topic = 'AMR250_3/elevator_server/reply', payload=json.dumps({"cmd" : "reached" , "robot_id" : "AMR250_3", "floor" : '1' }), qos=2, retain = False)
                    continue
                else: 
                    logger.error("[MQTT_cmd_CM] unknow cmd ") 
                    continue
                
                rc = mqtt_obj.publish(topic = AMR_MQTT_NAME[0]+"/elevator_server/cmd", payload = paylaod_dict, qos = 2, retain = False)
                if rc == None: 
                    # Didn't publish because client is current offline
                    # TODO 
                    pass
                else: 
                    if rc.is_published(): # == True , Finish all handshake with broker (qos1, qos2)
                        # TODO 
                        pass
                    else: 
                        pass
            else: 
                logger.warn("[MQTT] One of the client is not online.")
        time.sleep(0.01)
