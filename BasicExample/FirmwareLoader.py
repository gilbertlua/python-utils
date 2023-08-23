import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice
import FmlxDeviceConnector
from FormulatrixCorePy.FmlxBootloader import BootloaderApp,Record
from FormulatrixCorePy.FmlxController import FmlxController

''' insert your additional header/ module here '''
import FmlxLogger
import logging
import tkinter
import tkinter.filedialog
import os
root = tkinter.Tk()
root.withdraw() #use to hide tkinter window
currdir = os.getcwd()

''' your yaml path '''
path_wambo_trinamic= r"../DeviceOpfuncs/wambo_trinamic.yaml"
path_bootloader= r"../FmlxDeviceUtils/FmlxDeviceUtils/bootloader_opfuncs.yaml"

use_serial = False

# use this if we want to enable logging
# log_handler = FmlxLogger.CreateRotatingFileHandler(fileName='firmwareLoader',logLevel = logging.DEBUG,maxBytes=10000000,backupCount = 1)
log_handler = None

# must not use pythonnet!
usePythonnet = False

# define your device address!
address = int(input("please inset addr: "))

drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=[0,address],autoSelectComPort = True,usePythonnet = usePythonnet,log_handler = log_handler)

boot_ctrl = FmlxController(drv[0],retryCount = 3,log_handler = log_handler)
boot_ctrl.ReadTimeout = 1000
boot_ctrl.Connect()

if(not use_serial):
    app_ctrl = FmlxController(drv[1],retryCount = 3,log_handler = log_handler)
    app_ctrl.ReadTimeout = 1000
    app_ctrl.Connect()

ba = BootloaderApp(boot_ctrl,app_ctrl,0,address,BootloaderApp.ResetOption.Hang,BootloaderApp.McuPlatform.TexasInstrument,log_handler = log_handler)

file = tkinter.filedialog.askopenfilename(parent=root, initialdir=currdir, title='Please select update file binary')
if len(file) > 0:
    r=ba.UpgradeFirmware('','',file)
