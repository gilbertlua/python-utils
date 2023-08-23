
from logging.handlers import BufferingHandler
from os import stat
import can
from queue import Queue
import threading
import math
import logging
import FmlxLogger
import os
from crc import crc16
import ctypes
import struct

class CanFmlxDriver():
    DriverName = 'Can'
    VERSION = '1.0.0'
    MAX_DLC = 8
    def __init__(self,address,bustype,channel = 0,bitrate = 1000000,log_handler = None):
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._filters = [{"can_id": self._receiveMessageId, "can_mask": 0x7FF, "extended":False}]
        self._msgQueue = Queue()
        self._busType = bustype
        self._channel = channel
        self._bitRate = bitrate
        self._bus = None
        self._dataAvaiableEvent = threading.Event()
        self._receiveThreadInstance = None
        self._logger = logging.getLogger('CorePyCANDriver')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('CorePyCANDriver version : {0}'.format(CanFmlxDriver.VERSION))

    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._bus is not None

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._logger.debug('Connecting, busType : {0}, channel : {1}, bitrate : {2} , receive filter id : {3}'.format(self._busType,self._channel,self._bitRate,self._receiveMessageId))
        self._bus = can.interface.Bus(bustype=self._busType, channel=self._channel, bitrate=self._bitRate,can_filters=self._filters, accept_virtual = True, single_handle  = True)
        self._logger.debug('Connect success')
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        self._logger.debug('Disconnecting, busType : {0}, channel : {1}, bitrate : {2} , receive filter id : {3}'.format(self._busType,self._channel,self._bitRate,self._receiveMessageId))
        self._bus = None
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()

    def ResetDevice(self):
        raise NotImplementedError('Not Implemented in CAN Core Py!')

    def Write(self, buffer):
        count = len(buffer)
        index = 0
        while(count > 0):
            dlc = min(CanFmlxDriver.MAX_DLC,count)
            self._logger.debug('Writing, index : {0}, count : {1}, msgId : {2}, dlc : {3}, data : {4}'.format(index,count,self._transmitMessageId,dlc,buffer[index:index+dlc],buffer))
            try:
                self._bus.send(can.Message(data = buffer[index:index+dlc],is_extended_id=False,arbitration_id=self._transmitMessageId))
            except can.CanError:
                self._logger.exception(can.CanError)
                raise can.CanError
            count -= dlc
            index += dlc

    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout/1000)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        # if(len(buf)>0):
        #     self._logger.debug('Data Read, msgId : {0}, len : {1}, data : {2}'.format(self._receiveMessageId,len(buf),buf))        
            
        self._dataAvaiableEvent.clear()
        return buf
        
    def receiveThread(self):
        while(self.Connected):
            receivedData = self._bus.recv(1)
            if(not receivedData):
                continue
            self._logger.debug('Data Received,ts :{0}, msgId : {1}, dlc : {2}, data : {3}, is error frame :{4}'.format(receivedData.timestamp,self._receiveMessageId,receivedData.dlc,list(map(int,receivedData.data)),receivedData.is_error_frame))        
            if(receivedData.is_error_frame):
                continue
            for data in list(receivedData.data):
                self._msgQueue.put(data)
            #print(receivedData)
            self._dataAvaiableEvent.set()

