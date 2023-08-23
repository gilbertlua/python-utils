import serial
from queue import Queue
import threading
import argparse

from FmlxDeviceConnector import FmlxDeviceConnectorSingle

# for python script integration
class SerialCANBridge():
    
    def __init__(self,fmlxDriver,readTimeout = 0.5):
        self._driver = fmlxDriver
        self._dataAvaiableEvent=threading.Event()
        self._msgQueue = Queue()
        self.ReadTimeout = readTimeout
        self._connected = True
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()
        
    def Write(self,buffer):
        if(type(buffer)==str):
            buffer = list(map(ord,buffer))
            self._driver.Write(buffer)
        elif(type(buffer)==list):
            self._driver.Write(buffer)

    def Read(self):
        buf = []
        if(self._msgQueue.empty()):
            self._dataAvaiableEvent.wait(self.ReadTimeout)  
        while(not self._msgQueue.empty()):
            buf.append(self._msgQueue.get())
        self._dataAvaiableEvent.clear()
        return buf

    def ReadString(self):
        return self.ListToString(self.Read())

    def ListToString(self,data):
        return ''.join(list(map(chr,data)))

    def receiveThread(self):
        while(self._connected):
            try:
                receivedData = self._driver.Read()
            except TypeError:
                try:
                    receivedData = self._driver.Read(1)
                except:
                    continue
            for data in receivedData:
                self._msgQueue.put(data)
            self._dataAvaiableEvent.set()

    def __del__(self):
        self._connected = False

# for background task for serial can bridge
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serial CAN Bridge Daemon")
    parser.add_argument('-d', '--driverName', help="fmlx driver name", type=str)
    parser.add_argument('-c', '--comPort', help="comport driver if we choose fvaser as the driver", type=str)
    parser.add_argument('-a','--address',help="fmlx address", nargs='+', type=str)
    parser.add_argument('-v', '--virtualComPort', help="virtual com port number", type=str)
    parser.add_argument('-s', '--showLog', help="show the traffic into the console", action='store_true')

    args = parser.parse_args()
    driverName = args.driverName if args.driverName else ''
    comPort = args.comPort if args.comPort else ''
    address = args.address if args.addressaddress else ''
    virtualComPort = args.virtualComPort if args.virtualComPort else ''
    
    drv = FmlxDeviceConnectorSingle(driver_name=driverName,address=address,port=comPort)
    
