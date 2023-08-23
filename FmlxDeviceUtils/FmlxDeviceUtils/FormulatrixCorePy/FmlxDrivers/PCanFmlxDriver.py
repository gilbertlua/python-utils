
from os import stat
import can
from queue import Queue
import threading
import math
import logging
import FmlxLogger
import os
from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CCanSequentialHandler

class BaudRateFD():
    PCAN_BAUDFD_2M = 0,
    PCAN_BAUDFD_4M = 1,
    PCAN_BAUDFD_6M = 2,
    PCAN_BAUDFD_8M = 3,
    PCAN_BAUDFD_10M = 4,
    PCAN_BAUDFD_12M = 5

class PCanFmlxDriver():
    DriverName = 'PCan'
    VERSION = '1.0.0'
    _msgQueues = dict()
    _dataAvaiableEvent = dict()
    _Channels = []
    _BitRates = [] 
    _Buses = {}
    _logger = None
    _ReceiveThreadInstances = {}
    FILTER = [{"can_id": 0, "can_mask": 0, "extended":False}] # make it receive all data

    def __init__(self,address,channel = 0,bitrate = 1000000,isFd = False,isUsingBRS = False,baudRateFd = BaudRateFD.PCAN_BAUDFD_2M,isUsingSequential = False,log_handler = None):
        if(not PCanFmlxDriver._logger):
            PCanFmlxDriver._logger = logging.getLogger('PCanFmlxDriver')
            PCanFmlxDriver._logger.setLevel(logging.DEBUG)
            if(log_handler):
                PCanFmlxDriver._logger.addHandler(log_handler)
            PCanFmlxDriver._logger.info('PCanFmlxDriver version : {0}, address : {1}, channel : {2}'.format(PCanFmlxDriver.VERSION,address,channel))
        
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._channel = channel
        self._bitRate = bitrate
        self._bitRateFd = baudRateFd
        self._connected = False
        self._isUsingSequential=isUsingSequential
        self._isFd = isFd
        if(self._isFd):
            self._isUsingBRS = isUsingBRS
            self._maxDLC = 63
            if(self._isUsingSequential):
                self._txFrameId = 0 # for sequential can frame identification
                pass
        else:
            self._isUsingBRS = False
            self._maxDLC = 8
            if(self._isUsingSequential):
                self._txFrameId = 0 # for sequential can frame identification
                self._CanSeqHandler = CCanSequentialHandler()
            else:
                self._CanSeqHandler = None
        

    def SetLogHandler(self,log_handler):
        PCanFmlxDriver._logger.addHandler(log_handler)
        if(self._isUsingSequential):
            self._CanSeqHandler.SetLogHandler(log_handler=log_handler)

    @property
    def Connected(self):
        return self._connected

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return PCanFmlxDriver._msgQueues[self._receiveMessageId].qsize()

    def Connect(self):
        PCanFmlxDriver._logger.debug('Connect, channel : {0}, receive filter id : {1}'.format(self._channel,self._receiveMessageId))
        PCanFmlxDriver._msgQueues.update([(self._receiveMessageId, Queue())])
        PCanFmlxDriver._dataAvaiableEvent.update([(self._receiveMessageId, threading.Event())])
        self._connected = True
        if(not self._channel in PCanFmlxDriver._Channels):
            PCanFmlxDriver._logger.debug('Connect, Opening PCan Channel : {0},isUsingFd : {1}, isUsingBRS : {2}, nominalBitrate : {3}, DataBitrate : {4}'.format(self._channel,self._isFd,self._isUsingBRS,self._bitRate,self._bitRateFd))
            if(self._isFd):
                f_clock_mhz,nom_brp,nom_tseg1,nom_tseg2,nom_sjw,data_brp,data_tseg1,data_tseg2,data_sjw = ConvertBaudRateFDtoParams(self._bitRateFd)
                canBusInstance = can.interface.Bus(bustype='pcan', channel=self._channel,can_filters=PCanFmlxDriver.FILTER,fd = True, accept_virtual = True, single_handle  = True,f_clock_mhz=f_clock_mhz,nom_brp=nom_brp,nom_tseg1=nom_tseg1,nom_tseg2=nom_tseg2,nom_sjw=nom_sjw,data_brp=data_brp,data_tseg1=data_tseg1,data_tseg2=data_tseg2,data_sjw=data_sjw)
                PCanFmlxDriver._Buses.update({self._channel : canBusInstance})   
            else:
                PCanFmlxDriver._Buses.update({self._channel : can.interface.Bus(bustype='pcan', channel=self._channel, bitrate=self._bitRate,can_filters=PCanFmlxDriver.FILTER, accept_virtual = True, single_handle  = True)})    
            PCanFmlxDriver._ReceiveThreadInstances.update({self._channel : threading.Thread(target=PCanFmlxDriver.receiveThread, args=(self,self._Buses[self._channel],self._isFd,self._CanSeqHandler))})
            PCanFmlxDriver._ReceiveThreadInstances[self._channel].daemon = True
            PCanFmlxDriver._ReceiveThreadInstances[self._channel].start()
        PCanFmlxDriver._Channels.append(self._channel)
        PCanFmlxDriver._BitRates.append(self._BitRates)
        
    def Disconnect(self):
        PCanFmlxDriver._logger.debug('Disconnecting, channel : {0}, receive filter id : {1}'.format(self._channel,self._receiveMessageId))
        del PCanFmlxDriver._msgQueues[self._receiveMessageId]
        del PCanFmlxDriver._dataAvaiableEvent[self._receiveMessageId]
        PCanFmlxDriver._Channels.remove(self._channel)
        PCanFmlxDriver._BitRates.remove(self._bitRate)
        if(not self._channel in PCanFmlxDriver._Channels):
            PCanFmlxDriver._logger.debug('Closing PCAN Bus Channel : {0}'.format(self._channel))
            PCanFmlxDriver._Buses[self._channel].shutdown()
            PCanFmlxDriver._Buses.pop(self._channel)       
        self._connected = False

    def ResetDevice(self):
        raise NotImplementedError('Not Implemented in CAN Core Py!')

    def Write(self, buffer):
        count = len(buffer)
        index = 0
        PCanFmlxDriver._logger.debug('Write, buffer : {0}'.format(buffer))
        while(count > 0):
            if(not self._isUsingSequential):
                datalen = min(self._maxDLC,count)
                dlc = dataLenToDlc(datalen)
                PCanFmlxDriver._logger.debug('Writing, index : {0}, count : {1}, msgId : {2}, datalen {3} ,dlc : {4}, data : {5}'.format(index,count,self._transmitMessageId,datalen,dlc,buffer[index:index+dlc],buffer))
                if(self._isFd):
                    bufferSend = [datalen]
                    bufferSend+= buffer[index:index+datalen]
                    dataSend = bufferSend
                else:
                    dataSend =  buffer[index:index+dlc]   
                PCanFmlxDriver._Buses[self._channel].send(can.Message(data = dataSend,is_extended_id=False,arbitration_id=self._transmitMessageId,is_fd=True,bitrate_switch=self._isUsingBRS))
                count -= datalen
                index += datalen
            else:
                if(self._isFd):
                    pass
                else:
                    canPayloads = self._CanSeqHandler.ConvertToCanSequentialFrame(buffer,self._txFrameId)
                    for canPayload in canPayloads:
                        # print(canPayload)
                        PCanFmlxDriver._Buses[self._channel].send(can.Message(data = canPayload,is_extended_id=False,arbitration_id=self._transmitMessageId,is_fd=True,bitrate_switch=self._isUsingBRS))
                    break
    
    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(PCanFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            PCanFmlxDriver._dataAvaiableEvent[self._receiveMessageId].wait(self.ReadTimeout/1000)  
        while(not PCanFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            buf.append(PCanFmlxDriver._msgQueues[self._receiveMessageId].get())
        # if(len(buf)>0):
        #     PCanFmlxDriver._logger.debug('Data Read, msgId : {0}, len : {1}, data : {2}'.format(self._receiveMessageId,len(buf),buf))             
        PCanFmlxDriver._dataAvaiableEvent[self._receiveMessageId].clear()
        return buf

    @staticmethod 
    def receiveThread(self,canBus,isFd,canSeqHandler=None):
        while(len(PCanFmlxDriver._Buses)>0):
            receivedData = canBus.recv(1)
            if(not receivedData):
                continue
            PCanFmlxDriver._logger.debug('Data Received, msgId : {0}, dlc : {1}, data : {2}'.format(receivedData.arbitration_id,receivedData.dlc,list(map(int,receivedData.data))))        
            if(not receivedData.arbitration_id in PCanFmlxDriver._msgQueues):
                continue
            if(receivedData.dlc==0):
                continue
            if(not canSeqHandler):
                if(not isFd):
                    if(receivedData.is_error_frame):
                        continue
                    for data in list(receivedData.data):
                        PCanFmlxDriver._msgQueues[receivedData.arbitration_id].put(data)
                    PCanFmlxDriver._dataAvaiableEvent[receivedData.arbitration_id].set()
                else:
                    if(receivedData.is_error_frame):
                        continue
                    for index in range(receivedData.data[0]):
                        PCanFmlxDriver._msgQueues[receivedData.arbitration_id].put(receivedData.data[index+1])
                    PCanFmlxDriver._dataAvaiableEvent[receivedData.arbitration_id].set()
            else:
                if(receivedData.is_error_frame):
                    continue
                frameId = canSeqHandler.WriteCANFrame(receivedData.dlc,list(map(int,receivedData.data)))
                if(frameId<0):
                    continue
                datas = canSeqHandler.ReadAllData(frameId)
                if(datas == []):
                    continue
                for data in datas:
                    PCanFmlxDriver._msgQueues[receivedData.arbitration_id].put(data)
                PCanFmlxDriver._dataAvaiableEvent[receivedData.arbitration_id].set()

def dataLenToDlc(datalen):
    if(0 <= datalen <=8):
        return datalen
    elif 9 <= datalen <= 12:
        return 9
    elif 13 <= datalen <= 16:
        return 10
    elif 17 <= datalen <= 20:
        return 11
    elif 21 <= datalen <= 24:
        return 12
    elif 25 <= datalen <= 32:
        return 13
    elif 33 <= datalen <= 48:
        return 14
    elif 49 <= datalen <= 64:
        return 15
    else:
        return 0
    
def dlcToDataLen(dlc):
    if 0  <= dlc <=  8:
        return dlc
    elif 9:
        return 12
    elif 10:
        return 16
    elif 11:
        return 20
    elif 12:
        return 24
    elif 13:
        return 32
    elif 14:
        return 48
    elif 15:
        return 64
    else:
        return 0
    
def ConvertBaudRateFDtoParams(baudRateFD):
    f_clock_mhz = 0
    nom_brp =0
    nom_tseg1 =0
    nom_tseg2 =0
    nom_sjw =0
    data_brp =0
    data_tseg1  = 0
    data_tseg2 =0
    data_sjw =0
    if(baudRateFD == BaudRateFD.PCAN_BAUDFD_2M):
        f_clock_mhz=20;nom_brp=5;nom_tseg1=2;nom_tseg2=1;nom_sjw=1;data_brp=2;data_tseg1=3;data_tseg2=1;data_sjw=1
    elif(baudRateFD == BaudRateFD.PCAN_BAUDFD_4M):
        f_clock_mhz=40;nom_brp=5;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=7;data_tseg2=2;data_sjw=1
    elif(baudRateFD == BaudRateFD.PCAN_BAUDFD_6M):
        f_clock_mhz=60;nom_brp=5;nom_tseg1=8;nom_tseg2=3;nom_sjw=1;data_brp=2;data_tseg1=3;data_tseg2=1;data_sjw=1
    elif(baudRateFD == BaudRateFD.PCAN_BAUDFD_8M):
        f_clock_mhz=80;nom_brp=10;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=7;data_tseg2=2;data_sjw=1
    elif(baudRateFD == BaudRateFD.PCAN_BAUDFD_10M):
        f_clock_mhz=80;nom_brp=10;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=5;data_tseg2=2;data_sjw=1
    elif(baudRateFD == BaudRateFD.PCAN_BAUDFD_12M):
        f_clock_mhz=60;nom_brp=5;nom_tseg1=8;nom_tseg2=3;nom_sjw=1;data_brp=1;data_tseg1=2;data_tseg2=2;data_sjw=1

    return f_clock_mhz,nom_brp,nom_tseg1,nom_tseg2,nom_sjw,data_brp,data_tseg1,data_tseg2,data_sjw

