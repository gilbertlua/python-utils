from __future__ import print_function

import os
import sys
import time
import logging
import fnmatch

import clr
clr.AddReference('System')
clr.AddReference('System.IO')
from System import *
from System.IO.Ports import Parity, StopBits, Handshake

sys.path.append(os.path.abspath('../Include'))
clr.AddReference('Formulatrix.Core.Protocol')
clr.AddReference('Formulatrix.Core.Protocol.Serial.Ftdi.Win')
clr.AddReference('Formulatrix.Core.Protocol.Serial.Linux')
clr.AddReference("Formulatrix.Core.Protocol.Can.KVaser.Win")
from Formulatrix.Core.Logger import NullLogger
from Formulatrix.Core.Protocol import FmlxController, FmlxPacket, BootLoader, IFmlxDriver
from Formulatrix.Core.Protocol.Serial import SerialFmlxDriver
from Formulatrix.Core.Protocol.Serial.Ftdi.Win import FtdiFmlxDriver, FtdiFmlxDriverProvider
from Formulatrix.Core.Protocol.Can.KVaser.Win import KvaserFmlxDriver
from Formulatrix.Core.Protocol.SLCan.Win import SlcanFmlxDriver, FmlxSlcanSequential
from Formulatrix.Core.Protocol.Serial.Linux import *
from Formulatrix.Core.Protocol.Can.Linux import *
from Formulatrix.Core.Protocol.TCP import TcpFmlxDriver
from Formulatrix.Core.Protocol.Spi.Linux import SpiLinux,SpiInterop
from Formulatrix.Core.Protocol.Spi2Can.Linux import Spi2CanLinux
from Formulatrix.Core.Protocol.CanSequential.KVaser.Win import KvaserSequentialFmlxDriver

from Formulatrix.Core.Logger import IFmlxLogger
from sys import platform as _platform
from FmlxDevice import FmlxDevice

def get_platform():
    platforms = {
        'linux1' : 'Linux',
        'linux2' : 'Linux',
        'darwin' : 'OS X',
        'win32' : 'Windows'
    }
    if sys.platform not in platforms:
        return sys.platform

    return platforms[sys.platform]

class ConsoleLogger(IFmlxLogger):
    __namespace__ = "MyNameSpace"
    def LogDebug(self,format,arg):
        print (String.Format(format,arg))
    def LogInfo(self,format,arg):        
        print (String.Format(format,arg))

def find_ftdi(drv_idx):
    print("Refreshing device list...")
    drv_provider = FtdiFmlxDriverProvider()
    drv_provider.RefreshDeviceList()
    drivers = list(drv_provider.GetDeviceList())
    
    if len(drivers) <= 0:
        print("No device detected!")
        return None
    
    try:
        drv = drivers[drv_idx]
        if drv_idx < 0:
            raise IndexError
    except (TypeError, IndexError) as e:
        print("Detected device{}:".format("s" if len(drivers)>1 else ""))
        for idx, drv in enumerate(drivers):
            print("{}: {}".format(idx, drv))
        print("")
        if type(e) is TypeError:
            print("Specify device using -i")
        elif type(e) is IndexError:
            print("Device with index {} not found!".format(drv_idx))
        return None
    
    print("Selected device {}: {}".format(drv_idx, drv))
    return drv

def reset(loader):
    print("Resetting...")
    loader.ResetHardware()
    return True

def not_supported_yet(action):
    print("The action [{}] is not supported yet.".format(action))
    return False

def check_file(filename):
    if filename is None:
        print("Specify which hex file to use in the [filename] argument")
        return False
    elif not os.path.isfile(filename):
        print("Cannot find {}".format(filename))
        return False
    return True

def upgrade(loader, filename):
    if check_file(filename) is False:
        return False
    print("Going to upgrade from hex file: {}".format(filename))
    
    try:
        loader.UpgradeFirmware(os.path.abspath(filename))
    except Exception as e:
        print("\n{}\n{}".format(e, e.InnerException))
        return False
    else:
        print("")
    return True

