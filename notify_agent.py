import requests
import yaml
import json
import time
import threading
from global_var.global_logger import logger
from global_var.global_param import NOTIFY_MAX_RETRY_TIME, AMR_URI, IS_USING_HTTP , IS_USING_MQTT, IS_USING_XBEE, is_using_rss
if is_using_rss: 
    from weixin_alarm import alarm
if IS_USING_MQTT:
    from global_var.global_mqtt import mqtt_obj
if IS_USING_XBEE:
    from global_var.global_xbee import xbee_obj
s = requests.Session()

class notify_agent():
    def __init__(self):
        # Input
        self.payload = None  
        # ----- HTTP ------#
        self.http_payload = None # dict: {robot_id: 2 , tid: 1234.5678, current_floor:1 ..... }
        self.http_req = None # : http://192.168.64.12:8080/reached/
        self.http_try_times = None
        self.http_thread = None 
        #------ MQTT ------#
        self.mqtt_payload = None 
        self.topic = None
        self.qos = None 
        self.retain = None 
        self.mqtt_rc = None 
        #------ XBEE ------# 
        self.xbee_payload = None 
        self.xbee_rc = None 
        # State
        self.state = "stand_by" # "stand_by "completed" "abort" "trying"
        self.notify_t_start = None 
    
    def clear(self):
        # Input 
        self.payload = None 
        # ----- HTTP ------#
        self.http_payload = None # dict: {robot_id: 2 , tid: 1234.5678, current_floor:1 ..... }
        self.http_req = None # : http://192.168.64.12:8080/reached/
        self.http_try_times = None
        self.http_thread = None 
        #------ MQTT ------#
        self.mqtt_payload = None 
        self.topic = None
        self.qos = None 
        self.retain = None 
        self.mqtt_rc = None 
        #------ XBEE ------# 
        self.xbee_payload = None 
        self.xbee_rc = None 
        # State
        self.state = "stand_by" # "stand_by "completed" "abort" "trying"
        self.notify_t_start = None 
    
    def set_notify(self, payload = {}, topic = "topic" , qos = 2, retain = False ):
        '''
        payload is dict()
        You don't have to pass 'topic', 'qos' ... arg , when you switch IS_USING_MQTT to False 
        '''
        if self.state == "stand_by": # Accepted
            self.payload = payload
            # Input
            if IS_USING_HTTP:
                self.http_payload = payload.copy()
                del self.http_payload['cmd']
                self.http_req = AMR_URI + payload['cmd']
                self.http_try_times = 0
                self.http_thread = None 
            if IS_USING_MQTT:
                self.mqtt_payload = payload
                self.topic = topic
                self.qos = qos
                self.retain = retain
                self.mqtt_rc = None 
            if IS_USING_XBEE:
                self.xbee_payload = payload
                self.xbee_rc = None 
            
            # State
            self.state = "trying" # "completed" "abort" "trying"
            self.notify_t_start = time.time() # Counting time 

            #---- MQTT publish (non-blocking) ------#
            if IS_USING_MQTT:
                if mqtt_obj.available == "online": 
                    self.mqtt_rc = mqtt_obj.publish(self.topic, json.dumps(self.mqtt_payload), self.qos, self.retain)
                else: #  
                    logger.warning("[set_notify] One of the client is not online")
            #---- XBEE publish (non-blocking) ------#
            if IS_USING_XBEE:
                self.xbee_rc = xbee_obj.send(payload = json.dumps(self.xbee_payload))

            #----- HTTP publish (blocking)  ---------#
            if IS_USING_HTTP:
                self.http_thread = threading.Thread(target = self.http_notify)
                self.http_thread.start()
        else:
            logger.error('[notify_agent] Rejected to notify AMR' + str(http_payload['cmd']) + ', because previous task is not done yet.')
            return False
    
    def abort_handle(self):
        #----- Print Out log and rss -------# 
        if IS_USING_XBEE:
            logger.error('[notify_agent] XBEE wait for send AWK for ' + str(time.time() - self.notify_t_start ) + ' sec, abort.')
            if is_using_rss: 
                alarm.sent    ('[notify_agent] XBEE wait for send AWK for ' + str(time.time() - self.notify_t_start ) + ' sec, abort.')
        if IS_USING_MQTT:
            logger.error('[notify_agent] MQTT wait for publish callback for ' + str(time.time() - self.notify_t_start ) + ' sec, abort.')
            if is_using_rss: 
                alarm.sent    ('[notify_agent] MQTT wait for publish callback for ' + str(time.time() - self.notify_t_start ) + ' sec, abort.')
        if IS_USING_HTTP:
            logger.error('[notify_agent] retried ' + str(self.http_try_times) + ' times, but still failed to notify AMR ' + str(self.http_req) + ', give it up.')
            if is_using_rss: 
                alarm.sent    ('[notify_agent] retried ' + str(self.http_try_times) + ' times, but still failed to notify AMR ' + str(self.http_req) + ', give it up.')
        self.state = "abort"
    
    def http_notify(self):
        logger.info('[notify_agent] HTTP request to send ' + self.http_req)
        try:
            r = s.get(self.http_req, params=self.http_payload, timeout=10)# MAX wait for 10sec
            logger.info('[notify_agent] Got status_code :  (' +  str(r.status_code))
        except:
            pass
        else:
            # succesfully try  
            if r.status_code == requests.codes.ok and self.state == "trying": 
                logger.info('[notify_agent] HTTP completed to send ' + self.http_req + ", received " + str(r))
                self.state  = "completed"
                return
        # Need to retry !
        if self.state == "trying": # To check if MQTT is done first.
            self.http_try_times += 1
            logger.warning('[notify_agent] HTTP Fail to notify AMR. (retry:' +  str(self.http_try_times) + ")")

    def notify_iterateOnce(self):
        if self.state == "completed" or self.state == "stand_by":
            pass
        elif self.state == "abort":
            self.abort_handle()
        elif self.state == "trying":
            #------ Check for Timeout! -------# 
            if time.time() - self.notify_t_start >= NOTIFY_MAX_RETRY_TIME: # 60 sec 
                self.abort_handle()
                return 
            #------ XBEE -------# 
            if IS_USING_XBEE:# Non-blocking no need to start a thread.
                if self.xbee_rc == None: # Didn't publish because client is current offline
                    self.xbee_rc = xbee_obj.send(payload = self.xbee_payload) # Keep trying 
                else: 
                    if self.xbee_rc.is_awk:  # == True , is AWK by amr 
                        self.state = "completed"
                        return 
                    else: # False, Still waiting CB
                        logger.debug("[notify_agent] XBEE waiting send AWK")
            #------ MQTT -------# 
            if IS_USING_MQTT:# Non-blocking no need to start a thread.
                if self.mqtt_rc == None: # Didn't publish because client is current offline
                    self.mqtt_rc = mqtt_obj.publish(self.topic, json.dumps(self.mqtt_payload), self.qos, self.retain) # keep trying
                else: 
                    if self.mqtt_rc.is_published(): # == True , Finish all handshake with broker (qos1, qos2)
                        self.state = "completed"
                        return 
                    else: # False, Still waiting CB
                        logger.debug("[notify_agent] MQTT waiting publish CB")
            #------- HTTP -------#
            if IS_USING_HTTP:
                if self.http_thread.is_alive(): # threading is alive. keep wait.
                    pass
                    #print ("http threading is alive")
                else: # http theard is finished 
                    if self.state != "completed": # Retry
                        self.http_thread = threading.Thread(target = self.http_notify)
                        self.http_thread.start()
                    else: # HTTP Completed 
                        return 
        time.sleep(1)
        return
