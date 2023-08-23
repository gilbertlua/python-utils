from __future__ import print_function
from logging import log, raiseExceptions
import logging
import sys
import os
from subprocess import call
import FmlxLogger

# Use Versioning from now
__version__ = '1.0.0'


try:
    # logger.debug('Try to import clr or pythonnet')
    import clr
    sys.path.append(r"../Include")
    sys.path.append(r"../FmlxDeviceUtils")
    clr.AddReference("Formulatrix.Core.Protocol")
    clr.AddReference("Formulatrix.Core.Logger")
    from Formulatrix.Core.Protocol import FmlxController, IFmlxDriver, FmlxTimeoutException
    from Formulatrix.Core.Logger import IFmlxLogger
    from FmlxDevice import FmlxDevice
    isPythonnetImported = True
    import NetLogger
    # logger.info('Pythonnet Import Success')
except ImportError:
    # use python core if the pythonnet is not installed
    # logger.info('No pythonnet installed, use Python Core instead')
    isPythonnetImported = False
except ModuleNotFoundError:
    # use python core if the pythonnet is not installed
    # logger.info('No pythonnet installed, use Python Core instead')
    isPythonnetImported = False

def FmlxDeviceConnector(driver_name=None,address_list=None,serialComPort=None,hostName=None,hostPort=None,canFdUseBRS = False,autoSelectComPort = False,usePythonnet = True,usingOldCanSequential = False,log_handler = None):
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel = logging.CRITICAL))
    if(log_handler):
        logger.addHandler(log_handler)
    logger.info('FmlxDeviceConnector version : {0}'.format(__version__))

    if(isPythonnetImported):
        logger.info('Pythonnet Succesfully Imported')
    else:
        logger.info('Pythonnet import Fail!')
        usePythonnet = False

    if(not usePythonnet and sys.version_info[0] < 3):
        if(not isPythonnetImported):
            raise NotImplementedError('CorePython is Not yet Implemented on python2!, Please use python3 or install Pythonnet first')
        else:
            usePythonnet = True
    logger.info('OS : {0}'.format(get_platform()))
    logger.info('Python Version : {0}'.format(sys.version))

    if(driver_name==None):
        platform = get_platform()
        if platform == 'Linux' or platform == 'linux':
            drivers = {
                '1' : 'SLCAN Linux',
                '2' : 'KVASER Linux',
                '3' : 'VCAN Linux',
                '4' : 'SPI Linux',
                '5' : 'Serial Linux',
                '6' : 'SPI2CAN',
                '7' : 'VCAN Sequential Linux'
            }
        elif platform == 'Windows':
            drivers = {
                '1' : 'FVaser',
                '2' : 'KVaser',
                '3' : 'FTDI',
                '4' : 'TCP',
                '5' : 'SerialPort',
                '6' : 'BleDevice',
                '7' : 'KVCanBridge',
                '8' : 'PCAN',
                '9' : 'PCANFD',
                '10' : 'KvaserCanSequential',
                '11' : 'FVaserCanSequential',
                '12' : 'PCANFDSequential'
            }
        else:
            logging.error('%s is currently not supported' % platform)
            raise NotImplementedError('%s is currently not supported' % platform)
        
        driver_name=CommunicationTypeMenu()
        
    if(address_list == None):
        address_list = int(input('Input your address : '))
    elif(type(address_list) == int):
        address_list = address_list
    elif(type(address_list) == list):
        address_list = address_list
    else:
        logger.error('Invalid address_list types : {0}'.format(type(address_list)))
        raise TypeError('Invalid address_list types : {0}'.format(type(address_list)))
    
    logger.info('selected driver : {0} , address(es) : {1} , is using pythonnet : {2}'.format(driver_name,address_list,usePythonnet))
    
    if driver_name == 'FVaser':
        if(serialComPort==None):
            serial_port=get_serial_port(autoSelectComPort,logger=logger)
        else:
            serial_port=serialComPort
        
        if(usePythonnet):
            clr.AddReference("Formulatrix.Core.Protocol.SLCan.Win")
            from Formulatrix.Core.Protocol.SLCan.Win import SlcanFmlxDriver

        if(type(address_list) == int):
            if(usePythonnet):
                return SlcanFmlxDriver(address_list,serial_port),address_list
            else:
                from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
                return SlcanFmlxDriver(address_list,serial_port),address_list
        else:
            drv=[]
            for addr in address_list:
                if(usePythonnet):
                    drv+=[SlcanFmlxDriver(addr,serial_port)]
                else:
                    from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
                    drv+=[SlcanFmlxDriver(addr,serial_port)]
            return drv
    
    elif driver_name == 'KVaser':
        if(usePythonnet):
            clr.AddReference("Formulatrix.Core.Protocol.Can.KVaser.Win")
            from Formulatrix.Core.Protocol.Can.KVaser.Win import KvaserFmlxDriver   
            from Formulatrix.Core.Protocol.Can.KVaser.Win import CanBusBitRate
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanFmlxDriver
        if(type(address_list) == int):
            if(usePythonnet):
                return KvaserFmlxDriver.Overloads[int, int, CanBusBitRate, IFmlxLogger](address_list,0,CanBusBitRate.Bitrate_1M ,NetLogger.Pythonlogger('KVaser',log_handler=log_handler)),address_list
            else:
                from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
                return CanFmlxDriver(address_list,bustype = 'kvaser'),address_list
        else:
            drv=[]
            for i in address_list:
                if(usePythonnet):
                    drv+=[KvaserFmlxDriver.Overloads[int, int, CanBusBitRate, IFmlxLogger](i,0,CanBusBitRate.Bitrate_1M ,NetLogger.Pythonlogger('KVaser',log_handler=log_handler))]
                else:
                    drv+=[CanFmlxDriver(address = i,bustype = 'kvaser')]
            return drv

    elif driver_name == 'FTDI':
        if(type(address_list)!=int):
            logger.error('FTDI must use single address! address_list types : {0}'.format(type(address_list)))
            raise TypeError('FTDI must use single address! address_list types : {0}'.format(type(address_list)))
        #for address in address_list:
        #    print('for address:{0}'.format(address))
        #    drv+=[get_driver_FTDI()]
        drv=get_driver_FTDI(),address_list
        return drv

    elif driver_name == 'TCP':
        if(type(address_list)!=int):
            logger.error('TCP does not support multiple address! address_list types : {0}'.format(type(address_list)))
            raise TypeError('TCP does not support multiple address! address_list types : {0}'.format(type(address_list)))
        if(hostName==None):
            hostName = input('Input your host name or IP address :')
        if(hostPort==None):
            hostPort = input('Input your host port :')
        logger.info('Host name : {0}, Host Port : {1}'.format(hostName,hostPort))
        if(usePythonnet):
            from Formulatrix.Core.Protocol.TCP import TcpFmlxDriver
            drv = TcpFmlxDriver(hostName,int(hostPort))
            drv.ReadTimeout = 1000
            return drv,address_list
        else:
            from FormulatrixCorePy.FmlxDrivers.TcpFmlxDriver import TcpClient
            drv = TcpClient(hostName,int(hostPort)),address_list
            return drv

    elif driver_name == 'BleDevice':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Ble.Win import BleWin
            b=BleWin()
            ble = b.GetBleDeviceName()
            if(not ble):
                raise ModuleNotFoundError('No Bluetooth device')
            k=0
            for i in ble:
                print ('%s. %s' % (k, i))
                k+=1
            choose = int(input('Choose BLE Device : '))
            b.SetBleDevice(ble[choose])
            b.Log=True
            return b, address_list
        else:
            raise NotImplementedError('currently not implemented!')
                  
    elif driver_name == 'BluetoothRFComm':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Bluetooth.RFComm.Win import BlueToothRFComm
            if(not hostName):
                pass
                # device_list = BluetoothFmlxDriver.Scan()
                # choose = int(input('choose your device :'))
                # returimn BluetoothFmlxDriver.BluetoothRFCommClientFmlxDriver(device_list[choose-1][0]),address_list  
            else:
                return BlueToothRFComm(hostName,1),address_list
        else:
            from FormulatrixCorePy.FmlxDrivers import BluetoothFmlxDriver
            if(not hostName):
                device_list = BluetoothFmlxDriver.Scan()
                choose = int(input('choose your device :'))
                return BluetoothFmlxDriver.BluetoothRFCommClientFmlxDriver(device_list[choose-1][0]),address_list  
            else:
                return BluetoothFmlxDriver.BluetoothRFCommClientFmlxDriver(hostName),address_list

    elif driver_name == 'PCAN' or driver_name == 'PCANFD' or driver_name == 'PCANSequential' or driver_name == 'PCANFDSequential':
        return PCANModeSelector(driver_name,address_list,usePythonnet,useBRS=canFdUseBRS,logger=logger)    
            
    elif driver_name == 'SerialPort':
        if(usePythonnet):
            if(type(address_list)!=int):
                logger.error('Serial Port doesn\'t support multiple address! address type : {0}'.format(type(address_list)))
                raise NotImplementedError('Serial Port doesn\'t support multiple address! address type : {0}'.format(type(address_list)))
            from Formulatrix.Core.Protocol.Serial.Win import serialwin
            serial_port=get_serial_port(autoSelectComPort)
            drv=serialwin()
            drv.set_com_port(serial_port)
            return drv,address_list
        else:
            from FormulatrixCorePy.FmlxDrivers.SerialFmlxDriver import SerialFmlxDriver
            if(serialComPort==None):
                portname=get_serial_port(autoSelectComPort)
            else:
                portname=serialComPort
            return SerialFmlxDriver(portname=portname),address_list

    elif driver_name == 'KvaserCanSequential':
        if(usePythonnet):
            clr.AddReference("Formulatrix.Core.Protocol.Can.KVaser.Win")
            from Formulatrix.Core.Protocol.CanSequential.KVaser.Win import KvaserSequentialFmlxDriver     
            from Formulatrix.Core.Protocol.Can.KVaser.Win import CanBusBitRate
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanSequentialFmlxDriver
        if(type(address_list) == list):
            drv=[]
            for addr in address_list:
                if(usePythonnet):
                    # drv+=[KvaserSequentialFmlxDriver.Overloads[int, int, CanBusBitRate, IFmlxLogger](address_list,0,CanBusBitRate.Bitrate_1M ,NetLogger.Pythonlogger('KVaser',log_handler=log_handler))]
                    drv+=[KvaserSequentialFmlxDriver(addr,0)]
                else:
                    drv+=[CanSequentialFmlxDriver(address=addr,bustype = 'kvaser')]
            return drv
        elif(type(address_list) == int):
            if(usePythonnet):
                # drv = KvaserSequentialFmlxDriver.Overloads[int, int, CanBusBitRate, IFmlxLogger](address_list,0,CanBusBitRate.Bitrate_1M ,NetLogger.Pythonlogger('KVaserSequential',log_handler=log_handler)),address_list
                # drv = KvaserSequentialFmlxDriver(int(address_list),0,CanBusBitRate.Bitrate_1M ,NetLogger.Pythonlogger('KVaser',log_handler=log_handler))
                drv=KvaserSequentialFmlxDriver(address_list,0)
            else:
                drv=CanSequentialFmlxDriver(address=address_list,bustype = 'kvaser')
            return drv,address_list
        else:
            logger.error('unknown address list type : {0}'.format(type(address_list)))
            
    elif driver_name == 'FVaserCanSequential':
        if(serialComPort==None):
            serial_port=get_serial_port(autoSelectComPort,logger=logger)
        else:
            serial_port=serialComPort
        
        if(usePythonnet):
            from Formulatrix.Core.Protocol.SLCan.Win import FmlxSlcanSequential

        if(type(address_list) == int):
            if(usePythonnet):
                return FmlxSlcanSequential(address_list,serial_port),address_list
            else:
                from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
                return SlcanFmlxDriver(address_list,serial_port,isUsingSequential=True),address_list
        elif(type(address_list) == list):
            drv=[]
            for addr in address_list:
                if(usePythonnet):   
                    drv+=[FmlxSlcanSequential(addr,serial_port)]
                else:
                    from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
                    drv+=[SlcanFmlxDriver(addr,serial_port,isUsingSequential=True)]
            return drv
        
    elif driver_name == 'SLCAN Linux':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Can.Linux import LinuxCanFmlxDriver
        else:
            from FormulatrixCorePy.FmlxDrivers.SlcanFmlxDriver import SlcanFmlxDriver
            
        if(type(address_list) == int):
            if(usePythonnet):
                return LinuxCanFmlxDriver(address_list,0,2,None),address_list
            else:
                return SlcanFmlxDriver(address_list,'/dev/ttyUSB1'),address_list
        elif(type(address_list) == list):
            drv=[]
            for i in address_list:
                if(usePythonnet):
                    drv+=[LinuxCanFmlxDriver(i,0,2,None)]
                else:
                    drv+=[SlcanFmlxDriver(i,'/dev/ttyUSB1')]
            return drv

    elif driver_name == 'CAN Linux':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Can.Linux import LinuxCanFmlxDriver
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanFmlxDriver
        if(type(address_list) == int):
            if(usePythonnet):
                return LinuxCanFmlxDriver(address_list,0,1,None),address_list
            else:
                return CanFmlxDriver(address=addr,bustype = 'socketcan_native',channel = 'can0'),address_list
        elif(type(address_list) == list):
            drv=[]
            for addr in address_list:
                if(usePythonnet):
                    drv+=[LinuxCanFmlxDriver(addr,0,1,None)]
                else:
                    drv+=[CanFmlxDriver(address=addr,bustype = 'socketcan_native',channel = 'can0')]
            return drv

    elif driver_name == 'VCAN Linux':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Can.Linux import LinuxCanFmlxDriver
            if(type(address_list) == int):
                return LinuxCanFmlxDriver(address_list,0,0,None),address_list
            elif(type(address_list) == list):
                drv=[]
                for addr in address_list:
                    drv+=[LinuxCanFmlxDriver(addr,0,0,None)]
                return drv    
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanFmlxDriver
            if(type(address_list) == int):
                return CanFmlxDriver(address=address_list,bustype = 'socketcan_native',channel = 'vcan0'),address_list
            elif(type(address_list) == list):
                drv = []
                for addr in address_list:
                    drv+=[CanFmlxDriver(address=addr,bustype = 'socketcan_native',channel = 'vcan0')]
                return drv

    elif driver_name == 'SPI Linux':
        from Formulatrix.Core.Protocol.Spi.Linux import SpiLinux
        return [SpiLinux(16000000)]

    elif driver_name == 'Serial Linux':
        from FormulatrixCorePy.FmlxDrivers.SerialFmlxDriver import SerialFmlxDriver
        if(serialComPort==None):
            portname=get_serial_port(autoSelectComPort)
        else:
            portname=serialComPort
        return SerialFmlxDriver(portname=portname),address_list

    elif driver_name == 'KVCanBridge':
        if(serialComPort==None):
            serial_port=get_serial_port()
        else:
            serial_port=serialComPort
        if(serial_port==None):
            raise Exception('no COM Port found')
        from virtualbridge import VirtualBridge
        bridge= VirtualBridge(serial_port,0)
        bridge.connect()
        if (bridge.isConnect()):
            print("Kvaser Virtual Bridge connect to : %s " % serial_port)
            clr.AddReference("Formulatrix.Core.Protocol.Can.KVaser.Win")
            from Formulatrix.Core.Protocol.Can.KVaser.Win import KvaserFmlxDriver        
            drv=[]
            for i in address_list:
                drv+=[KvaserFmlxDriver(i,0)]
            return drv
            #return[None]

    elif driver_name == 'SPI2CAN':
        if(usePythonnet):
            from Formulatrix.Core.Protocol.Spi2Can.Linux import Spi2CanLinux
            if(type(address_list) == list):
                drv = []
                for addr in address_list:
                    drv+=[Spi2CanLinux(addr)]
                return drv
            elif(type(address_list) == int):
                return Spi2CanLinux(address_list),address_list
        else:
            if(type(address_list) == list):
                from FormulatrixCorePy.FmlxDrivers.Spi2CanFmlxDriver import SPI2CANFmlxDriver
                drv = []
                for addr in address_list:
                    drv+=[SPI2CANFmlxDriver(addr)]
                return drv
            elif(type(address_list) == int):
                return SPI2CANFmlxDriver(address_list),address_list

    elif driver_name == 'VCAN Sequential Linux' :
        if(usePythonnet):
            raise NotImplementedError('Not yet implemented')
            # from Formulatrix.Core.Protocol.Can.Linux import LinuxCanFmlxDriver
            # if(num_of_address==0):
            #     return LinuxCanFmlxDriver(address_fmlx,0,0,None),address_fmlx
            # else:
            #     drv=[]
            #     for i in address_list:
            #         drv+=[LinuxCanFmlxDriver(i,0,0,None)]
            #     return drv    
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanSequentialFmlxDriver
            if(type(address_list) == int):
                return CanSequentialFmlxDriver(address=address_list,bustype = 'socketcan_native',channel = 'vcan0'),address_list
            else:
                drv = []
                for addr in address_list:
                    drv+=[CanSequentialFmlxDriver(address=addr,bustype = 'socketcan_native',channel = 'vcan0')]
                return drv

    elif driver_name == 'CAN Sequential Linux' :
        print('can sequental')
        if(usePythonnet):
            raise NotImplementedError('Not yet implemented')
            # from Formulatrix.Core.Protocol.Can.Linux import LinuxCanFmlxDriver
            # if(num_of_address==0):
            #     return LinuxCanFmlxDriver(address_fmlx,0,0,None),address_fmlx
            # else:
            #     drv=[]
            #     for i in address_list:
            #         drv+=[LinuxCanFmlxDriver(i,0,0,None)]
            #     return drv    
        else:
            from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CanSequentialFmlxDriver
            if(type(address_list) == int):
                return CanSequentialFmlxDriver(address=address_list,bustype = 'socketcan_native',channel = 'can0',isOld=usingOldCanSequential),address_list
            else:
                drv = []
                for addr in address_list:
                    drv+=[CanSequentialFmlxDriver(address=addr,bustype = 'socketcan_native',channel = 'can0',isOld=usingOldCanSequential)]
                return drv

    else:
        logger.error('No choice!')
        raise IndexError('No choice!')

