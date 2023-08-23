import socket
from queue import Queue
import threading
import logging

class TcpServer(object):
    DriverName = 'TcpServer'
    VERSION = '1.0.0'
    def __init__(self,hostName,port, log_handler = None):
        self._logger = logging.getLogger('TcpServerFmlxDriver')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('TcpServerFmlxDriver version : {0}, HostName : {1}, Port : {2}'.format(TcpServer.VERSION,hostName,port))
        
        self._hostName = hostName
        self._port = port
        self.ReadTimeout = 500
        self.WriteTimeout = 500
        self._msgQueue = Queue()
        self._isConnected = False
        self._Socket = None
        self._Conn = None
        self._Addr = None
        self._dataAvaiableEvent = threading.Event()

    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)
        
    @property
    def Connected(self):
        return self._isConnected

    def __del__(self):
        self.Disconnect()
        self._bus = None

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._Socket.bind((self._hostName, self._port))
        self._Socket.listen()
        self._logger.info('Waiting for client connection..')
        self._Conn, self._Addr = self._Socket.accept()
        self._logger.info(f'Connection Accepted from {self._Addr}')
        self._isConnected = True
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()
        

    def Disconnect(self):
        if(not self._isConnected):
            return
        self._Conn.close()
        self._Socket.close()
        self._isConnected = False
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()
        self._logger.info('Disconnect..')

    def ResetDevice(self):
        raise NotImplementedError('can\'t reset device using TCP driver')

    def Write(self, buffer):
        self._logger.debug(f'data write : {list(buffer)}')
        self._Conn.sendall(bytes(buffer))

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
            try:
                receivedData = self._Conn.recv(1024)
            except ConnectionResetError:
                # keep waiting till someone reconnect
                self._logger.info('Client Disconnected, waiting for new client')
                # self._Socket.close()
                # self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # self._Socket.bind((self._hostName, self._port))
                self._Socket.listen()
                self._Conn, self._Addr  = self._Socket.accept()
                self._logger.info(f'Client Connected again, address : {self._Addr}')
                continue
            if(receivedData == bytes()):
                self._logger.info('client close the connection, automatically disconnect')
                self.Disconnect()
                break
            for data in receivedData:
                self._msgQueue.put(data)
            self._logger.debug(f'data received : {list(receivedData)}')
            self._dataAvaiableEvent.set()
    

class TcpClient(object):
    DriverName = 'TcpClient'
    VERSION = '1.0.0'
    def __init__(self,hostName,port, log_handler = None):
        self._logger = logging.getLogger('TcpClientFmlxDriver')
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('TcpClientFmlxDriver version : {0}, HostName : {1}, Port : {2}'.format(TcpClient.VERSION,hostName,port))
        
        self._hostName = hostName
        self._port = port
        self.ReadTimeout = 500
        self.WriteTimeout = 500
        self._msgQueue = Queue()
        self._isConnected = False
        self._Socket = None
        self._dataAvaiableEvent = threading.Event()
        
    def SetLogHandler(self,log_handler):
        self._logger.addHandler(log_handler)

    @property
    def Connected(self):
        return self._isConnected

    def __del__(self):
        self.Disconnect()

    @property
    def BytesInReadQueue(self):
        return self._msgQueue.qsize()

    def Connect(self):
        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Waiting for server connection..')
        self._Socket.connect((self._hostName, self._port))
        self._isConnected = True
        self._receiveThreadInstance = threading.Thread(target=self.receiveThread)
        self._receiveThreadInstance.daemon = True
        self._receiveThreadInstance.start()
        

    def Disconnect(self):
        if(not self._isConnected):
            return
        self._Socket.close()
        self._isConnected = False
        with self._msgQueue.mutex:
            self._msgQueue.queue.clear()
        print('Disconnect..')

    def ResetDevice(self):
        raise NotImplementedError('can\'t reset device using TCP driver')

    def Write(self, buffer):
        self._Socket.sendall(bytes(buffer))

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
            receivedData = self._Socket.recv(1024)
            if(receivedData == bytes()):
                print('server close the connection, automatically disconnect')
                self.Disconnect()
                break
            for data in receivedData:
                self._msgQueue.put(data)
            # print(receivedData)
            self._dataAvaiableEvent.set()
        