def verify(loader, filename):
    if check_file(filename) is False:
        return False
    print("Going to verify against hex file: {}".format(filename))
    
    try:
        loader.VerifyFirmware(os.path.abspath(filename))
    except Exception as e:
        print("\n{}\n{}".format(e, e.InnerException))
        return False
    else:
        print("")
    return True

class PrintProgress():
    last_action = None
    PROGRESS_BAR_LENGTH = 68
    action_str = {
        BootLoader.Action.Reset: "Resetting hardware...",
        BootLoader.Action.GenerateRecords: "Parsing firmware file...",
        BootLoader.Action.EraseFlash: "Erasing flash memory...",
        BootLoader.Action.ProgramFlash: "Programming firmware to flash...",
        BootLoader.Action.VerifyFlash: "Verifying firmware on flash...",
        BootLoader.Action.InvokeApp: "Invoking firmware application...",
        BootLoader.Action.VerifyApp: "Succeeded invoking firmware application."
    }
    
    @staticmethod
    def handler(obj, value):
        if value.Action != PrintProgress.last_action:
            print("")
            print(PrintProgress.action_str[value.Action])
            PrintProgress.last_action = value.Action
        pct = value.Percentage
        
        chars_done = int(pct*PrintProgress.PROGRESS_BAR_LENGTH/100.)
        chars_remain = PrintProgress.PROGRESS_BAR_LENGTH - chars_done
        progress_bar = "#"*chars_done + "."*chars_remain
        
        print("{:3d}% [{}]".format(pct, progress_bar), end='\r')

drvBootloader = None
drvUserApp = None

