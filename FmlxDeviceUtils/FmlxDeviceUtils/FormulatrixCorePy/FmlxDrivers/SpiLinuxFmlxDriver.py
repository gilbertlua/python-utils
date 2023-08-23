import spidev
import ctypes
import threading
try:
    import queue
except ImportError:
    import Queue as queue


class SpiLinuxFmlxDriver():
    #MAX_LEN = 12
    _msgQueues = dict()
    _bytesQueues = []
    _SpiTx = spidev.SpiDev()
    _SpiRx = spidev.SpiDev()
    _SpiLock = threading.Lock()

    _gpioInterop = ctypes.CDLL('libFMLX_SpiWrapper.so')
    _gpioFd = -1
    DriverName = 'SPILinux'
    _dataAvailableEvent = threading.Event() 
    
    def __init__(self, address, speedHz=16000000, hasDataPin=5):
        # it's supposed to be public
        self._ReadTimeout = 500
        self._WriteTimeout = 500
        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600

        self._connected = False
        self._canResetFirmware = False
        self._writeLock = threading.Lock()
        self._hasDataPin = hasDataPin
        self._spiSpeedHz = speedHz

    @property
    def ReadTimeout(self):
        return self._ReadTimeout

    @ReadTimeout.setter
    def ReadTimeout(self, timeout):
        self._ReadTimeout = timeout

    @property
    def WriteTimeout(self):
        return self._WriteTimeout

    @WriteTimeout.setter
    def WriteTimeout(self, timeout):
        self._WriteTimeout = timeout

    @property
    def Connected(self):
        return self._connected

    @property
    def CanResetFirmware(self):
        return self._canResetFirmware

    def __del__(self):
        del SpiLinuxFmlxDriver._msgQueues[self._receiveMessageId]
        if(len(SpiLinuxFmlxDriver._msgQueues) == 0):
            SpiLinuxFmlxDriver._SpiRx.close()
            SpiLinuxFmlxDriver._SpiTx.close()
            
    @property
    def BytesInReadQueue(self):
        pass

    def Open(self, speed):
        pass

    def Write(self, buffer):
        if not self._connected:
            raise Exception('Not Connected!')

        count = len(buffer)
        index = 0
        with self._SpiLock:
            txData = [0] * count
            for i in range(count):
                txData[i] = buffer[i]
            SpiLinuxFmlxDriver._SpiTx.writebytes(buffer)

    def Read(self):
        if not self._connected:
            raise Exception('Not Connected!')
        buf = []
        if not SpiLinuxFmlxDriver._bytesQueues:
            self._dataAvailableEvent.wait(self.ReadTimeout/1000)
        while SpiLinuxFmlxDriver._bytesQueues:
            
            buf.extend(SpiLinuxFmlxDriver._bytesQueues)
            #print(buf)
            SpiLinuxFmlxDriver._bytesQueues*=0
        self._dataAvailableEvent.clear()
        return buf

    def Connect(self):
        SpiLinuxFmlxDriver._msgQueues.update(
            [(self._receiveMessageId, queue.Queue())])
        SpiLinuxFmlxDriver._dataAvailableEvent = threading.Event()
        SpiLinuxFmlxDriver.SpiLock = threading.Lock()
        if SpiLinuxFmlxDriver._gpioFd == -1:
            SpiLinuxFmlxDriver._gpioFd = SpiLinuxFmlxDriver._gpioInterop.GpioInit(ctypes.c_int(self._hasDataPin))
            SpiLinuxFmlxDriver._gpioInterop.GpioSetDir(SpiLinuxFmlxDriver._gpioFd, self._hasDataPin, 0)
            SpiLinuxFmlxDriver._gpioInterop.GpioSetEdge(self._hasDataPin, 1)

        if len(SpiLinuxFmlxDriver._msgQueues) == 1:
            SpiLinuxFmlxDriver._SpiTx.open(0, 0)
            SpiLinuxFmlxDriver._SpiRx.open(0, 1)
            SpiLinuxFmlxDriver._SpiTx.max_speed_hz = self._spiSpeedHz
            SpiLinuxFmlxDriver._SpiRx.max_speed_hz = self._spiSpeedHz

            SpiLinuxFmlxDriver._receiveThreadInstance = threading.Thread(
                target=SpiLinuxFmlxDriver.receiveThread, args=(self,))
            SpiLinuxFmlxDriver._receiveThreadInstance.daemon = True
            SpiLinuxFmlxDriver._receiveThreadInstance.start()
        self._connected = True

    def Disconnect(self):
        del SpiLinuxFmlxDriver._msgQueues[self._receiveMessageId]
        if len(SpiLinuxFmlxDriver._msgQueues) == 0:
            SpiLinuxFmlxDriver._SpiTx.close()
            SpiLinuxFmlxDriver._SpiRx.close()
        self._connected = False
    
    @staticmethod
    def receiveThread(self):
        while len(SpiLinuxFmlxDriver._msgQueues) > 0:
            if SpiLinuxFmlxDriver._gpioInterop.GpioWaitForEdge(SpiLinuxFmlxDriver._gpioFd, 5) != 0:                
                continue
            spiData = SpiLinuxFmlxDriver._SpiRx.readbytes(2)
            dataLen = spiData[0] << 8 | spiData[1]           
            if dataLen > 0:
                receivedData = SpiLinuxFmlxDriver._SpiRx.readbytes(dataLen)
                SpiLinuxFmlxDriver._bytesQueues.extend(receivedData)
                self._dataAvailableEvent.set()
            
