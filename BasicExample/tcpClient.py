''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time
import FmlxLogger

''' your yaml path '''
path_atsam_basic= r"../DeviceOpfuncs/wambo_trinamic.yaml"

usePythonnet = False
address = 22
useSinglePrecision = True
hostName = "localhost"
hostPort = 322
log_handler = FmlxLogger.CreateRotatingFileHandler(fileName='tcpClient')
drv,address=FmlxDeviceConnector.FmlxDeviceConnector(address_list = address,driver_name = 'TCP',hostName=hostName,hostPort=hostPort,usePythonnet = usePythonnet,log_handler=log_handler)
d = FmlxDevice(drv, address, path_atsam_basic,log_handler = log_handler,usePythonnet = usePythonnet,retryCount =1,use_single_precision = useSinglePrecision)
d.connect()
