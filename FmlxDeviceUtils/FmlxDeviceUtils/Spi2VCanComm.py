import can

class Spi2VcanComm():
    def __init__(self,txAddress=0x577,rxAddress=0x578,bustype = 'socketcan_native',channel = 'vcan0',bitrate = 1000000):
        # it's supposed to be public
        self.ReadTimeout = 0.5
        self._txAddress = txAddress
        self._rxAddress = rxAddress
        # then below is private
        self._filters = [{"can_id": self._rxAddress, "can_mask": 0x7FF, "extended":False}]
        self._bus = can.interface.Bus(bustype=bustype, channel=channel, bitrate=bitrate,can_filters=self._filters, accept_virtual = True, single_handle  = True)
        
    def OpenCANChannel(self):
        buffer = [ord('O')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))

    def CloseCANChannel(self):
        buffer = [ord('C')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))

    def SetAcceptanceMask(self,mask):
        buffer = [ord('M')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))

    def SetAcceptanceFilter(self):
        pass

    def SetCANbitrate(self):
        pass

    def ReadStatusFlag(self):
        buffer = [ord('F')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))
        resps = self.waitResponse()
        strData = ''
        for resp in resps:
            if(resp == 0x0a or resp == 0x00):
                break
            strData+=chr(resp)
        return strData

    def ReadVersion(self):
        buffer = [ord('V')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))
        resps = self.waitResponse()
        strData = ''
        for resp in resps:
            if(resp == 0x0a or resp == 0x00):
                break
            strData+=chr(resp)
        return strData
    
    def ReadSerialNumber(self):
        buffer = [ord('N')]
        self._bus.send(can.Message(data = buffer,is_extended_id=False,arbitration_id=self._txAddress))
        resps = self.waitResponse()
        strData = ''
        for resp in resps:
            if(resp == 0x0a or resp == 0x00):
                break
            strData+=chr(resp)
        return strData

    def ReadPowerManagementStatus(self):
        pass

    def waitResponse(self):
        receivedData = self._bus.recv(1)
        if(not receivedData):
            raise TimeoutError('No response from SPI2CAN')
        return list(receivedData.data)