# it will return the driver string!
def CommunicationTypeMenu():
    commTypeCallback = [CANCommTypeMenu,SerialCommTypeMenu,TCPCommTypeMenu,BluetoothCommTypeMenu,SPICommTypeMenu]
    print('1. CAN')
    print('2. Serial')
    print('3. TCP')
    print('4. Bluetooth')
    if(get_platform() == 'Linux' or get_platform() == 'linux'):
        print('5. SPI') # only on Linux
    try:
        strInput = input('Choose Your Communication Type :')
        commType = int(strInput)
    except ValueError:
        raise ValueError('CommunicationTypeMenu Invalid Value : {0}'.format(strInput))
    
    return commTypeCallback[commType-1]()

def CANCommTypeMenu():
    if(get_platform() == 'Linux' or get_platform() == 'linux'):
        print('1. VCAN')
        print('2. SLCAN')
        print('3. CAN')
        print('4. FVaser')
        print('5. PCAN')
        print('6. PCANFD')
    elif(get_platform() == 'Windows'):
        print('1. FVaser')
        print('2. KVaser')
        print('3. PCAN')
        print('4. PCANFD')
        print('5. KVaser - Fvaser Bridge')
    else:
        raise NotImplementedError('Platform {0} is currently Unsupported!'.format(get_platform()))
    strInput = input('Choose Your CAN Type :')
    try:
        canType = int(strInput) - 1
    except ValueError:
        raise ValueError('CANCommTypeMenu Invalid Value : {0}'.format(strInput))
    if(get_platform() == 'Linux' or get_platform() == 'linux'):
        if(canType<0 or canType>5):
            raise IndexError('CANCommTypeMenu Out of bound Value : {0}'.format(canType))
    if(get_platform() == 'Windows'):
        if(canType<0 or canType>4):
            raise IndexError('CANCommTypeMenu Out of bound Value : {0}'.format(canType))
        
    print('1. Sequential')
    print('2. Normal')
    strInput = input('Choose Your CAN Type :')
    try:
        canMode = int(strInput) - 1
    except ValueError:
        logging.error('CAN Mode Menu Invalid Value : {0}'.format(strInput))
        raise ValueError('CAN Mode Menu  Invalid Value : {0}'.format(strInput))
    if(canMode<0 or canMode>1):
        logging.error('CAN Mode Menu  Out of bound Value : {0}'.format(canMode))
        raise IndexError('CAN Mode Menu  Out of bound Value : {0}'.format(canMode))
    
    if(get_platform() == 'Linux' or get_platform() == 'linux'):
        if(canType==0): # vcan
            if(canMode == 0):
                return 'VCAN Sequential Linux'
            elif(canMode == 1):
                return 'VCAN Linux'
        elif(canType==1): #slcan
            if(canMode == 0):
                return 'SLCAN Sequential Linux'
            elif(canMode == 1):
                return 'SLCAN Linux'
        elif(canType==2): # can hardware
            if(canMode == 0):
                return 'CAN Sequential Linux'
            elif(canMode == 1):
                return 'CAN Linux'
        elif(canType==3): # FVaser
            if(canMode == 0):
                return 'FVaserCanSequential'
            elif(canMode == 1):
                return 'FVaser'
        elif(canType==4): # PCAN
            if(canMode == 0):
                return 'PCANSequential'
            elif(canMode == 1):
                return 'PCAN'
        elif(canType==5): # PCANFD
            if(canMode == 0):
                return 'PCANFDSequential'
            elif(canMode == 1):
                return 'PCANFD'
    elif(get_platform() == 'Windows'):
        if(canType==0): # FVaser
            if(canMode == 0):
                return 'FVaserCanSequential'
            elif(canMode == 1):
                return 'FVaser'
        elif(canType==1): #KVaser
            if(canMode == 0):
                return 'KvaserCanSequential'
            elif(canMode == 1):
                return 'KVaser'
        elif(canType==2): # PCAN
            if(canMode == 0):
                return 'PCANSequential'
            elif(canMode == 1):
                return 'PCAN'
        elif(canType==3): # PCANFD
            if(canMode == 0):
                return 'PCANFDSequential'
            elif(canMode == 1):
                return 'PCANFD'
        elif(canType==4): # KVaser - FVaser Bridge
            pass
            # if(canMode == 0):
            #     return 'PCANFDSequential'
            # elif(canMode == 1):
            #     return 'PCANFD'

