from global_var.global_param import BROKER_IP, CLIENT_NAME , AMR_MQTT_NAME
# import paho.mqtt.client as mqtt
from MQTT.mqtt_template import MQTT_OBJ
import time 
import json
# client = mqtt.Client(client_id="test_pub", clean_session=False, userdata=None) # , protocol=MQTTv31)# , protocol=MQTTv311, transport="tcp")
# client.connect_async(host=BROKER_IP, port=1883, keepalive=10, bind_address="")
# Use in conjunction with loop_start() to connect in a non-blocking manner.
# The connection will not complete until loop_start() is called.

#-----   Start Mqtt Engine  -----#
# client.loop_start ()
mqtt_obj = MQTT_OBJ(client_id="test_pub", broker_ip=BROKER_IP, port=1883, keepalive=10, clean_session=False)
while (1):
    word=input('please input one or more word\n')
    print (word)


    
    json



    mqtt_obj.publish_blocking(topic = AMR_MQTT_NAME[0] + "/"+CLIENT_NAME+"/cmd" , payload = word, qos = 2, retain = True)
    time.sleep(0.5)
