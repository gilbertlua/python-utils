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
import yaml2gui # --> yaml2gui module must be imported
import FmlxLogger

''' your yaml path '''
path_wambo_trinamic= r"../DeviceOpfuncs/wambo_trinamic.yaml" #--> change it to your device yaml

# it will return two values, the driver instance drv and our address addr

# log_handler = FmlxLogger.CreateRotatingFileHandler('yaml2gui')
log_handler = None
# choose what you need
usePythonnet = True
autoSelectComPort = True
use_single_precision = False
driver_name = 'PCANSequential'
address = [15]
drv=FmlxDeviceConnector.FmlxDeviceConnector(driver_name = driver_name,address_list=address,usePythonnet=usePythonnet,autoSelectComPort = autoSelectComPort,log_handler = log_handler)
# drv=FmlxDeviceConnector.FmlxDeviceConnector(driver_name = 'KvaserCanSequential',address_list=address,usePythonnet=usePythonnet,autoSelectComPort = autoSelectComPort,log_handler = log_handler)
# drv=FmlxDeviceConnector.FmlxDeviceConnector(driver_name = 'KVaser',address_list=address,usePythonnet=usePythonnet,autoSelectComPort = autoSelectComPort,log_handler = log_handler)

d = FmlxDevice(drv[0], address[0], path_wambo_trinamic,use_single_precision = use_single_precision,usePythonnet=usePythonnet,log_handler = log_handler)
d.connect()
list_devices = [d]

def moveMotorAbsFunction(id,pos,vel,acc,jrk):
    print(f'{d.move_motor_abs(id,pos,vel,acc,jrk)}')

def getAppVersionFunction():
    print(f'APPNAME : {d.get_app_name()},VERSION : {d.get_version()}')

gui=yaml2gui.CYaml2Gui(list_devices,'Yaml2GUI example')
gui.add_button('moveMotorAbs',moveMotorAbsFunction)
gui.add_button('Get App and Version',getAppVersionFunction)
gui.add_button('hoho haha',getAppVersionFunction)
gui.set_user_app_menu(0,0)
gui.set_user_app_menu(1,1)