def SerialCommTypeMenu(logger = None):
    if(get_platform() == 'Windows'):
        print('1. Serial Port')
        print('2. FTDI')
    elif(get_platform() == 'Linux' or get_platform() == 'linux'):
        return 'Serial Linux'
    else:
        raise NotImplementedError('Platform {0} is currently Unsupported!'.format(get_platform()))
    strInput = input('Choose Your Serial Type :')
    try:
        serialMode = int(strInput) - 1
    except ValueError:
        raise ValueError('CAN Mode Menu  Invalid Value : {0}'.format(strInput))
    if(serialMode<0 or serialMode>1):
        raise IndexError('CAN Mode Menu  Out of bound Value : {0}'.format(serialMode))
    if(serialMode == 0):
        return 'SerialPort'
    elif(serialMode == 1):
        return 'FTDI'

def TCPCommTypeMenu():
    return 'TCP'

def BluetoothCommTypeMenu():
    print('1. BLE')
    print('2. RFComm')
    strInput = input('Choose Your Bluetooth Type :')
    
    choose = int(strInput)
    if(choose == 1):
        return 'BleDevice'
    elif(choose==2):
        return 'BluetoothRFComm'

def SPICommTypeMenu():
    if(get_platform() != 'Linux' and get_platform() != 'linux'):
        raise NotImplementedError('Platform {0} is currently Unsupported!'.format(get_platform()))
    return 'SPI Linux'

