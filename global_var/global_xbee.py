
from global_param import IS_USING_XBEE, XBEE_HOST_IP

#---- MQTT improt -----#
if IS_USING_XBEE:
    from XBEE.xbee_template import BLUE_COM
    from global_logger import logger

#########################################
###   Config of bluetooth connction   ###
#########################################
xbee_obj = BLUE_COM(logger, host = XBEE_HOST_IP , port = 1)

