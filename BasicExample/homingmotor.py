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

def get_enc():
    try:
        while True:
            f = d.get_encoder_position(0)
            g = d.get_motor_pos(0)['curr_pos']
            print("encoder position:",f," \tmotor position:",g)
            time.sleep(0.4)    
    except KeyboardInterrupt:
        print("done")