def PCANModeSelector(pcanDriverName,address_list,usePythonnet,useBRS = False,logger = None):
    if(logger):
        logger.info('PCAN driver name : {0} , address(es) : {1} , use pythonnet : {2}'.format(pcanDriverName,address_list,usePythonnet))
    
    if(usePythonnet):
        if(pcanDriverName == 'PCAN'):
            from Formulatrix.Core.Protocol.Can.PCAN.Win import PCanFmlxDriver
            pcanClass = PCanFmlxDriver
            useCanSequential = False
        elif(pcanDriverName == 'PCANFD'):
            from Formulatrix.Core.Protocol.Can.PCAN.Win import PCanFdFmlxDriver
            pcanClass = PCanFdFmlxDriver
            useCanSequential = False
        elif(pcanDriverName == 'PCANSequential'):
            from Formulatrix.Core.Protocol.Can.PCAN.Win import PCanFmlxDriver
            pcanClass = PCanFmlxDriver
            useCanSequential = True
        elif(pcanDriverName == 'PCANFDSequential'):
            from Formulatrix.Core.Protocol.Can.PCAN.Win import PCanFdSequentialFmlxDriver
            pcanClass = PCanFdSequentialFmlxDriver
            useCanSequential = True
        avaiable_channels = pcanClass.GetAvaiableChannel()
        if(logger):
            logger.info('avaiable PCAN channels : {0}'.format(avaiable_channels))
        for index,channel in enumerate(avaiable_channels):
            print ('%s. %s' % (index+1, channel))
        try:
            if(index>1):
                choose = input('Choose Your PCAN channel : ')
                pcan_fd = pcanClass.ChannelStringToInteger(avaiable_channels[int(choose)])
            else: # auto select
                pcan_fd = pcanClass.ChannelStringToInteger(avaiable_channels[0])
        except UnboundLocalError:
            logger.error('No PCAN device found!')
            raise ModuleNotFoundError('No PCAN device found!')
        if(logger):
            logger.info('selected PCAN channel : {0}'.format(pcan_fd))    
        if(type(address_list) == int):
            return pcanClass(address_list,pcan_fd,useCanSequential,NetLogger.Pythonlogger('PCAN',log_handler=logger)),address_list
        elif(type(address_list) == list):
            drv=[]
            for addr in address_list:
                drv+=[pcanClass(addr,pcan_fd,useCanSequential,NetLogger.Pythonlogger('PCAN',log_handler=logger))]
            return drv
    else:
        from FormulatrixCorePy.FmlxDrivers.PCanFmlxDriver import PCanFmlxDriver
        if(pcanDriverName == 'PCAN'):
            useFd = False
            useCanSequential = False
        elif(pcanDriverName == 'PCANFD'):
            useFd = True
            useCanSequential = False
        elif(pcanDriverName == 'PCANSequential'):
            useFd = False
            useCanSequential = True
        elif(pcanDriverName == 'PCANFDSequential'):
            useFd = True
            useCanSequential = True
        from PCANBasic import PCANBasic
        avaiable_channels = PCANGetAvaiableChannel()
        if(logger):
            logger.info('avaiable PCAN channels : {0}'.format(avaiable_channels))
        for index,channel in enumerate(avaiable_channels):
            print ('%s. %s' % (index+1, channel))
        try:
            if(index>1):
                choose = int(input('Choose Your PCAN channel : ')) - 1
            else: # auto select
                choose = 0
        except UnboundLocalError:
            raise ModuleNotFoundError('No PCAN device found!')

        if(logger):
            logger.info('selected PCAN channel : {0}'.format(avaiable_channels[choose]))    
        if(type(address_list) == int):
            return PCanFmlxDriver(address=address_list,channel = avaiable_channels[choose],isFd=useFd,isUsingSequential=useCanSequential,isUsingBRS=useBRS),address_list
        elif(type(address_list) == list):
            drv=[]
            for addr in address_list:
                drv+=[PCanFmlxDriver(address=addr,channel = avaiable_channels[choose],isFd=useFd,isUsingSequential=useCanSequential,isUsingBRS=useBRS)]
            return drv

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

