''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
from Formulatrix.Core.Protocol import FmlxController
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time

''' your yaml path '''
path_wambo_trinamic= r"../DeviceOpfuncs/wambo_trinamic.yaml"
path_sensor= r"../DeviceOpfuncs/STM32_sensor.yaml"

''' define your address'''
address = [1,3]

address_dispenser_board_0 = 1
address+=[address_dispenser_board_0]

address_aspirator_board_1 = 8
address+=[address_aspirator_board_1]


# it will return two values, the driver instance drv[0] and our address drv[1]
drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=address)

dp0 = FmlxDevice(drv[0], address[1], path_wambo_trinamic)
dp0.connect()
as1 = FmlxDevice(drv[1], address[3], path_wambo_trinamic)
as1.connect()
