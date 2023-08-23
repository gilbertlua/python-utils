import can
from queue import Queue
import threading
import argparse
from FmlxDeviceConnector import PCANGetAvaiableChannel
import time
import sys
import FmlxLogger
import logging

log_handler = FmlxLogger.CreateRotatingFileHandler('pcan-kv')
logger = logging.getLogger('pcan-kv')
logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)
# logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.DEBUG))
        

VERSION = "1.0.0"

# command line argument to config the plotter
parser = argparse.ArgumentParser(description="Formulatrix PCAN-KVaser Bridge")
parser.add_argument('-c', '--channel', help="kvaser channel", type=int)
args = parser.parse_args()
if(args.channel):
    kvaserChannel=int(args.channel)
else:
    kvaserChannel=0

avaiable_channels = PCANGetAvaiableChannel()
if(len(avaiable_channels)==0):
    raise ModuleNotFoundError('No PCAN found!')

choose = 0
for index,channel in enumerate(avaiable_channels):
    print ('%s. %s' % (index+1, channel))
    if(index>1):
        choose = int(input('Choose Your PCAN channel : ')) - 1

print('PCAN <-> KVaser Bridge ver : {0}'.format(VERSION))
print('Selected PCAN : {0}'.format(avaiable_channels[choose]))
print('Selected KVaser Channel : {0}'.format(kvaserChannel))

kvaserBus = can.interface.Bus(bustype='kvaser', channel=kvaserChannel, bitrate=1000000, accept_virtual = True, single_handle  = True)
pcanBus = can.interface.Bus(bustype='pcan', channel=avaiable_channels[choose], bitrate=1000000, accept_virtual = True, single_handle  = True)

isRunning = True

def pcanToKvaserThread():
    global isRunning,pcanBus,kvaserBus
    while(isRunning):
        receivedData = pcanBus.recv(1)
        if(not receivedData):
            continue
        logger.debug('pc->kv,ts : {0}, MsgId : {1}, dlc : {2}, data : {3}'.format(receivedData.timestamp,receivedData.arbitration_id,receivedData.dlc,list(map(int,receivedData.data))))
        kvaserBus.send(receivedData)

def kvaserToPcanThread():
    global isRunning,pcanBus,kvaserBus
    while(isRunning):
        receivedData = kvaserBus.recv(1)
        if(not receivedData):
            continue
        logger.debug('kv->pc,ts : {0}, MsgId : {1}, dlc : {2}, data : {3}'.format(receivedData.timestamp,receivedData.arbitration_id,receivedData.dlc,list(map(int,receivedData.data))))
        pcanBus.send(receivedData)

pcanToKvaserThreadInstance = threading.Thread(target=pcanToKvaserThread)
pcanToKvaserThreadInstance.daemon = True
pcanToKvaserThreadInstance.start()

kvaserToPcanThreadInstance = threading.Thread(target=kvaserToPcanThread)
kvaserToPcanThreadInstance.daemon = True
kvaserToPcanThreadInstance.start()

def uncaughtExceptionHandler(self,exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print('Uncaught Exception',exc_info=(exc_type, exc_value, exc_traceback))

while 1:
    time.sleep(1)
