import sys
import os
sys.path.append('../Include')
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
from Formulatrix.Core.Protocol import FmlxController
import FmlxDeviceConnector


''' insert your additional header/ module here '''
''' for example numpy : '''
# import numpy as np
# import threading
import time
# import signal
import fopleyMotor
import fopleyUtilities as fu 


''' your yaml path '''
path= 'generic_opfuncs.yaml'

start_address = int(input('Start Address Search:'))
end_address = int(input('End Address Search:'))

if( (end_address - start_address) <= 0):
    print('Invalid start and end address')
    input("Press Enter to continue...")
    quit()
if( (end_address - start_address) > 63):
    print('Maximum 64 address')
    input("Press Enter to continue...")
    quit()

addresses = list(range(end_address+1))[start_address:] # address 0 is not used, because it's bootloader

# it will return two values, the driver instance drv[0] and our address drv[1]
drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=addresses)

d=[]
for i,address in enumerate(addresses):
    drv[i].ReadTimeout = 20
    d += [FmlxDevice(drv[i], address, path)]
    # connect it, then it is ready to use.
    d[i].connect()
    try:
        print('address {0} is connected : {1}'.format(address,d[i].get_app_name()))
    except:
        print('address {0} is diconnected'.format(address))

input("Press Enter to continue...")