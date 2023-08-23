''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
# from Formulatrix.Core.Protocol import FmlxController
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time
# import numpy as np
# import threading
# import signal
# import fopleyMotor
# import fopleyUtilities as fu 

''' your yaml path '''
path_wambo_trinamic= r"../DeviceOpfuncs/wambo_trinamic.yaml"

# it will return two values, the driver instance drv and our address addr

# choose what you need
drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle()


d = FmlxDevice(drv, address, path_wambo_trinamic)
d.connect()
# d is our fmlxDevice instance
# after this you can use all the firmware yamls or APIs by typing d.xxx, for example
# d.get_app_name()

def maju_mundur():
    print('move to pos 1000')
    motor_pos_now = d.get_motor_pos(0)['curr_pos']
    if(motor_pos_now!=1000):
        d.move_motor_abs(0,1000,2000,12000,65000)
        wait_move()
        print('move done, now move to pos 0')
    d.move_motor_abs(0,0,2000,12000,65000)
    wait_move()
    print('movement done')

move_done = 0

def wait_move():
    global move_done
    while(move_done==0):
        time.sleep(0.001)
    move_done = 0

def handle_motor_move_done(motor_id,status,position):
    global move_done
    print('motor id:{0} status : {1} position : {2}'.format(motor_id,status,position))
    move_done = 1
d.motor_move_done+=handle_motor_move_done