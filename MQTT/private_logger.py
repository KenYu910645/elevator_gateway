import logging 
import argparse
# logger
# Set up logger
formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
private_logger = logging.getLogger('MQTT')
private_logger.setLevel(logging.DEBUG)

#Set up args
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                    help='Enable debug info on consolo')
args = parser.parse_args()

'''
# Print out logging message on console
h_console = logging.StreamHandler()
h_console.setFormatter(formatter)
if args.verbose:
    h_console.setLevel(logging.DEBUG)
else:
    h_console.setLevel(logging.INFO)
logger.addHandler(h_console)
'''

# Record logging message at logging file
h_file = logging.FileHandler("mqtt_private.log")
h_file.setFormatter(formatter)
if args.verbose:
    h_file.setLevel(logging.DEBUG)
else:
    h_file.setLevel(logging.INFO)
private_logger.addHandler(h_file)
