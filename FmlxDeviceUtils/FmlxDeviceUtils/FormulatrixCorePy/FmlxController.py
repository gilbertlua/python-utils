from functools import partial
import os
import sys
import struct
import threading
import ctypes
import logging
import FmlxLogger

try:
    import queue
except ImportError:
    import Queue as queue
from datetime import datetime

from FormulatrixCorePy.FmlxPacket import FmlxPacket

try:
    # Should be defined in Python 3
    x = TimeoutError
except:
    # For Python 2
    class TimeoutError(Exception):
        def __init__(self, value="Timeout"):
            self.value = value

        def __str__(self):
            return repr(self.value)

class IllegalOpcodeError(Exception):
    def __init__(self, value="Illegal Opcode"):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FmlxController(object):
    EVENT_OPCODE_OFFSET = 512
    NO_ERROR_OPCODE = 0
    ILLEGAL_SIZE_OPCODE = -3
    NULL_STRING_TEST = -4

    CHECKSUM_ERROR = -40
    ARGUMENT_ERROR = -41
    ILLEGAL_OPCODE = -42
    VERSION = '1.0.0'

    def __init__(self, driver, useSinglePrecision=False, retryCount=1,log_handler = None):
        self._logger = logging.getLogger('FmlxController_{0}'.format(driver.DriverName))
        self._logger.setLevel(logging.DEBUG)
        self._driver = driver
        if(log_handler):
            self._logger.addHandler(log_handler)
            self._driver.SetLogHandler(log_handler)
        self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.CRITICAL))
        self._logger.info('FmlxController version : {0}, driver :{1} , useSinglePrecision : {2}, retryCount : {3}'.format(FmlxController.VERSION,driver.DriverName,useSinglePrecision,retryCount))
        
        
        self._useSinglePrecision = useSinglePrecision
        self._receiveThreadEnabled = False
        self._receivedPacket = None
        self._retryCount = retryCount
        self._responseDataAvaiableEvent = threading.Event()
        self._sendCommandLock = threading.Lock()
        self._eventHandlers = []

    @property
    def ReadTimeout(self):
        return self._driver.ReadTimeout

    @ReadTimeout.setter
    def ReadTimeout(self, value):
        self._logger.debug('Set Read Timeout : {0} miliseconds'.format(value))
        self._driver.ReadTimeout = value

    @property
    def WriteTimeout(self):
        return self._driver.WriteTimeout

    @WriteTimeout.setter
    def WriteTimeout(self, value):
        self._logger.debug('Set Write Timeout : {0}'.format(value))
        self._driver.WriteTimeout = value

    @property
    def Connected(self):
        return self._driver.Connected

    def SendCommand(self, opcode, address, *args):
        if(not self.Connected):
            self._logger.exception('Try to send command but not connected')
            raise ConnectionRefusedError('Not Connected!')
        with self._sendCommandLock:
            self._logger.debug('send command , args : {0}'.format(args))
            packet = FmlxPacket(None)
            packet.Opcode = opcode
            packet.Address = address
            for arg in args:
                if(self._useSinglePrecision and type(arg)==ctypes.c_double):
                    packet.Add(ctypes.c_float(arg.value))
                else:
                    packet.Add(arg)
            packet.Checksum=packet.calculateChecksum()
            self._logger.debug('send command, size :{0}, packetId : {1}, address : {2}, opcode : {3}, payload : {4} ,packet checksum : {5}'.format(packet.Size,packet.PacketId,packet.Address,packet.Opcode,packet.Payload,packet.Checksum))
            self._responseDataAvaiableEvent.clear()
            retry = self._retryCount
            while(retry > 0):
                self._driver.Write(packet.ToRaw)
                if(self._responseDataAvaiableEvent.wait(self.ReadTimeout/1000)):
                    break
                self._responseDataAvaiableEvent.clear()
                retry -= 1
                self._logger.debug('Timeout, retry left : {0}'.format(retry))
            else:
                self._responseDataAvaiableEvent.clear()
                # self._logger.exception('Send Command,TimeoutError :No data received while waiting for {0} Seconds x {1}'.format(
                #     self.ReadTimeout, self._retryCount))
                raise TimeoutError('No data received while waiting for {0} MiliSeconds x {1}'.format(
                    self.ReadTimeout, self._retryCount))
            if(not self._receivedPacket.VerifyChecksum()):
                raise Exception('Wrong Checksum!')
            if(ctypes.c_int16(self._receivedPacket.Opcode).value == FmlxController.CHECKSUM_ERROR):
                raise Exception('Device Receive Wrong Checksum!')
            if(ctypes.c_int16(self._receivedPacket.Opcode).value == FmlxController.ILLEGAL_SIZE_OPCODE):
                raise Exception('Device Receive Illegal Size Opcode!')
            if(ctypes.c_int16(self._receivedPacket.Opcode).value == FmlxController.ILLEGAL_OPCODE):
                raise IllegalOpcodeError('Device Receive Illegal Opcode!')
            return self._receivedPacket
        
    def Connect(self):
        if(self.Connected):
            return
        self._driver.Connect()
        self._receiveThreadInstance = threading.Thread(
            target=self._receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        if(not self.Connected):
            return
        self._driver.Disconnect()
        
    def ResetFirmware(self):
        if (not self.Connected):
            raise Exception('Cannot reset firmware while not connected.')
        self._driver.ResetDevice()

    def _receiveThread(self):
        receivedData = []
        hasRemainingData = False
        
        while(self.Connected):
            if(not hasRemainingData):
                driverData = self._driver.Read()  
                if(driverData):
                    receivedData+=driverData
                else:
                    receivedData = [] # purge it

            packet = FmlxPacket(receivedData,self._useSinglePrecision)
            
            if(not packet.IsSizePacketReceived):
                hasRemainingData = False
                continue
            if(not packet.IsSizeValid):
                hasRemainingData = False
                continue
            if(not packet.IsSizeLegal):
                while(not packet.IsSizeLegal and len(receivedData) >= 2):
                    self._logger.debug('packet size is not legal, packet : {0}, received data : {1}'.format(packet.ToRaw,receivedData))
                    receivedData = receivedData[2:] # shift until valid data size is found ( < 524 )
                    packet = FmlxPacket(receivedData,self._useSinglePrecision)
                hasRemainingData = False
                continue
            if(not packet.IsAllDataReceived):
                # self._logger.debug('not all data received, packet : {0}, received data : {1}'.format(packet.ToRaw,receivedData))
                hasRemainingData = False
                continue
            if(not packet.VerifyChecksum()):
                self._logger.debug('receiveThread,Checksum Error packet checksum : {0}, calculated checksum : {1}, packet : {2}, received data : {3}'.format(packet.Checksum,packet.calculateChecksum(),packet.ToRaw,receivedData))
                receivedData = receivedData[2:] # shift until valid data found
                hasRemainingData = False
                continue
            # event goes here
            if(packet.Opcode >= FmlxController.EVENT_OPCODE_OFFSET and packet.Opcode != ctypes.c_uint16(FmlxController.ILLEGAL_OPCODE).value):
                for handler in self._eventHandlers:
                    self._logger.debug('receiveThread,Event Received, size :{0}, packetId : {1}, address : {2}, opcode : {3}, payload : {4} ,packet checksum : {5}'.format(packet.Size,packet.PacketId,packet.Address,packet.Opcode,packet.Payload,packet.Checksum))
                    # print('event:',packet.ToRaw)
                    handler(packet)
                receivedData=receivedData[packet.Size+2:]
                if(len(receivedData)>0):
                    hasRemainingData = True
                continue
            # response goes here
            self._logger.debug('receiveThread,Response Received, size :{0}, packetId : {1}, address : {2}, opcode : {3}, payload : {4} ,packet checksum : {5}'.format(packet.Size,packet.PacketId,packet.Address,packet.Opcode,packet.Payload,packet.Checksum))
            self._receivedPacket = packet
            receivedData=receivedData[packet.Size+2:]
            self._responseDataAvaiableEvent.set()
            if(len(receivedData)>0):
                hasRemainingData = True

    def __iadd__(self,handler):
        self._eventHandlers.append(handler)
        return self

    def uncaughtExceptionHandler(self,exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        self._logger.critical('Uncaught Exception',exc_info=(exc_type, exc_value, exc_traceback))

class FmlxControllerSlave():
    EVENT_OPCODE_OFFSET = 512
    
    class ErrorOpcode():
        NO_ERROR_OPCODE = 0
        ILLEGAL_SIZE_OPCODE = -3
        NULL_STRING_TEST = -4

        CHECKSUM_ERROR = -40
        ARGUMENT_ERROR = -41
        ILLEGAL_OPCODE = -42
    
    def __init__(self, driver, address,commandCallbacks,timeout = 500,useSinglePrecision = False,log_handler = None):
        self._logger = logging.getLogger('FmlxControllerSlave_{0}'.format(driver.DriverName))
        self._logger.setLevel(logging.DEBUG)
        self._driver = driver
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.CRITICAL))
        self._logger.info('FmlxControllerSlave version : {0}, driver :{1} , useSinglePrecision : {2}'.format(FmlxController.VERSION,driver.DriverName,useSinglePrecision))
        
        self._driver = driver
        self._address = address
        self._useSinglePrecision = useSinglePrecision
        self._commandCallbacks = commandCallbacks
        self._timeout = timeout
        self._receiveThreadEnabled = False
        self._receivedPacket = None
        self._responseDataAvaiableEvent = threading.Event()
        self._sendCommandLock = threading.Lock()
        self._eventHandlers = []
        self._firstCommand = False # has not received any command yet
        self._currentPacketId = None
        self._currentChecksum = None
        self._responsePacket = FmlxPacket()
        self._eventPacket = FmlxPacket()
        self._eventId = 0
        self._CommandPacket = None
        self._driver.Connect()
        self._receiveThreadInstance = threading.Thread(target=self._receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def __del__(self):
        self._driver.Disconnect()
        pass

    # commands
    def NumCmdUnread(self):
        return 0

    def ResetCmd(self):
        pass
    
    def ReadCmdBool(self):
        return self._CommandPacket.FetchBool()
	
    def ReadCmdInt16(self):
        return self._CommandPacket.FetchInt16()
	
    def ReadCmdUint16(self):
        return self._CommandPacket.FetchUInt16()

    def ReadCmdInt32(self):
        return self._CommandPacket.FetchInt32()

    def ReadCmdUint32(self):
        return self._CommandPacket.FetchUInt32()

    def ReadCmdFloat(self):
        if(self._useSinglePrecision):
            return self._CommandPacket.FetchFloat()
        else:
            return self._CommandPacket.FetchDouble()

    def ReadCmdBuf(self,length):
        return self._CommandPacket.FetchInt16Array(length)

    def ReadCmdStr(self):
        return self._CommandPacket.FetchString()

    # responses
    def ClearRsp(self):
        self._responsePacket.ResetWrite()
        self._responsePacket.ResetRead()

    def WriteRsp(self,values):
        self._responsePacket.Add(values)

    # events
    def ClearEvt(self):
        self._eventPacket.ResetWrite()

    def WriteEvt(self,values):
        self._eventPacket.Add(values)

    def SendEvt(self,evtOpcode):
        self._eventPacket.PacketId = self._eventId
        self._eventId+=1
        self._eventPacket.Address = self._address
        self._eventPacket.Opcode = evtOpcode
        self._eventPacket.Checksum = self._eventPacket.calculateChecksum()
        self._driver.Write(self._eventPacket.ToRaw)

    def SendError(self,errOpcode):
        self._responsePacket.Address = self._address
        self._responsePacket.Opcode = errOpcode

    def _receiveThread(self):
        receivedData = []
        while(self._driver.Connected):
            receivedData += self._driver.Read()
            packet = FmlxPacket(receivedData)
            if(not packet.IsSizePacketReceived):
                # print(receivedData)
                continue
            if(not packet.IsSizeLegal):
                while(not packet.IsSizeLegal and len(receivedData) >= 2):
                    receivedData = receivedData[2:] # shift until valid data size is found ( < 524 )
                    packet = FmlxPacket(receivedData)
                continue
            if(not packet.IsAllDataReceived):
                continue
            if(not packet.VerifyChecksum()):
                receivedData=receivedData[packet.Size+2:] # drop all data
                # receivedData = receivedData[2:] 
                continue
            
            self._logger.debug(f'packet received, packedId : {packet.PacketId}, address : {packet.Address}, opcode : {packet.Opcode}, data : {packet.Payload}')
            
            if(packet.Address != self._address):
                self._logger.debug(f'invalid address, packet address : {packet.Address}, self address : {self._address}')
                receivedData=receivedData[packet.Size+2:]
                continue
            self._responsePacket.Opcode = 0
            self._responsePacket.Address = self._address
            
            if(packet.PacketId != self._currentPacketId and packet.Checksum != self._currentChecksum):    
                self._currentPacketId = packet.PacketId
                self._currentChecksum = packet.Checksum
                self._responsePacket.ResetWrite()
                self._CommandPacket = packet
                try:
                    self._commandCallbacks[packet.Opcode](self) # responsePacket data payload will be updated by the callback
                except KeyError:
                    self._logger.debug(f'illegal opcode, op : {packet.Opcode}')
                    self.SendError(-42)
            else:
                self._logger.debug('Same packet ID/Checksum as before')

            self._responsePacket.Checksum = self._responsePacket.calculateChecksum()
            self._logger.debug(f'response send, packedId : {self._responsePacket.PacketId}, address : {self._responsePacket.Address}, opcode : {self._responsePacket.Opcode}, data : {self._responsePacket.Payload}, checksum : {self._responsePacket.Checksum}')
            self._driver.Write(self._responsePacket.ToRaw)
            receivedData=receivedData[packet.Size+2:]



