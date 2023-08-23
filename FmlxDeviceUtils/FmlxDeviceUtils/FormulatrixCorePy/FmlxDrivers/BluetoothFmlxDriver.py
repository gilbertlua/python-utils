import bluetooth
import logging
import threading
from queue import Queue

class BluetoothRFCommClientFmlxDriver():
    DriverName = 'BluetoothRFCommClient'
    VERSION = '1.0.0'

    def __init__(self,macAddress,port = 1,log_handler = None):
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500
        self._msgQueue = Queue()
        self._macAddress = macAddress
        self._port = port
        self._logger = logging.getLogger('BluetoothRFComm')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('BluetoothRFComm version : {0}'.format(BluetoothRFCommClientFmlxDriver.VERSION))
        self._btSocket = None
        self._dataAvaiableEvent = threading.Event()
        self._receiveThreadInstance = None
        self._transmitLock = threading.Lock()

    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._btSocket is not None

    def __del__(self):
        # self._btSocket.close()
        self._btSocket = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._btSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self._logger.debug('Connecting, macAddress: {0}, port : {1}'.format(self._macAddress,self._port))
        self._btSocket.connect((self._macAddress, self._port))
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
        raise NotImplementedError()

    def Write(self, buffer):
        with self._transmitLock:
            self._btSocket.send(bytes(buffer))
       
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
            receivedData = self._btSocket.recv(1024)
            if(not receivedData):
                continue
            self._logger.debug('Data Received, data : {0}'.format(receivedData))        
            for data in list(receivedData):
                self._msgQueue.put(data)
            #print(receivedData)
            self._dataAvaiableEvent.set()

def Scan():
    print('Scanning for bluetooth devices... ')
    devices = bluetooth.discover_devices(lookup_names = True, lookup_class = True)
    number_of_devices = len(devices)
    index = 1
    print(number_of_devices,"devices found")
    for addr, name, device_class in devices:
        print("{0}.Name : {1}, MAC : {2}, Class : {3}".format(index,name,addr,device_class))
        index+=1
    return devices