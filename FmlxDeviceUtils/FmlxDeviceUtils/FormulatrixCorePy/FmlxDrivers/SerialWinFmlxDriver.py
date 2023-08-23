import serial
from queue import Queue
from collections import deque

import threading

class SerialWinFmlxDriver():
    DriverName = 'USBToSerial'
    MAX_DLC = 8
    _msgQueues = dict()
    _serialBuffer = deque()
    _serialPort = {}
    _portNames = []
    _bytesQueue = []

    
    _flowControl = dict([
        ('none', 0),
        ('rtscts', 256),
        ('dtrdsr', 512),
        ('xonxoff', 1024)
    ])

    def __init__(self, address, portname):
        # it's supposed to be public
        self._ReadTimeout = 500
        self._WriteTimeout = 500
        # then below is private
        self._address = address
        self._receiveMessageId = address + 0x580
        self._transmitMessageId = address + 0x600

        self._portName = portname
        self._connected = False
        self._canResetFirmware = False
        self._readwriteLock = threading.Lock()
        self._dataAvailableEvent = threading.Event()

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
        del SerialWinFmlxDriver._msgQueues[self._receiveMessageId]
        self._serialPort[self._portName].close()

    @property
    def BytesInReadQueue(self):
        return SerialWinFmlxDriver._msgQueues[self._receiveMessageId].qsize()

    def Connect(self):
        SerialWinFmlxDriver._msgQueues.update([(self._receiveMessageId, Queue())])
        if not self._portName in SerialWinFmlxDriver._portNames:

            SerialWinFmlxDriver._portNames+=[self._portName]
            SerialWinFmlxDriver._serialPort.update({self._portName: serial.Serial(port=self._portName, baudrate=115200,
                                                                                  bytesize=8, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,xonxoff=False,rtscts=False,dsrdtr=False,write_timeout=0)})
            if not SerialWinFmlxDriver._serialPort[self._portName].is_open:
                SerialWinFmlxDriver._serialPort[self._portName].open()
            SerialWinFmlxDriver._receiveThreadInstance = threading.Thread(target=SerialWinFmlxDriver._receiveThread,
                                                                          args=(self, SerialWinFmlxDriver._serialPort[self._portName]))
            SerialWinFmlxDriver._receiveThreadInstance.daemon = True
            SerialWinFmlxDriver._receiveThreadInstance.start()
        self._connected = True

    def Disconnect(self):
        SerialWinFmlxDriver._portNames.remove(self._portName)
        if not self._portName in SerialWinFmlxDriver._portNames:
            SerialWinFmlxDriver._serialPort[self._portName].close()
            SerialWinFmlxDriver._serialPort.pop(self._portName)
        self._connected = False

    @staticmethod
    def _receiveThread(self, serialPort):
        while serialPort.is_open:
            byteWaiting = serialPort.inWaiting()
            if byteWaiting:
                receivedData = serialPort.read(byteWaiting)
                SerialWinFmlxDriver._bytesQueue.extend(receivedData)
                self._dataAvailableEvent.set()

    def GetBytesInQueues(self):
        count = 0
        with self._readwriteLock:
            count = SerialWinFmlxDriver._serialPort[self._portName].inWaiting()
        return count

    def Read(self):
        if not self._connected:
            raise Exception('Not Connected!')
        buf = []
        if not SerialWinFmlxDriver._bytesQueue:
            self._dataAvailableEvent.wait(self._ReadTimeout/1000)
        while SerialWinFmlxDriver._bytesQueue:
            buf.extend(SerialWinFmlxDriver._bytesQueue)
            SerialWinFmlxDriver._bytesQueue *= 0
        self._dataAvailableEvent.clear()
        return buf

    def Write(self, buffer):        
        if not self._connected :
            raise Exception('Not Connected!')
        count = len(buffer)
        with self._readwriteLock:
            if count > 0:
                SerialWinFmlxDriver._serialPort[self._portName].write(buffer)


def GetSerialPort(auto_choose = False):
    import serial.tools.list_ports   # import serial module
    comPorts = list(serial.tools.list_ports.comports())    # get list of all devices connected through serial port
    if len(comPorts) == 0:
        raise OSError('No COM port found!')
    else:
        for i in range(len(comPorts)):
            print(i+1, '.', comPorts[i].description)
        if auto_choose is False or len(comPorts) > 2:
            choose = input(': ')
        else:
            # choose the only one if there was only one
            if len(comPorts) == 1:
                choose = 1
            # choose the bigger one if there are 2 comport detected
            elif len(comPorts) == 2:
                comPortString = [str(comPorts[0]).split()[0], str(comPorts[1]).split()[0]]
                selected_comPort = comPortString[0] if int(comPortString[0][3:]) > int(comPortString[1][3:]) else  comPortString[1]
                print('selected Comport : {0}'.format(selected_comPort))
                return selected_comPort
        serial_port_string = str(comPorts[int(choose)-1]).split()[0]
    return serial_port_string
