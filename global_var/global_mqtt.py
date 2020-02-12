from global_param import IS_USING_MQTT, BROKER_IP, CLIENT_NAME
#---- MQTT improt -----#
if IS_USING_MQTT:
    from MQTT.mqtt_template import MQTT_OBJ
    from global_logger import logger

    # ------  Connection ------ #
    mqtt_obj = MQTT_OBJ(client_id=CLIENT_NAME, broker_ip=BROKER_IP, port=1883, keepalive=10, clean_session=False, logger = logger)
    # Wait for connection Accpeted by broker (Optional) 
    #while mqtt_obj.available != "online":
    #    time.sleep(0.1)
