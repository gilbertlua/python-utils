import spidev
import ctypes
try:
    import queue
except ImportError:
    import Queue as queue
import threading

class SPI2CANFmlxDriver():
    MAX_DLC = 8
    _msgQueues = dict()
    _dataAvaiableEvent = dict()
    _serialPort = None
    _portnames = []
    _SpiTx = spidev.SpiDev()
    _SpiRx = spidev.SpiDev()
    _SpiLock = threading.Lock()
    _gpioInterop = ctypes.CDLL('libFMLX_SpiWrapper.so')
    _gpioFd = -1

    DriverName = 'SPI2CAN'
    def __init__(self, address, speedHz=16000000, hasDataPin=1):
        # it's supposed to be public
        self.ReadTimeout = 500
        self.WriteTimeout = 500

        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600
        self._hasDataPin = hasDataPin
        self._spiSpeedHz = speedHz
        self._connected = False
        self._writeLock = threading.Lock()

    @property
    def Connected(self):
        return self._connected

    def __del__(self):
        del SPI2CANFmlxDriver._msgQueues[self._receiveMessageId]
        if(len(SPI2CANFmlxDriver._msgQueues) == 0):
            SPI2CANFmlxDriver._SpiRx.close()
            SPI2CANFmlxDriver._SpiTx.close()
    @property
    def BytesInReadQueue(self):
        return SPI2CANFmlxDriver._msgQueues[self._receiveMessageId].qsize()

    def Connect(self):
        SPI2CANFmlxDriver._msgQueues.update(
            [(self._receiveMessageId, queue.Queue())])
        SPI2CANFmlxDriver._dataAvaiableEvent.update(
            [(self._receiveMessageId, threading.Event())])

        if(SPI2CANFmlxDriver._gpioFd == -1):
            SPI2CANFmlxDriver._gpioFd  = SPI2CANFmlxDriver._gpioInterop.GpioInit(ctypes.c_int(self._hasDataPin))
            SPI2CANFmlxDriver._gpioInterop.GpioSetDir(SPI2CANFmlxDriver._gpioFd,self._hasDataPin,0)
            SPI2CANFmlxDriver._gpioInterop.GpioSetEdge(self._hasDataPin,1)
        if(len(SPI2CANFmlxDriver._msgQueues) == 1):
            SPI2CANFmlxDriver._SpiTx.open(0, 0)
            SPI2CANFmlxDriver._SpiRx.open(0, 1)
            SPI2CANFmlxDriver._SpiTx.max_speed_hz = self._spiSpeedHz
            SPI2CANFmlxDriver._SpiRx.max_speed_hz = self._spiSpeedHz

            SPI2CANFmlxDriver._receiveThreadInstance = threading.Thread(
                target=SPI2CANFmlxDriver.receiveThread, args=(self,))
            SPI2CANFmlxDriver._receiveThreadInstance.daemon = True
            SPI2CANFmlxDriver._receiveThreadInstance.start()
        self._connected = True

    def Disconnect(self):
        del SPI2CANFmlxDriver._msgQueues[self._receiveMessageId]
        del SPI2CANFmlxDriver._dataAvaiableEvent[self._receiveMessageId]
        if(len(SPI2CANFmlxDriver._msgQueues) == 0):
            SPI2CANFmlxDriver.SpiTx.close()
            SPI2CANFmlxDriver.SpiRx.close()
        self._connected = False

    def ResetDevice(self):
        raise NotImplementedError('Not Implemented On {0}'.format(SPI2CANFmlxDriver.DriverName))

    def Write(self, buffer):
        if(not self._connected):
            raise Exception('Not Connected!')

        count = len(buffer)
        index = 0
        with self._writeLock:
            while(count > 0):
                txData = [0] * 12
                txData[0] = ord('t')
                txData[1] = self._transmitMessageId & 0xff
                txData[2] = ( self._transmitMessageId >> 8 ) & 0xff
                dlc = min(SPI2CANFmlxDriver.MAX_DLC,count)
                txData[3] = dlc
                for i in range(dlc):
                    txData[4+i] = buffer[index+i]
                SPI2CANFmlxDriver._SpiTx.writebytes(txData)
                count -= dlc
                index += dlc

    def Read(self):
        if(not self._connected):
            raise Exception('Not Connected!')
        buf = []
        if(SPI2CANFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            SPI2CANFmlxDriver._dataAvaiableEvent[self._receiveMessageId].wait(self.ReadTimeout/1000)
        while(not SPI2CANFmlxDriver._msgQueues[self._receiveMessageId].empty()):
            buf.append(
                SPI2CANFmlxDriver._msgQueues[self._receiveMessageId].get())
        SPI2CANFmlxDriver._dataAvaiableEvent[self._receiveMessageId].clear()
        return buf

    def SpiTransfer(self, buffers=None, size=12):
        with SPI2CANFmlxDriver._SpiLock:
            if(buffers):
                SPI2CANFmlxDriver._SpiTx.writebytes(buffers)
            else:
                return SPI2CANFmlxDriver._SpiRx.readbytes(size)

    @staticmethod
    def receiveThread(self):
        while(len(SPI2CANFmlxDriver._msgQueues) > 0):
            if(SPI2CANFmlxDriver._gpioInterop.GpioWaitForEdge(SPI2CANFmlxDriver._gpioFd,1)!=0):
                continue
            receivedData = SPI2CANFmlxDriver._SpiRx.readbytes(12)
            if(receivedData[0] == ord('t')):
                dlc = receivedData[3]
                if(dlc > SPI2CANFmlxDriver.MAX_DLC):
                    print('WARNING, invalid DLC : {0}'.format(dlc))
                    continue
                msgId = receivedData[2] << 8 | receivedData[1]
                if(not msgId in SPI2CANFmlxDriver._msgQueues):
                    continue
                for i in range(dlc):
                    SPI2CANFmlxDriver._msgQueues[msgId].put(receivedData[4 + i])
                SPI2CANFmlxDriver._dataAvaiableEvent[msgId].set()
