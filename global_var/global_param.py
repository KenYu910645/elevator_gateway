import os 
import yaml
from global_var.global_logger import logger
from pprint import pprint, pformat

# Load parameters
f = open(os.path.join(os.path.dirname(__file__), "../param.yaml") ,'r')
params_raw = f.read()
f.close()
param_dict = yaml.load(params_raw)

# Load parameters
table = param_dict['table']
AMR_URI = param_dict['AMR_URI']
AMR_MQTT_NAME = param_dict['AMR_MQTT_NAME']
CLIENT_NAME = param_dict['CLIENT_NAME']
BROKER_IP = param_dict['BROKER_IP']
NOTIFY_MAX_RETRY_TIME = param_dict['NOTIFY_MAX_RETRY_TIME']
REC_TIMEOUT = param_dict['REC_TIMEOUT'] 
IS_VERBOSE = param_dict['IS_VERBOSE']
IS_SIMULATION = param_dict['IS_SIMULATION']
DOOR_OPEN_LIMIT_TIME = param_dict['DOOR_OPEN_LIMIT_TIME'] 
WAIT_REACH_LIMIT_TIME = param_dict['WAIT_REACH_LIMIT_TIME'] 
SLIENCE_MIN_COUNTER = param_dict['SLIENCE_MIN_COUNTER']
FLOOR_LED_CONFIRMATION_MAX_TIME = param_dict['FLOOR_LED_CONFIRMATION_MAX_TIME']
FLOOR_LED_CONFIRMATION_MIN_TIME = param_dict['FLOOR_LED_CONFIRMATION_MIN_TIME']
WAIT_DOOR_LIMIT = param_dict['WAIT_DOOR_LIMIT']
is_using_rss = param_dict['is_using_rss']
IS_USING_MQTT = param_dict['IS_USING_MQTT']
IS_USING_HTTP = param_dict['IS_USING_HTTP']
CORP_ID = param_dict['CORP_ID']
CORP_SECRET = param_dict['CORP_SECRET']
AGENT_ID = param_dict['AGENT_ID']
ENABLE_VERIFY_DOOR_STATUS = param_dict['ENABLE_VERIFY_DOOR_STATUS']
CLOSE_EYE_WAIT_DOOR_SEC = param_dict['CLOSE_EYE_WAIT_DOOR_SEC']
IS_USING_XBEE = param_dict['IS_USING_XBEE']
XBEE_HOST_IP = param_dict['XBEE_HOST_IP']

# Print out parameters
logger.info("[param_loader] table = " + pformat(table))
logger.info("[param_loader] AMR_URI = " + str(AMR_URI))
logger.info("[param_loader] AMR_MQTT_NAME = " + str(AMR_MQTT_NAME))
logger.info("[param_loader] AMR_MQTT_NAME = " + str(CLIENT_NAME))
logger.info("[param_loader] BROKER_IP = " + str(BROKER_IP))
logger.info("[param_loader] NOTIFY_MAX_RETRY_TIME = " + str(NOTIFY_MAX_RETRY_TIME))
logger.info("[param_loader] REC_TIMEOUT = " + str(REC_TIMEOUT))
logger.info("[param_loader] IS_VERBOSE = " + str(IS_VERBOSE))
logger.info("[param_loader] IS_SIMULATION = " + str(IS_SIMULATION))
logger.info("[param_loader] DOOR_OPEN_LIMIT_TIME = " + str(DOOR_OPEN_LIMIT_TIME))
logger.info("[param_loader] WAIT_REACH_LIMIT_TIME = " + str(WAIT_REACH_LIMIT_TIME))
logger.info("[param_loader] SLIENCE_MIN_COUNTER = " + str(SLIENCE_MIN_COUNTER))
logger.info("[param_loader] FLOOR_LED_CONFIRMATION_MAX_TIME = " + str(FLOOR_LED_CONFIRMATION_MAX_TIME))
logger.info("[param_loader] FLOOR_LED_CONFIRMATION_MIN_TIME = " + str(FLOOR_LED_CONFIRMATION_MIN_TIME))
logger.info("[param_loader] WAIT_DOOR_LIMIT = " + str(WAIT_DOOR_LIMIT))
logger.info("[param_loader] is_using_rss = " + str(is_using_rss))
logger.info("[param_loader] IS_USING_MQTT = " + str(IS_USING_MQTT))
logger.info("[param_loader] IS_USING_HTTP = " + str(IS_USING_HTTP))
logger.info("[param_loader] IS_USING_XBEE = " + str(IS_USING_XBEE))
logger.info("[param_loader] CORP_ID = " + str(CORP_ID))
logger.info("[param_loader] CORP_SECRET = " + str(CORP_SECRET))
logger.info("[param_loader] AGENT_ID = " + str(AGENT_ID))
logger.info("[param_loader] ENABLE_VERIFY_DOOR_STATUS = " + str(ENABLE_VERIFY_DOOR_STATUS))
logger.info("[param_loader] CLOSE_EYE_WAIT_DOOR_SEC = " + str(CLOSE_EYE_WAIT_DOOR_SEC))
logger.info("[param_loader] XBEE_HOST_IP = " + str(XBEE_HOST_IP))