# in this can fd driver, we currently only support 1mbps nominal bit rate but flexible data bit rate         
class CanFdFmlxDriver():
    DriverName = 'CanFd'
    MAX_DATALEN = 64
    VERSION = '1.0.0'
    class BaudRateFD():
        PCAN_BAUDFD_2M = 0,
        PCAN_BAUDFD_4M = 1,
        PCAN_BAUDFD_6M = 2,
        PCAN_BAUDFD_8M = 3,
        PCAN_BAUDFD_10M = 4,
        PCAN_BAUDFD_12M = 5
    
    def __init__(self,address,bustype,channel = 0,baudRateFd = BaudRateFD.PCAN_BAUDFD_2M,isUsingBRS = False,log_handler = None):
        self._logger = logging.getLogger('CorePyCANFDDriver_{0}'.format(bustype))
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('CorePyCANDriver version : {0}'.format(CanFmlxDriver.VERSION))
        self._logger.debug('address : {0}, busType : {1}, channel {2}, baudRateFD : {3}, isUsingBRS : {4}'.format(address,bustype,channel,baudRateFd,isUsingBRS))
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500
        
        # then below is private
        self._baudRateFd = baudRateFd
        self._isUsingBRS = isUsingBRS
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._filters = [{"can_id": self._receiveMessageId, "can_mask": 0x7FF, "extended":False}]
        self._msgQueue = Queue()
        self._busType = bustype
        self._channel = channel
        self._bus = None
        self._dataAvaiableEvent = threading.Event()
        self._receiveThreadInstance = None

    def SetLoghandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._bus is not None

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        f_clock_mhz,nom_brp,nom_tseg1,nom_tseg2,nom_sjw,data_brp,data_tseg1,data_tseg2,data_sjw = self.ConvertBaudRateFDtoParams(self._baudRateFd)
        self._logger.debug('Connecting..')
        self._bus = can.interface.Bus(bustype=self._busType, channel=self._channel,can_filters=self._filters,fd = True, accept_virtual = True, single_handle  = True,f_clock_mhz=f_clock_mhz,nom_brp=nom_brp,nom_tseg1=nom_tseg1,nom_tseg2=nom_tseg2,nom_sjw=nom_sjw,data_brp=data_brp,data_tseg1=data_tseg1,data_tseg2=data_tseg2,data_sjw=data_sjw)
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        self._bus = None
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()

    def ResetDevice(self):
        return

    def Write(self, buffer):
        count = len(buffer)
        index = 0
        while(count > 0):
            datalen = min(CanFdFmlxDriver.MAX_DATALEN,count)
            dlc = self.dataLenToDlc(datalen)
            bufferSend = [datalen]
            bufferSend+=buffer[index:index+datalen]
            self._logger.debug('Writing, index : {0}, count : {1}, msgId : {2}, dataLen {3} , dlc : {4}, data : {5}'.format(index,count,self._transmitMessageId,datalen,dlc,bufferSend))
            
            self._bus.send(can.Message(data = bufferSend,is_extended_id=False,arbitration_id=self._transmitMessageId,is_fd=True,bitrate_switch=self._isUsingBRS))
            count -= datalen
            index += datalen

    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout/1000)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        self._dataAvaiableEvent.clear()
        return buf
        
    def receiveThread(self):
        while(self.Connected):
            receivedData = self._bus.recv(1)
            if(not receivedData):
                continue
            self._logger.debug('Data Received,ts : {0}, msgId : {1}, dlc : {2}, data : {3}'.format(receivedData.timestamp,self._receiveMessageId,receivedData.dlc,list(map(int,receivedData.data))))        
            for index in range(receivedData.data[0]):
                self._msgQueue.put(receivedData.data[index+1])
            self._dataAvaiableEvent.set()

    def dataLenToDlc(self,datalen):
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
        
    def ConvertBaudRateFDtoParams(self,baudRateFD):
        f_clock_mhz = 0
        nom_brp =0
        nom_tseg1 =0
        nom_tseg2 =0
        nom_sjw =0
        data_brp =0
        data_tseg1  = 0
        data_tseg2 =0
        data_sjw =0
        if(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_2M):
            f_clock_mhz=20;nom_brp=5;nom_tseg1=2;nom_tseg2=1;nom_sjw=1;data_brp=2;data_tseg1=3;data_tseg2=1;data_sjw=1
        elif(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_4M):
            f_clock_mhz=40;nom_brp=5;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=7;data_tseg2=2;data_sjw=1
        elif(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_6M):
            f_clock_mhz=60;nom_brp=5;nom_tseg1=8;nom_tseg2=3;nom_sjw=1;data_brp=2;data_tseg1=3;data_tseg2=1;data_sjw=1
        elif(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_8M):
            f_clock_mhz=80;nom_brp=10;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=7;data_tseg2=2;data_sjw=1
        elif(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_10M):
            f_clock_mhz=80;nom_brp=10;nom_tseg1=5;nom_tseg2=2;nom_sjw=1;data_brp=1;data_tseg1=5;data_tseg2=2;data_sjw=1
        elif(baudRateFD == CanFdFmlxDriver.BaudRateFD.PCAN_BAUDFD_12M):
            f_clock_mhz=60;nom_brp=5;nom_tseg1=8;nom_tseg2=3;nom_sjw=1;data_brp=1;data_tseg1=2;data_tseg2=2;data_sjw=1

        return f_clock_mhz,nom_brp,nom_tseg1,nom_tseg2,nom_sjw,data_brp,data_tseg1,data_tseg2,data_sjw
    