def get_serial_port(auto_choose = False,logger = None):
    import serial.tools.list_ports   # import serial module
    comPorts = list(serial.tools.list_ports.comports())    # get list of all devices connected through serial port
    if(logger):
        logger.info('auto choose enabled is {0}'.format(auto_choose))
    if len(comPorts)==0:
        raise OSError('No COM port found!')
    else:
        platform = get_platform()
        for i in range(len(comPorts)):
                   
            if platform == 'Linux' or platform == 'linux':
                print (i+1,'.{0},{1}'.format(comPorts[i].name,comPorts[i].description))
            elif platform == 'Windows':
                print (i+1,'.',comPorts[i].description)
            
        if(auto_choose == False or len(comPorts)>2): 
            choose = input(': ')
        else:
            # choose the only one if there was only one
            if(len(comPorts) == 1):
                choose = 1
            # choose the bigger one if there are 2 comport detected
            elif(len(comPorts) == 2):
                comPortString=[str(comPorts[0]).split()[0],str(comPorts[1]).split()[0]]
                selected_comPort = comPortString[0] if int(comPortString[0][3:]) > int(comPortString[1][3:]) else  comPortString[1]
                return selected_comPort
        serial_port_string = str(comPorts[int(choose)-1]).split()[0]
        if(logger):
            logger.info('selected Comport : {0}'.format(serial_port_string))
    return serial_port_string

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
    return ftdi_list[choose]

