''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
import time
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
from Formulatrix.Core.Protocol import FmlxController
import FmlxDeviceConnector
''' insert your additional header/ module here '''
''' for example numpy : '''
from FmlxWireshark import CFmlxPacketSniffer
# import signal

''' your yaml path '''
# path_trinamic= r"../DeviceOpfuncs/mini_wambo.yaml"
path_trinamic= r"../DeviceOpfuncs/trinamic.yaml"

def selection_menu(shown_text=''):
    if(sys.version_info[0] < 3):
        return raw_input(shown_text)
    else:
        return input(shown_text)  


address_list = []
master_driver_list = []
slave_driver_list = []
drivers = {
    '1' : 'FVaser',
    '2' : 'KVaser',
    '3'	: 'FTDI',
    '4' : 'SerialPort',
    '5' : 'KvaserCanSequential',
    '6' : 'FVaserCanSequential'
}
for k, v in sorted(drivers.items()):
    print ('%s. %s' % (k,v))
choose = selection_menu('select your communication method : ')    
driver_name = drivers[choose]
if(driver_name == 'FVaser' or driver_name=='KVaser' or driver_name == 'KvaserCanSequential' or driver_name=='FVaserCanSequential'):
    print('Insert your device address')
    address = int(selection_menu())
    address_list += [address,address+0x80]
    device_count = 1
    print('Select your yaml path')
    yaml_path_list = [FmlxDevice.getPath(1,'your yaml path')]
    print('your yaml path : {0}'.format(yaml_path_list[0]))
    print('Insert your device name list')  
    device_name_list = [str(selection_menu())]

    drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=address_list,driver_name=driver_name)    

    log_file_path = None
    for d in drv:
        d.Connect()
    slave_driver_list += [drv[0]]
    master_driver_list += [drv[1]]
    
elif(driver_name == 'FTDI' or driver_name=='SerialPort'):
    print('Insert your device addresses')
    addresses = int(selection_menu(': '))
    address_list=[addresses,addresses+0x80]
    yaml_path_list = [FmlxDevice.getPath(1,'your yaml path')]
    print('your yaml path : {0}'.format(yaml_path_list[0]))
    print('Insert your device name list')
    print('for example : wambo,ioexpander,MTI')  
    device_name_list = selection_menu(': ').split(',')
    drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=address_list,driver_name=driver_name)    
    for d in drv:
        d.Connect()
    log_file_path = None

    master_driver_list += [drv[0]]
    slave_driver_list += [drv[1]] 
    device_count = 1      

useSinglePrecision = selection_menu('use single precision?(y/n):') == 'y'

print(device_name_list,slave_driver_list,master_driver_list,yaml_path_list)
m = CFmlxPacketSniffer(device_count,slave_driver_list,master_driver_list,yaml_path_list,device_name_list,useSinglePrecision,log_file_path)
while 1:
    m.Execute()
    time.sleep(0.001)
    