class CanSequentialFmlxDriver():
    DriverName = 'CanSequential'
    MAX_DLC = 8
    def __init__(self,address,bustype,channel = 0,bitrate = 1000000,log_handler = None,isOld = False):
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._filters = [{"can_id": self._receiveMessageId, "can_mask": 0x7FF, "extended":False}]
        self._msgQueue = Queue()
        self._busType = bustype
        self._channel = channel
        self._bitRate = bitrate
        self._bus = None
        self._dataAvaiableEvent = threading.Event()
        self._receiveThreadInstance = None
        
        self._txFrameId = 0 # for sequential can frame identification
        self._CanSeqHandler = CCanSequentialHandler(isOld=isOld)
        self._logger = logging.getLogger('CorePyCANSequentialDriver')

    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._bus is not None

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._bus = can.interface.Bus(bustype=self._busType, channel=self._channel, bitrate=self._bitRate,can_filters=self._filters, accept_virtual = True, single_handle  = True)
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        self._bus = None
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()

    def ResetDevice(self):
        return

    def Write(self, buffer):
        if(not self.Connected):
            raise Exception('Not Connected!')
        count = len(buffer)
        index = 0
        seqId = 0
        sendData = []
        canPayloads = self._CanSeqHandler.ConvertToCanSequentialFrame(buffer,self._txFrameId)
        for canPayload in canPayloads:
            self._bus.send(can.Message(data = canPayload,is_extended_id=False,arbitration_id=self._transmitMessageId))
            # PCanFmlxDriver._Buses[self._channel].send(can.Message(data = canPayload,is_extended_id=False,arbitration_id=self._transmitMessageId,is_fd=True,bitrate_switch=self._isUsingBRS))
    
    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        self._dataAvaiableEvent.clear()
        return buf
        
    def receiveThread(self):
        while(self.Connected):
            receivedData = self._bus.recv(1)
            if(not receivedData):
                continue
            # print('recv thrd',list(receivedData.data))
            frameId = self._CanSeqHandler.WriteCANFrame(receivedData.dlc,receivedData.data)
            if(frameId<0):
                continue
            datas = self._CanSeqHandler.ReadAllData(frameId)
            if(datas == []):
                continue
            #print(datas)
            for data in datas:
                self._msgQueue.put(data)
            self._dataAvaiableEvent.set()

