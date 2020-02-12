#!/usr/bin/env python

from XBEE.xbee_template import BLUE_COM
from global_var.global_logger import logger
from global_var.global_param import XBEE_HOST_IP , CLIENT_NAME
import signal 
import threading 
import time 
import json

######################
###  Exit handler  ###
######################
is_running = True
def sigint_handler(signum, frame):
    global is_running
    is_running = False
    logger.warning('[sigint_handler] catched interrupt signal!')
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

###########################
###  Callback function  ###
###########################
def BT_cmd_CB (msg):
    logger.info("Get msg from BT_cmd_CB : " + str(msg))


#########################################
###   Config of bluetooth connction   ###
#########################################
blue_com = BLUE_COM(logger, host = XBEE_HOST_IP, port = 1)
blue_com.add_cmd_CB(BT_cmd_CB)
blue_com.client_engine_start()

user_type = "" 

def input_fun(): 
    global user_type
    while is_running: 
        user_type = raw_input('Send:') # Check q to quit TODO 


###############
###  Loop   ###
###############
input_thread = threading.Thread(target = input_fun)
input_thread.start()


while is_running :
    if user_type != "":
        if user_type == 'q':
            is_running = False 
            break
        robot_id = 'AMR250_TEST'
        tid = "7777.8888"
        current_floor = "1"
        target_floor = "4"
        paylaod_dict = {}
        user_type_list = user_type.split()

        # ------ Utility cmd ------# 
        if  user_type_list[0] == 'open' or user_type_list[0] == 'close' or user_type_list[0] == 'release_button' :
            paylaod_dict  = json.dumps({"cmd" : user_type_list[0] , "robot_id" : robot_id , "tid" : tid})
        # ------ Often Used cmd ------# 
        elif user_type_list[0] == 'call':
            try: 
                current_floor = user_type_list[1]
                target_floor  = user_type_list[2]
                paylaod_dict  = json.dumps({"cmd" : user_type_list[0] , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
            except:
                logger.error("[MQTT_cmd_CM] unknow cmd ") 
        elif user_type_list[0] == 'precall':
            try: 
                target_floor = user_type_list[1]
                paylaod_dict  = json.dumps({"cmd" : user_type_list[0] , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
            except:
                logger.error("[MQTT_cmd_CM] unknow cmd ")
        elif user_type_list[0] == 'enter':
            paylaod_dict  = json.dumps({"cmd" : "entering_done" , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
        elif user_type_list[0] == 'rele':
            paylaod_dict  = json.dumps({"cmd" : "release" , "robot_id" : robot_id , "tid" : tid , "current_floor" : current_floor, "target_floor":target_floor })
        elif user_type_list[0] == 'reboot':
            paylaod_dict  = json.dumps({"cmd" : user_type_list[0] , "robot_id" : robot_id , "tid" : tid , "pw" : "elevator_server"})
        #----   Test cmd   -----# 
        
        elif user_type_list[0] == 'w':
            try: 
                key = user_type_list[1]
                d   = user_type_list[2]
                paylaod_dict  = json.dumps({"cmd" : "EVledWrite" , "key" : key , "d" : d })
            except:
                logger.error("[MQTT_cmd_CM] unknow cmd ") 
        elif user_type_list[0] == 'r':
            try: 
                key = user_type_list[1]
                paylaod_dict  = json.dumps({"cmd" : "EVledRead" , "key" : key })
            except:
                logger.error("[MQTT_cmd_CM] unknow cmd ") 
        
        elif user_type_list[0] == 'sudo_release':
            paylaod_dict  = json.dumps({"cmd" : user_type_list[0] })
        else: 
            logger.error("[MQTT_cmd_CM] unknow cmd ")
            user_type = "" 
            continue

        blue_com.send(paylaod_dict)
        user_type = ""

    # Wait 1 sec 
    time.sleep(1)
input_thread.join(1)

#####################
###   End Engine  ###
#####################
print ("[Main] DISCONNECT ")
blue_com.client_engine_stop()