def main(args):
    # drv = None
    global drvBootloader
    global drvUserApp
    from sys import platform as _platform
    mcu = None
    if(args.MCU == None):
        raise Exception('You must input the MCU argument!')
    if(args.MCU == 'STM32F4'):
        mcu = BootLoader.MCUPlatform.STM32F4
        filename, file_extension = os.path.splitext(args.filename)
        if(file_extension!='.hex'):
            raise Exception('Invalid hex file name extention for STM32F4, must be .hex! current extention: {0}'.format(file_extension))
    elif(args.MCU == 'TI'):
        mcu = BootLoader.MCUPlatform.TexasInstrument
    else:
        raise Exception('Invalid MCU platform! : {0}'.format(args.MCU))
    # Windows 64-bit
    useSingleController=False
    if args.driver == 'ftdi':
        drv_idx = int(args.port)
        print("Connecting using FtdiFmlxDriver to index {} ...".format(drv_idx))
        drvBootloader = find_ftdi(drv_idx)
        drvUserApp=drvBootloader        
        drvBootloader.ReadTimeout = 300
        drvBootloader.FlowControl='none'
        useSingleController=True
    elif args.driver == 'serial':
        port = args.port
        baud = args.baud or 115200
        cts = args.cts
        print("Connecting using SerialFmlxDriver to {} ...".format(args.port))
        print("Parameters: {} bps, {} flow control".format(baud, "with" if cts else "no"))
        
        drvBootloader = SerialFmlxDriver('', port, baud, 8, Enum.Parse(Parity,"None"), StopBits.One, Handshake.RequestToSend if cts else Enum.Parse(Handshake,"None"))
        drvBootloader.ReadTimeout = 300
        useSingleController=True
    elif args.driver == 'termios':
        port = args.port
        baud = 115200
        cts = False
        print("Connecting using TermiosFmlxDriver to {} ...".format(args.port))
        print("Using default parameters: {} bps, {} flow control".format(baud, "with" if cts else "no"))
        drvBootloader = TermiosFmlxDriver.Overloads[String, BaudRate, ControlFlow, Boolean](port, BaudRate.B115200, Enum.Parse(ControlFLow,"None"), False)
        drvBootloader.ReadTimeout = 300
        drvUserApp=drvBootloader                
        useSingleController=True
    elif args.driver == 'KVaser':
        drvBootloader =KvaserFmlxDriver(0,0)
        drvBootloader.ReadTimeout = 300
        drvUserApp = KvaserFmlxDriver(int(args.Useraddress),0)
        drvUserApp.ReadTimeout = 300
    elif args.driver == 'KvaserCanSequential':
        drvBootloader =KvaserSequentialFmlxDriver(0,0)
        drvBootloader.ReadTimeout = 300
        drvUserApp = KvaserSequentialFmlxDriver(int(args.Useraddress),0)
        drvUserApp.ReadTimeout = 300
    elif args.driver == 'FVaserCanSequential':
        port = args.port
        if _platform.startswith('win') or _platform.startswith('cygwin'):
            drvBootloader = FmlxSlcanSequential(args.address,port)
            drvUserApp = FmlxSlcanSequential(args.Useraddress,port)
            drvBootloader.ReadTimeout = 300
            drvUserApp.ReadTimeout = 300
        else:
            can_type = {
                '1' : 'SLCan',
                '2' : 'KVaser',
                '3' : 'VCan',
            }
            print ('Choose your CAN Channel:')
            for k, v in sorted(can_type.items()):
                print ('%s. %s' % (k,v))
            flavor=raw_input(': ')
            if(flavor == '1'):
                drvBootloader = LinuxCanSequentialFmlxDriver(args.address,0,2,NullLogger())
                drvUserApp = LinuxCanSequentialFmlxDriver(args.Useraddress,0,2,NullLogger())
            if(flavor == '2'):
                drvBootloader = LinuxCanSequentialFmlxDriver(args.address,0,1,NullLogger())
                drvUserApp = LinuxCanSequentialFmlxDriver(args.Useraddress,0,1,NullLogger())
            if(flavor == '3'):
                drvBootloader = LinuxCanSequentialFmlxDriver(args.address,0,0,NullLogger())
                drvUserApp = LinuxCanSequentialFmlxDriver(args.Useraddress,0,0,NullLogger())
            drvBootloader.ReadTimeout = 300
            drvUserApp.ReadTimeout = 300
    elif args.driver == 'FVaser':
        port = args.port
        if _platform.startswith('win') or _platform.startswith('cygwin'):
            # print ('a1',args.address)
            # print ('a2',args.Useraddress)
            drvBootloader = SlcanFmlxDriver(args.address,port)
            drvUserApp = SlcanFmlxDriver(args.Useraddress,port)
            # print ('fvaser boot')
            drvBootloader.ReadTimeout = 300
            drvUserApp.ReadTimeout = 300
        else :
            can_type = {
                '1' : 'SLCan',
                '2' : 'KVaser',
                '3' : 'VCan',
            }
            print ('Choose your CAN Channel:')
            for k, v in sorted(can_type.items()):
                print ('%s. %s' % (k,v))
            flavor=raw_input(': ')
            if(flavor == '1'):
                drvBootloader = LinuxCanFmlxDriver(args.address,0,2,NullLogger())
                drvUserApp = LinuxCanFmlxDriver(args.Useraddress,0,2,NullLogger())
            if(flavor == '2'):
                drvBootloader = LinuxCanFmlxDriver(args.address,0,1,NullLogger())
                drvUserApp = LinuxCanFmlxDriver(args.Useraddress,0,1,NullLogger())
            if(flavor == '3'):
                drvBootloader = LinuxCanFmlxDriver(args.address,0,0,NullLogger())
                drvUserApp = LinuxCanFmlxDriver(args.Useraddress,0,0,NullLogger())
            drvBootloader.ReadTimeout = 300
            drvUserApp.ReadTimeout = 300
    elif args.driver == 'tcp':
        drvUserApp = TcpFmlxDriver(args.Ipaddress,args.Ipport)
        # drvBootloader.ReadTimeout = 300
        drvBootloader = drvUserApp
        useSingleController=True
        # drvUserApp.ReadTimeout = 300
    elif args.driver == 'SPILinux':
        drvBootloader = SpiLinux(16000000)
        drvBootloader.ReadTimeout = 300
        useSingleController=True
        if(args.latchPin != None):
            _latchPinFd=SpiInterop.GpioInit(args.latchPin)
            SpiInterop.GpioSetDir(_latchPinFd, args.latchPin, 1)
            SpiInterop.GpioWrite(_latchPinFd,1)     
    elif args.driver == 'SPI2CANLinux':
        drvBootloader = Spi2CanLinux(0)
        drvBootloader.ReadTimeout = 300
        drvUserApp = Spi2CanLinux(int(args.Useraddress))
        drvUserApp.ReadTimeout = 300

    if(useSingleController == False):
        if drvBootloader is None or drvUserApp  is None:
            print("Failed initializing FmlxDriver")
            exit(0)
    fmlxdevice = FmlxDevice(drvUserApp, args.Useraddress, 'generic_opfuncs.yaml')
    for i in range(3):
        try:
            fmlxdevice.get_app_name()
        except:
            pass
    use_hang = args.hang
    print("Support hardware reset: {}".format("yes" if drvBootloader.CanResetFirmware else "no"))
    if use_hang:
        reset_option = BootLoader.ResetOption.Hang
        print("Configured reset option to use hang_firmware command")
    else:
        reset_option = BootLoader.ResetOption.Default
        print("Configured reset option to use default behavior")

    print ('a1',args.address)
    print ('a2',args.Useraddress)
    busIdBootLoader = UInt16(args.address)
    busIdUserApp = UInt16(args.Useraddress)
    ctl = FmlxController(drvBootloader)
    if useSingleController:
        #print("single controller\n\n\n\n")
        ctlUserApp = ctl
    else:
        #print("Double controller\n\n\n\n")   
        ctlUserApp = FmlxController(drvUserApp)

    print("Initializing loader,...")
    loader = BootLoader(busIdBootLoader,busIdUserApp, ctl,ctlUserApp, NullLogger(), reset_option,mcu)
    ctl.Connect()
    #ctl.LoggingDisabled=False
    #ctl.Log=ConsoleLogger()

    if (drvBootloader != drvUserApp):       
        ctlUserApp.Connect()
    
    loader.Open()
    loader.ProgressUpdated += PrintProgress.handler
    
    action = args.action
    result = False
    
    if action == 'reset':
        result = reset(loader)
    elif action == 'upgrade':
        result = upgrade(loader, args.filename)
    elif action == 'verify':
        result = verify(loader, args.filename)
    else:
        result = True  # for interactive/development mode
    
    loader.Close()
    ctl.Disconnect()
    
    if result is True:
        print("")
        print("Done.")
    else:
        exit(0)