class CanFdSequentialFmlxDriver():
    DriverName = 'CanFdSequential'
    MAX_DLC = 8
    def __init__(self,address,bustype,channel = 0,bitrate = 1000000,log_handler = None):
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._filters = [{"can_id": self._receiveMessageId, "can_mask": 0x7FF, "extended":False}]
        self._msgQueue = Queue()
        self._busType = bustype
        self._channel = channel
        self._bitRate = bitrate
        self._bus = None
        self._dataAvaiableEvent = threading.Event()
        self._receiveThreadInstance = None
        
        self._txFrameId = 0 # for sequential can frame identification
        self._CanSeqHandler = CCanSequentialHandler()

    @property
    def Connected(self):
        return self._bus is not None

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._bus = can.interface.Bus(bustype=self._busType, channel=self._channel, bitrate=self._bitRate,can_filters=self._filters, accept_virtual = True, single_handle  = True)
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        self._bus = None
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()

    def ResetDevice(self):
        return

    def Write(self, buffer):
        if(not self.Connected):
            raise Exception('Not Connected!')
        count = len(buffer)
        index = 0
        seqId = 0
        sendData = []
        while(count > 0):
            data=[]
            if(seqId==0):
                numDataSent = min(4, count)
            else:
                numDataSent = min(7, count)
            data.append((self._txFrameId << 7) | (seqId & 0x7f))
            # data.append(seqId)
            dlc = 2 # adding frame Id and seq id 2 bytes
            if( seqId == 0): # header
                if(count > 4):
                    data.append(math.ceil(( count - 4 ) / 7)) # expected frame count
                elif(count <=4):
                    data.append(0) # expected frame count
                data.append(( count >> 8 ) & 0xff) # expected data count LSB
                data.append(count & 0xff) # expected data count MSB
                for buf in buffer[index:index+numDataSent]:
                    data.append(buf)
                dlc += 3 + numDataSent
            else: # 
                for buf in buffer[index:index+numDataSent]:
                    data.append(buf)
                dlc += numDataSent
            # print(data,buffer[index:index+dlc])
            self._bus.send(can.Message(data = data,is_extended_id=False,arbitration_id=self._transmitMessageId))
            # sendData.append(data)
            seqId+=1
            count -= numDataSent
            index += numDataSent
        # print(sendData)
        # print(reversed(sendData))
        # for data in reversed(sendData):
        #     self._bus.send(can.Message(data = data,is_extended_id=False,arbitration_id=self._transmitMessageId))
        # self._txFrameId = ( self._txFrameId + 1 ) % 4; # rolling frame id
    
    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout/1000)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        self._dataAvaiableEvent.clear()
        return buf
        
    def receiveThread(self):
        while(self.Connected):
            receivedData = self._bus.recv(1)
            if(not receivedData):
                continue
            # print('recv thrd',list(receivedData.data))
            self._CanSeqHandler.WriteCANFrame(receivedData.dlc,receivedData.data)
            datas = self._CanSeqHandler.ReadAllData()
            if(datas == []):
                continue
            #print(datas)
            for data in datas:
                self._msgQueue.put(data)
            self._dataAvaiableEvent.set()

