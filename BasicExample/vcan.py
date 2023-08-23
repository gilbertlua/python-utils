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


''' your yaml path '''
path_wamic= r"../DeviceOpfuncs/vcan.yaml"

# choose what you need
usePythonnet = True
address = 22
# drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle(driver_name='VCAN Linux',address=address,autoSelectComPort = True,usePythonnet = usePythonnet)
drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle() #driver_name='VCAN Sequential Linux',address=address,autoSelectComPort = True,usePythonnet = usePythonnet)

# drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle(driver_name='KvaserCanSequential',address=address,autoSelectComPort = True,usePythonnet = usePythonnet)
# d = FmlxDevice(drv, address, path_atsam_basic,usePythonnet = usePythonnet,retryCount =1)
d = FmlxDevice(drv, address, path_wamic, use_single_precision = True, usePythonnet = usePythonnet, retryCount =1)
d.connect()