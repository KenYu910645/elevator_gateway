from global_var.global_param import BROKER_IP
from MQTT.mqtt_template import MQTT_OBJ
import time 

def ev_sim_reply_CB(client, userdata, message): # simulation CB
    print(message.payload)

print (BROKER_IP)
mqtt_obj = MQTT_OBJ(client_id="test_sub", broker_ip=BROKER_IP, port=1883, keepalive=10, clean_session=False)
mqtt_obj.add_subscriber([("/simu_IPC/reply",2,ev_sim_reply_CB)])
#mqtt_obj.publish_blocking(topic = "/simu_IPC/reply" , payload = "123", qos = 2, retain = True)
while (1):
    time.sleep(0.5)