class CCanSequentialHandler():
    MAX_CAN_FRAME = 1

    def __init__(self,log_handler=None,syncPeriodSeconds = 0.5,isOld = False):
        self._CanFrames=[]
        self._canFramingSyncThreadInstance=[]
        self._CanFramingAvaiableDataEvent=[]
        self._CanReadLock = []
        self._isRunning = True
        self._syncPeriodSeconds = syncPeriodSeconds
        self._isOld = isOld
        for i in range(CCanSequentialHandler.MAX_CAN_FRAME + 1):
            self._CanFrames+=[SCanSequentialFrame(isOld=self._isOld)]
            self._CanFramingAvaiableDataEvent+=[threading.Event()]
            self._canFramingSyncThreadInstance+=[threading.Thread(target=self.canFramingSyncThread, args=(i,))]
            self._CanReadLock += [threading.Lock()]
            self._canFramingSyncThreadInstance[i].daemon = True
            self._canFramingSyncThreadInstance[i].start()
        self._logger = logging.getLogger('CanSequentialHandler')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)

    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    def __del__(self):
        self._isRunning = False
        
    def WriteCANFrame(self,dlc, pData):
        self._logger.debug('WriteCanFrame, dlc : {0}, data : {1}'.format(dlc,pData))
        if ( dlc > 8 ): 
            return -1
        if ( dlc == 0 ): 
            return -1
        frameId = (pData[0] >> 7) & 1
        seqId = pData[0] & 0x7f
        dlc -= 1; # minus the frame and seqId bytes
        
        if ( seqId >= 76 ):
            return -1
        if ( frameId > CCanSequentialHandler.MAX_CAN_FRAME ):
            return -1
        self._CanFramingAvaiableDataEvent[frameId].set()
        with self._CanReadLock[frameId]:
            if ( seqId == 0 ):
                self._CanFrames[frameId].IsHeaderReceived = True
                self._CanFrames[frameId].TotalExpectedFrame = pData[1]
                self._CanFrames[frameId].TotalExpectedData = pData[2] << 8 | pData[3]
                dlc -= 3; # minus expected frame and data bytes
                self._CanFrames[frameId].TotalReceivedFrame = 0
                self._CanFrames[frameId].TotalReceivedData = dlc
                self._CanFrames[frameId].payload[seqId] = pData[4:].copy()
                for i in range(1,self._CanFrames[frameId].TotalExpectedFrame + 1):
                    if ( len(self._CanFrames[frameId].payload[i]) ):
                        self._CanFrames[frameId].TotalReceivedData += len(self._CanFrames[frameId].payload[i])
                        self._CanFrames[frameId].TotalReceivedFrame+=1
                self._logger.debug('WriteCanFrame,header, frame id : {0}, seq id : {1} , totalExpectedFrame : {2}, totalExpectedData : {3} , payload : {4}'.format(frameId,seqId,self._CanFrames[frameId].TotalExpectedFrame,self._CanFrames[frameId].TotalExpectedData,self._CanFrames[frameId].payload[seqId]))
            else:
                if(self._CanFrames[frameId].IsHeaderReceived and seqId > self._CanFrames[frameId].TotalExpectedFrame):
                    return -1
                if(len(self._CanFrames[frameId].payload[seqId]) == 0):
                    self._CanFrames[frameId].TotalReceivedFrame += 1
                    self._CanFrames[frameId].TotalReceivedData+=dlc
                else:
                    self._CanFrames[frameId].TotalReceivedData+=dlc - len(self._CanFrames[frameId].payload[seqId])
                self._CanFrames[frameId].payload[seqId] = pData[1:].copy()

                self._logger.debug('WriteCanFrame,payload, frame id : {0}, seq id : {1} , payload : {2}'.format(frameId,seqId,self._CanFrames[frameId].payload[seqId]))
        return frameId

    def ConvertToCanSequentialFrame(self,buffer,txFrameId):
        self._logger.debug('Converting to can Sequential frame, txFrameId : {0}, datacount : {1}, data : {2}'.format(txFrameId,len(buffer),buffer))
        count = len(buffer)
        dataSendIndex = 0
        remainingData = count + 2
        seqId = 0
        canPayloads = []
        if(not self._isOld):
            crc = crc16(buffer)
            buffer+= [(crc >> 8) & 0xff]
            buffer+= [crc & 0xff]
        self._logger.debug('crc : {0},{1}'.format(buffer[-2],buffer[-1]))
        while(remainingData > 0):
            numDataSent = min( 4 if seqId == 0 else 7 , remainingData)
            self._logger.debug('dataSendIndex : {0}, numDataSent : {1}, buffer : {2}'.format(dataSendIndex,numDataSent,buffer[dataSendIndex:dataSendIndex+numDataSent]))
            canPayload=[(txFrameId << 7) | (seqId & 0x7f)]
            if(seqId==0): # header
                if(count+2>4):
                    if (((count + 2 - 4) % 7) != 0):
                        canPayload.append(1)
                        canPayload[1]+=((count + 2 - 4) // 7) # expected frame count
                    else:
                        canPayload+= [((count + 2 - 4) // 7)] # expected frame count
                canPayload.append((count >> 8) & 0xff) # expected data count MSB
                canPayload.append(count & 0xff) # expected data count LSB
                
                canPayload+=buffer[dataSendIndex:dataSendIndex+numDataSent]
                totalExpectedFrame = ((count + 2 - 4) // 7)
                totalExpectedData = count
                self._logger.debug('ConvertCanSequential,Header,txFrameId : {0}, seqId : {1}, totalExpectedFrame :{2}, TotalExpectedData :{3}, Payload : {4} '.format(txFrameId,seqId,totalExpectedFrame,totalExpectedData,canPayload))
            
            else: #payload
                canPayload+=buffer[dataSendIndex:dataSendIndex+numDataSent]
                self._logger.debug('ConvertCanSequential,Payload,txFrameId : {0}, seqId : {1}, Payload : {2} '.format(txFrameId,seqId,canPayload))
            
            canPayloads.append(canPayload)
            seqId+=1
            remainingData -= numDataSent
            dataSendIndex += numDataSent

        return canPayloads

    def ReadAllData(self,frameId):
        pData = []
        with self._CanReadLock[frameId]:
            if(not self._CanFrames[frameId].IsComplete(frameId,self._logger)):
                return pData
            
            self._logger.debug('frame complete, index : {0}'.format(frameId))
            for payloadIndex in range(1+self._CanFrames[frameId].TotalReceivedFrame):
                for data in self._CanFrames[frameId].payload[payloadIndex]:
                    pData.append(data)    

            self._CanFrames[frameId].TotalExpectedFrame = 0
            self._CanFrames[frameId].TotalExpectedData = 0
            self._CanFrames[frameId].TotalReceivedFrame = 0
            self._CanFrames[frameId].TotalReceivedData = 0
            self._CanFrames[frameId].IsHeaderReceived = False
            for payload in self._CanFrames[frameId].payload:
                payload.clear()
            if(self._isOld):
                return pData
            else:
                return pData[:-2]

    def Purge(self,frameIndex):
        if(self._CanFrames[frameIndex].TotalExpectedFrame == 0 and self._CanFrames[frameIndex].TotalExpectedData == 0 and self._CanFrames[frameIndex].TotalReceivedFrame == 0 and self._CanFrames[frameIndex].TotalReceivedData == 0):
            return
        self._logger.debug('purging frame index : {0}'.format(frameIndex))
        with self._CanReadLock[frameIndex]:
            self._CanFrames[frameIndex].TotalExpectedFrame = 0
            self._CanFrames[frameIndex].TotalExpectedData = 0
            self._CanFrames[frameIndex].TotalReceivedFrame = 0
            self._CanFrames[frameIndex].TotalReceivedData = 0
            self._CanFrames[frameIndex].IsHeaderReceived = False
            for payload in self._CanFrames[frameIndex].payload:
                payload.clear()

    def canFramingSyncThread(self,frameIndex):
        while(self._isRunning):
            isCanFrameAvaiable = self._CanFramingAvaiableDataEvent[frameIndex].wait(self._syncPeriodSeconds)  
            if(not isCanFrameAvaiable):
                self.Purge(frameIndex)
            self._CanFramingAvaiableDataEvent[frameIndex].clear()

class SCanSequentialFrame():
    def __init__(self,isFd=False,isOld = False):
        self._isOld = isOld
        self.TotalExpectedFrame = 0
        self.TotalExpectedData = 0
        self.TotalReceivedFrame = 0
        self.TotalReceivedData = 0
        self.IsHeaderReceived = False
        self.payload = []
        if(not isFd):
            for i in range(76):
                self.payload.append([])
        else:
            for i in range(10):
                self.payload.append([])


    def IsComplete(self,index = None, logger = None):
        if(index!=None and logger):
            logger.debug('Is Complete?, canFrameIndex : {0},  TotalReceivedFrame : {1} , TotalExpectedFrame : {2} , TotalReceivedData : {3}, TotalExpectedData {4}'.format(index,self.TotalReceivedFrame,self.TotalExpectedFrame,self.TotalReceivedData,self.TotalExpectedData))       
                
        if ( not self.IsHeaderReceived ):
            return False
        
        if ( self.TotalReceivedFrame != self.TotalExpectedFrame ):
            return False
        if(not self._isOld):
            if( self.TotalReceivedData-2 != self.TotalExpectedData ):
                return False
        else:
            if( self.TotalReceivedData != self.TotalExpectedData ):
                return False
            return True

        # calculate checksum
        buffer = []
        for dataIdx in range(self.TotalReceivedFrame+1):
            buffer+=self.payload[dataIdx]
        calculatedCrc = crc16(buffer[:-2])
        packetCrc = (buffer[self.TotalReceivedData-2] << 8) | buffer[self.TotalReceivedData-1] #struct.unpack('H', bytearray(buffer[-2:]))[0]
        if(index!=None  and logger):
            logger.debug('checksum check, canFrameIndex : {0},  calculatedCrc : {1} , packetCrc : {2}, result : {3}'.format(index,calculatedCrc,packetCrc,calculatedCrc==packetCrc))       
        
        return calculatedCrc == packetCrc