def PCANGetAvaiableChannel():
    import PCANBasic
    items = []
    objPCANBasic = PCANBasic.PCANBasic()
    result =  objPCANBasic.GetValue(PCANBasic.PCAN_NONEBUS, PCANBasic.PCAN_ATTACHED_CHANNELS)
    if  (result[0] == PCANBasic.PCAN_ERROR_OK):
        # Include only connectable channels
        #
        for channel in result[1]:
            if  (channel.channel_condition & PCANBasic.PCAN_CHANNEL_AVAILABLE):
                items.append(PCANFormatChannelName(channel.channel_handle))

    items.sort()
    return items
    
def PCANFormatChannelName(handle):
    import PCANBasic
    if handle < 0x100:
        devDevice = PCANBasic.TPCANDevice(handle >> 4)
        byChannel = handle & 0xF
    else:
        devDevice = PCANBasic.TPCANDevice(handle >> 8)
        byChannel = handle & 0xFF

    return ('%s%s' % (PCANGetDeviceName(devDevice.value), byChannel))
    
## Gets the name of a PCAN device
def PCANGetDeviceName(handle):
    import PCANBasic
    switcher = {
        PCANBasic.PCAN_NONEBUS.value: "PCAN_NONEBUSBUS",
        PCANBasic.PCAN_PEAKCAN.value: "PCAN_PEAKCANBUS",
        PCANBasic.PCAN_ISA.value: "PCAN_ISABUS",
        PCANBasic.PCAN_DNG.value: "PCAN_DNGBUS",
        PCANBasic.PCAN_PCI.value: "PCAN_PCIBUS",
        PCANBasic.PCAN_USB.value: "PCAN_USBBUS",
        PCANBasic.PCAN_PCC.value: "PCAN_PCCBUS",
        PCANBasic.PCAN_VIRTUAL.value: "PCAN_VIRTUALBUS",
        PCANBasic.PCAN_LAN.value: "PCAN_LANBUS"
    }
    return switcher.get(handle,"UNKNOWN")    

def FmlxDeviceConnectorSingle(address=None,driver_name=None,serialComPort=None,hostName=None,hostPort=None,autoSelectComPort = False,canFdUseBRS = False,usePythonnet = True,log_handler = None):
    return FmlxDeviceConnector(driver_name=driver_name,address_list=address,serialComPort=serialComPort,hostName=hostName,hostPort=hostPort,canFdUseBRS = canFdUseBRS,autoSelectComPort = autoSelectComPort,usePythonnet = usePythonnet,log_handler = log_handler)
