import serial
from queue import Queue
import threading
import math
import FmlxLogger
import logging

class SerialFmlxDriver():
    DriverName = 'Serial'
    VERSION = '1.0.0'
    _msgQueues = dict()
    _dataAvaiableEvent = dict()
    _serialPort = {}
    _portnames = []
    _logger = None

    def __init__(self, portname, log_handler = None):
        self._portname = portname
        self._logger = logging.getLogger('SerialCOM')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('SerialFmlxDriver version : {0}, portname : {1}'.format(SerialFmlxDriver.VERSION,self._portname))

        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        self._dataAvaiableEvent = threading.Event()
        self._msgQueue = Queue()
        self._serialPort = None
        self._writeLock = threading.Lock()


    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._serialPort is not None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._logger.debug('Connecting, portname : {0}'.format(self._portname))
        self._serialPort = serial.Serial(port=self._portname, baudrate=115200,write_timeout=0)
        self._logger.debug('Connect success')
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()

    def Disconnect(self):
        self._logger.debug('Disconnecting, portname : {0}'.format(self._serialPort))
        self._serialPort = None
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()

    def ResetDevice(self):
        raise NotImplementedError('Not Implemented in Serial COM Py!')    

    def Write(self, buffer):
        if(not self.Connected):
            raise Exception('Not Connected!')
        count = len(buffer)
        index = 0
        with self._writeLock:
            while(count > 0):
                writtenCount = self._serialPort.write(bytes(buffer[index:]))
                count -= writtenCount
                index += writtenCount

    def Read(self):
        if(not self.Connected):
            raise Exception('Not Connected!')
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout/1000)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        # if(len(buf)>0):
        #     self._logger.debug('Data Read, data : {0}'.format(buf))                
        self._dataAvaiableEvent.clear()
        return buf

    def receiveThread(self):
        while(self.Connected):
            receivedData = self._serialPort.read()
            if(not receivedData):
                continue
            self._msgQueue.put(int.from_bytes(receivedData, "little"))
            self._dataAvaiableEvent.set()