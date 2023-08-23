import serial
from queue import Queue
import threading
import math
import FmlxLogger
import logging
from FormulatrixCorePy.FmlxDrivers.CanFmlxDriver import CCanSequentialHandler

class SlcanFmlxDriver():
    DriverName = 'SLCAN'
    VERSION = '1.0.0'
    MAX_DLC = 8
    _msgQueues = dict()
    _dataAvaiableEvent = dict()
    _serialPort = {}
    _portnames = []
    _logger = None

    hexStringToInt = dict([ 
        (ord('0'), '0'), 
        (ord('1'), '1'),
        (ord('2'), '2'),
        (ord('3'), '3'),
        (ord('4'), '4'),
        (ord('5'), '5'), 
        (ord('6'), '6'),
        (ord('7'), '7'),
        (ord('8'), '8'),
        (ord('9'), '9'),
        (ord('A'), 'A'),
        (ord('B'), 'B'),
        (ord('C'), 'C'),
        (ord('D'), 'D'),
        (ord('E'), 'E'),
        (ord('F'), 'F')
        ])

    def __init__(self, address, portname,isUsingSequential = False, log_handler = None):
        if(not SlcanFmlxDriver._logger):
            SlcanFmlxDriver._logger = logging.getLogger('SlcanFmlxDriver')
            SlcanFmlxDriver._logger.setLevel(logging.DEBUG)
            if(log_handler):
                SlcanFmlxDriver._logger.addHandler(log_handler)
            SlcanFmlxDriver._logger.info('SlcanFmlxDriver version : {0}, address : {1}, portname : {2}'.format(SlcanFmlxDriver.VERSION,address,portname))
        
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500
        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        
        # SlcanFmlxDriver._portnames += [portname]
        self._portname = portname
        self._connected = False
        self._writeLock = threading.Lock()
        self._isUsingSequential=isUsingSequential
        if(self._isUsingSequential):
            self._txFrameId = 0 # for sequential can frame identification
            self._CanSeqHandler = CCanSequentialHandler()
        else:
            self._CanSeqHandler = None

    def SetLogHandler(self,log_handler):
        SlcanFmlxDriver._logger.addHandler(log_handler)
        if(self._isUsingSequential):
            self._CanSeqHandler.SetLogHandler(log_handler)

    @property
    def Connected(self):
        return self._connected

    def __del__(self):
        del SlcanFmlxDriver._msgQueues[self._receiveMessageId]
        SlcanFmlxDriver._serialPort[self._receiveMessageId].close()

    @property
    def BytesInReadQueue(self):
        return SlcanFmlxDriver._msgQueues[self._receiveMessageId].qsize()

    def Connect(self):
        SlcanFmlxDriver._logger.debug('Connect, portname : {0}, receive filter id : {1}'.format(self._portname,self._receiveMessageId))
        SlcanFmlxDriver._msgQueues.update([(self._receiveMessageId, Queue())])
        SlcanFmlxDriver._dataAvaiableEvent.update([(self._receiveMessageId, threading.Event())])
        if(not self._portname in SlcanFmlxDriver._portnames):
            SlcanFmlxDriver._logger.debug('Connect,Opening ComPort : {0}'.format(self._portname))
            SlcanFmlxDriver._serialPort.update({self._portname : serial.Serial(port=self._portname, baudrate=4000000,write_timeout=0)})
            SlcanFmlxDriver._receiveThreadInstance = threading.Thread(target=SlcanFmlxDriver._receiveThread, args=(self,SlcanFmlxDriver._serialPort[self._portname],self._CanSeqHandler))
            SlcanFmlxDriver._receiveThreadInstance.daemon = True
            SlcanFmlxDriver._receiveThreadInstance.start()
        SlcanFmlxDriver._portnames+=[self._portname]
        self._connected = True

    def Disconnect(self):
        SlcanFmlxDriver._logger.debug('Disconnecting, Address : {0}'.format(self._address))  
        del SlcanFmlxDriver._msgQueues[self._receiveMessageId]
        del SlcanFmlxDriver._dataAvaiableEvent[self._receiveMessageId]
        SlcanFmlxDriver._portnames.remove(self._portname)
        if(not self._portname in SlcanFmlxDriver._portnames):
            SlcanFmlxDriver._logger.debug('Closing SerialPort : {0}'.format(self._portname))
            SlcanFmlxDriver._serialPort[self._portname].close()
            SlcanFmlxDriver._serialPort.pop(self._portname)
        self._connected = False
        del SlcanFmlxDriver._logger[self._address]

    def ResetDevice(self):
        raise NotImplementedError('Not Implemented in {0}'.format(SlcanFmlxDriver.DriverName))

    def Write(self, buffer):
        if(not self._connected):
            raise Exception('Not Connected!')
        
        count = len(buffer)
        index = 0
        SlcanFmlxDriver._logger.debug('Write, buffer : {0}'.format(buffer))
        with self._writeLock:
            if(not self._isUsingSequential):
                while(count > 0):
                    strMsgHeader = 't'
                    strMsgid = '%03x' % self._transmitMessageId
                    dlc = SlcanFmlxDriver.MAX_DLC if count > SlcanFmlxDriver.MAX_DLC else count
                    strMsgDlc = str(dlc)
                    strMsgData = ''
                    SlcanFmlxDriver._logger.debug('Write Can Frame, msgId : {0}, dlc {1}, data :{2}'.format(self._transmitMessageId,dlc,buffer[index:dlc]))
                    for i in range(dlc):
                        strMsgData += '%02x' % buffer[index+i]
                    strMsg = strMsgHeader+strMsgid.upper()+strMsgDlc.upper() + \
                        strMsgData.upper()+'\r'
                    SlcanFmlxDriver._logger.debug('Write Serial, {0}'.format(strMsg[0:-1]))
                    SlcanFmlxDriver._serialPort[self._portname].write(strMsg.encode())
                    count -= dlc
                    index += dlc
            else:
                strMsgHeader = 't'
                strMsgid = '%03x' % self._transmitMessageId
                
                canPayloads = self._CanSeqHandler.ConvertToCanSequentialFrame(buffer,self._txFrameId)
                for canPayload in canPayloads:
                    strMsgDlc = str(len(canPayload))
                    strMsgData = ''
                    SlcanFmlxDriver._logger.debug('Write Can Frame, msgId : {0}, dlc {1}, data :{2}'.format(self._transmitMessageId,len(canPayload),canPayload))
                    for payload in canPayload:
                        strMsgData += '%02x' % payload
                    strMsg = strMsgHeader+strMsgid.upper()+strMsgDlc.upper() + \
                        strMsgData.upper()+'\r'
                    SlcanFmlxDriver._logger.debug('Write Serial, {0}'.format(strMsg[0:-1]))
                    SlcanFmlxDriver._serialPort[self._portname].write(strMsg.encode())    

    def Read(self):
        if not self._connected:
            raise Exception('Not Connected!')
        buf = []
        if(SlcanFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            SlcanFmlxDriver._dataAvaiableEvent[self._receiveMessageId].wait(self.ReadTimeout/1000)
        while(not SlcanFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            buf.append(SlcanFmlxDriver._msgQueues[self._receiveMessageId].get())
        # if(len(buf)>0):
        #     SlcanFmlxDriver._logger.debug('read, msgId : {0} , data : {1}'.format(self._receiveMessageId,buf))
        SlcanFmlxDriver._dataAvaiableEvent[self._receiveMessageId].clear()
        return buf

    @staticmethod
    def _receiveThread(self,serialPort,canSeqHandler):
        while(serialPort.is_open):
            receivedData = serialPort.read_until(bytes([13]))
            SlcanFmlxDriver._logger.debug('Receive Thread, receive data {0}'.format(receivedData))
            if(receivedData[0] == ord('t') or receivedData[0] == ord('T') or receivedData[0] == ord('r') or receivedData[0] == ord('R')):
                msgId = int(''.join(map(lambda x : SlcanFmlxDriver.hexStringToInt[x], receivedData[1:4])), 16)
                if(not msgId in SlcanFmlxDriver._msgQueues):
                    continue 
                dlc = int(''.join(map(lambda x : SlcanFmlxDriver.hexStringToInt[x], receivedData[4:5])), 16)
                data=[]
                for i in range(dlc):
                    data+=[int(''.join(map(lambda x : SlcanFmlxDriver.hexStringToInt[x], receivedData[5+i*2:7+i*2])), 16)]
                if(not canSeqHandler):
                    for i in range(dlc):
                        SlcanFmlxDriver._msgQueues[msgId].put(data[i])
                    SlcanFmlxDriver._dataAvaiableEvent[msgId].set()
                    SlcanFmlxDriver._logger.debug('receive thread, msgId : {0} dlc : {1}, data : {2}'.format(msgId,dlc,list(data)))
                else:
                    canSeqHandler.WriteCANFrame(dlc,data)
                    datas = canSeqHandler.ReadAllData()
                    if(datas == []):
                        continue
                    for data in datas:
                        SlcanFmlxDriver._msgQueues[msgId].put(data)
                    SlcanFmlxDriver._dataAvaiableEvent[msgId].set()
                    