def get_serial_port():
    import serial.tools.list_ports   # import serial module
    comPorts = list(serial.tools.list_ports.comports())    # get list of all devices connected through serial port
    if len(comPorts)==0:
        print ('No COM port found!')
        return
    else:
        for i in range(len(comPorts)):
            print (i+1,'.',comPorts[i]) 
        if(sys.version_info< (3,0)):
            choose=raw_input(': ')
        else:
            choose=input(': ')
        serial_port_string = str(comPorts[int(choose)-1])
        serial_port=''
        for i in serial_port_string:
            if(i==' '):
                break
            serial_port+=i
    return serial_port

def get_driver_FTDI():
    from Formulatrix.Core.Protocol.Serial.Ftdi.Win import FtdiFmlxDriver, FtdiFmlxDriverProvider
    drv_provider = FtdiFmlxDriverProvider()
    drv_provider.RefreshDeviceList()
    ftdi_list = drv_provider.GetDeviceList()
    for idx,val in enumerate(ftdi_list):
        print (idx+1,val)
    choose = int(input('Choose FTDI device : '))-1
    ftdi_list[choose].FlowControl = 'none'
    ftdi_list[choose].ReadTimeout = 500
    return choose

def search_hex():
    i=0
    filelist=[]
    listOfFiles = os.listdir('.')  
    pattern = "*.hex"  
    for entry in listOfFiles:  
        if fnmatch.fnmatch(entry, pattern):
                # i+=1
                # print i,'.',entry
                if('bootloader' in entry):
                    pass
                else:
                    filelist+=[entry]
    pattern = "*.i00"  
    for entry in listOfFiles:  
        if fnmatch.fnmatch(entry, pattern):
                # i+=1
                # print i,'.',entry
                if('bootloader' in entry):
                    pass
                else:
                    filelist+=[entry]
    return filelist

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Formulatrix command-line firmware loader")
    
    # Positional
    parser.add_argument('action', help="Specify the action to perform",
                        choices=['reset', 'upgrade', 'verify'], nargs='?')
    parser.add_argument('filename', help="COFF/.i00 hex file to use", nargs='?')
    
    # Options
    parser.add_argument('-d', '--driver', help="IFmlxDriver type to use",
                        choices=['ftdi', 'serial', 'termios','KVaser','FVaser','tcp','SPILinux','SPI2CANLinux'], required=False)
    parser.add_argument('-p', '--port', help="Port used by driver: driver index for [ftdi], COM* or /dev/tty* for [serial,termios]")
    parser.add_argument('-f', '--hang', help="Force use software reset (hang_firmware)",
                        action='store_true')
    parser.add_argument('-b', '--baud', help="Baud rate", type=int)
    parser.add_argument('-c', '--cts', help="Use CTS/RTS flow control", action='store_true')
    parser.add_argument('-a', '--address', help="bootloader app FmlxProtocol address (busId)", type=int)
    parser.add_argument('-u', '--Useraddress', help="User app FmlxProtocol address (busId)", type=int)
    parser.add_argument('-ip', '--Ipaddress', help="Target device ip address", type=str)
    parser.add_argument('-pr', '--Ipport', help="Target device IP port", type=int)
    parser.add_argument('-m', '--MCU', help="Target Device MCU platform", choices=['TI', 'STM32F4'], nargs='?')
    parser.add_argument('-l', '--latchPin', help="Use latch power, only firmware with power management included", type=int, nargs='?')
    args = parser.parse_args()

    if args.driver is None:
        class bootArgs:
            driver=''
            Useraddress=1
            address=0
            port=''
            baud=4000000
            action='upgrade'
            filename=''
            hang=True
            
        args = bootArgs()
        drivers = {
            '1' : 'FVaser/CAN Linux',
            '2' : 'KVaser',
            '3'	: 'ftdi',
            '4' : 'termios',
            '5' : 'tcp',
            '6' : 'SPILinux',
            '7' : 'SPI2CANLinux',
            '8' : 'KvaserCanSequential',
            '9' : 'FVaserCanSequential',
            '10' : 'serial'
        }
        mcu = {
            '1' : 'TI',
            '2' : 'STM32F4',
        }
        print ('Choose your Driver:')
        for k, v in sorted(drivers.items()):
            print ('%s. %s' % (k,v))
        if(sys.version_info< (3,0)):
            flavor=raw_input(': ')
        else:
            flavor=input(': ')
        args.driver = drivers[flavor]
        if drivers[flavor] == 'FVaser/CAN Linux':
            platform = get_platform()
            if platform == 'Windows':
                args.port = get_serial_port()
                args.driver='FVaser'
        elif drivers[flavor] == 'FVaserCanSequential':
            platform = get_platform()
            if platform == 'Windows':
                args.port = get_serial_port()
        elif drivers[flavor] == 'ftdi':
            args.port = get_driver_FTDI()
            args.baud=115200
        elif drivers[flavor] == 'serial':
            args.driver = 'serial'
            args.port = get_serial_port()
            args.baud=115200
            args.cts = True
        print ('Your Target Address:')
        if(sys.version_info< (3,0)):
            args.Useraddress=raw_input(': ')
        else:
            args.Useraddress=input(': ')
        print ('Choose Your MCU Platform:')
        for k, v in sorted(mcu.items()):
            print ('%s. %s' % (k,v))
        if(sys.version_info< (3,0)):
            flavor=raw_input(': ')
        else:
            flavor=input(': ')
        args.MCU=mcu[flavor]
        print ('Choose Your Hex File:')
        hex_file_list=FmlxDevice.getPath()
        args.filename = hex_file_list
        args.latchPin = None
        if(args.driver == 'SPILinux'):
            print('use power latc(y/n)?')
            if(sys.version_info< (3,0)):
                latch=raw_input(': ')
            else:
                latch=input(': ')
            if(latch == 'y' or latch == 'Y'):
                if(sys.version_info< (3,0)):
                    _latchPinNum=int(raw_input('latch pin number : '))
                else:
                    _latchPinNum=int(input('latch pin number : '))
                args.latchPin=_latchPinNum
             
    main(args)
