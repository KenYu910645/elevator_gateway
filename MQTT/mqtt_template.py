#!/usr/bin/env python
import time
import paho.mqtt.client as mqtt
from MQTT.private_logger import private_logger

IS_PUB_WITHOUT_CONNECT = False # Set to True, if want to publish without checking mqtt connection (msg will be queue at mqtt client)
IS_PUB_LOG = True # Set to True, to logging publish msg and publish CB information

class MQTT_OBJ():
    def __init__(self,client_id="service_provider", broker_ip="iot.eclipse.org", port=1883, keepalive=10, clean_session=False, logger = None ):
        # -----   Member variable --------#
        self.logger = logger
        if self.logger == None : # NO logger specified 
            self.logger = private_logger
        self.sub_list = [] # Record subscribe topic
        self.client_id = client_id
        self.available = "offline" # "online or offline"
        self.client = mqtt.Client(client_id=client_id, clean_session=clean_session, userdata=None) # , protocol=MQTTv31)# , protocol=MQTTv311, transport="tcp")
        self.client.enable_logger(self.logger)
        # client.user_data_set("This is user_data for testing")
        self.client.will_set(topic=(client_id+"/available"), payload="offline", qos=2, retain=True)

        #--------  MQTT callback function -----------#
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_unsubscribe = self.on_unsubscribe
        self.client.on_log = self.on_log

        #--------- Connection -----------#
        # Blocking connection funtion
        #rc = self.client.connect(host=broker_ip, port=port, keepalive=keepalive, bind_address="")
        #self.logger.info("[Connection] rc = " +  str(rc))

        # Non-blocking connection function 
        self.client.connect_async(host=broker_ip, port=port, keepalive=keepalive, bind_address="")
        # Use in conjunction with loop_start() to connect in a non-blocking manner.
        # The connection will not complete until loop_start() is called.

        #-----   Start Mqtt Engine  -----#
        self.client.loop_start ()
        
    def add_subscriber(self, sub_req):
        '''
        Input : sub_req = [("topic1" , qos , fun_cb) , ("topic2", qos, fun_cb), ....]    
        '''
        for i in sub_req:
            #----------------  Valid check  ----------------# 
            is_valid_subreq = True
            for j in self.sub_list:
                if i[0] == j[0]: # This topic has already been subscribe
                    if i[1] != j[1]: # But Qos has change 
                        j[1] = i[1] # modified sub_qos as req asked
                    else: # Igonre sub_req because this topic has already been sub.
                        is_valid_subreq = False
            
            #----------------  Add sub_req to sub_list ------------------# 
            if is_valid_subreq:
                self.sub_list.append([i[0], i[1]])
                self.client.message_callback_add(i[0], i[2])
            # self.client.message_callback_remove(sub)
        # ---------  real subcribe send to broker ------------#
        self.logger.info("[MQTT] Add_subscriber : " + str(self.sub_list))
        self.client.subscribe(self.sub_list)
    def publish(self, topic, payload, qos, retain):
        '''
        This is a Non-blocking publish function.
        Output : 
            return : pub_rc
        Use pub_rc.is_published() to check publish has completed or not
        return None , for connection problem. In that case, user should publish msg again after connection is recovery.
        '''
        if self.available == "offline" and (not IS_PUB_WITHOUT_CONNECT): 
            return None 
        else:
            pub_rc = self.client.publish(topic, payload, qos, retain)
            if IS_PUB_LOG : 
                self.logger.info("[MQTT] publish '" + str(payload) + "' to '" + topic + "' (Q" + str(qos) + ", R" + str(int(retain))+", Mid: " + str(pub_rc[1]) + ")")
            if pub_rc[0] != mqtt.MQTT_ERR_SUCCESS : # Something wrong
                self.logger.error("[MQTT] publish "  +  mqtt.error_string(pub_rc[0]) + " (Mid: " + str(pub_rc[1])) # pub_rc=(result,mid)
            return pub_rc
    
    def publish_blocking (self, topic, payload, qos, retain, timeout = 10):
        '''
        This is a blocking function, return until CB is get , or timeout.
        Output : 
            publish result : (0 , pub_rc)
            0 : something wrong while publishing , maybe timeout
            1 : successfully publish and get CB
        '''
        if self.available == "offline" and (not IS_PUB_WITHOUT_CONNECT): 
            return (0, None ) 
        else:
            pub_rc = self.client.publish(topic, payload, qos, retain)
            if IS_PUB_LOG:
                self.logger.info("[MQTT] publish '" + str(payload) + "' to '" + topic + "' (Q" + str(qos) + ", R" + str(int(retain))+", Mid: " + str(pub_rc[1]) + ")")
            if pub_rc[0] != mqtt.MQTT_ERR_SUCCESS : # Something wrong
                self.logger.error("[MQTT] publish " +  mqtt.error_string(pub_rc[0]) + " (Mid: " + str(pub_rc[1])) # pub_rc=(result,mid)
                return (0 , pub_rc)
            
            #---------  wait for published completed --------#  (on_publish will be called first.)
            t_start = time.time()
            # pub_rc.wait_for_publish() # Wait until on_publish CB, But this will wait forever
            while pub_rc.is_published():
                if time.time() - t_start >= timeout: # Wait for all the handshake is completed 
                    self.logger.warn("[MQTT] publish TIMEOUT! Wait CB for " + str(timeout) + " sec.")
                    return (0 , pub_rc)
                time.sleep(0.01)
            if IS_PUB_LOG : 
                self.logger.info("[MQTT] publish completed in " + str(round((time.time() - t_start)*1000,3)) + " ms" + ", (Mid: " + str(pub_rc[1]) + ")" )
            return (1 , pub_rc)

    #########################
    ###    MQTT callback  ###
    #########################
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self,client, userdata, flags, rc):
        # print "[on_connect] the private user data as set in Client() or user_data_set() : " , str(userdata) 
        # print "[on_connect] response flags sent by the broker : ", flags
        self.logger.info(str(flags)) # TODO Test 
        self.logger.info("[MQTT] connect_CB: "+ mqtt.connack_string(rc))
        self.available = "online"
        client.publish(topic=(self.client_id+"/available"), payload="online", qos=2, retain=True)
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        if self.sub_list != []:
            client.subscribe(self.sub_list)
    
    def on_disconnect(self,client, userdata, rc):
        self.available = "offline"
        if rc != 0:
            self.logger.error("[MQTT] on_disconnect - Unexpected disconnection." + mqtt.connack_string(rc))
        else:
            self.logger.warning("[MQTT] on_disconnect - Successfully disconnect")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self,client, userdata, message):
        # This callback should NOT be called. 
        # User should declare self-define callback for subcribe topic.
        self.logger.info("[MQTT] on_message :  " + str(message.payload) + "(Q" + str(message.qos) + ", R" + str(message.retain) + ")")
    
    # When the message has been sent to the broker an on_publish() callback
    def on_publish(self, mosq, obj, mid): # Call after all of the handshake is completed 
        if IS_PUB_LOG: 
            self.logger.info("[MQTT]" + " Publish Complete." + "(Mid: "+ str(mid) + ")")
        # Qos_0 : this simply means that the message has left the client.
        # Qos_1 Qos_2:  this means that the appropriate handshakes have completed.
    
    # When the broker has acknowledged the subscription, an on_subscribe() callback will be generated.
    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.logger.info ("[MQTT] Subscribe AWK."+ "(Mid: "+ str(mid) + ")" )
        # The granted_qos variable is a list of integers that give the QoS level the broker has granted for each of the different subscription requests.

    # When the broker has acknowledged the unsubscribe, an on_unsubscribe() callback will be generated.
    def on_unsubscribe(self, client, userdata, mid):
        self.logger.info( "[MQTT] Unsubscribe AWK"+ "(Mid: "+ str(mid) + ")" )  

    def on_log(self,client, userdata, level, buf):
        # level == MQTT_LOG_INFO or MQTT_LOG_NOTICE or MQTT_LOG_WARNING, MQTT_LOG_ERR
        # The message itself is in buf
        # print "[on_log] : ", level, "  " , buf
        pass
