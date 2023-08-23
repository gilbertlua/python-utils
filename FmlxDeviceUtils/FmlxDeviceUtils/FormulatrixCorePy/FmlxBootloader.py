from FormulatrixCorePy.FmlxController import IllegalOpcodeError
import ctypes
from enum import Enum
from intelhex import IntelHex, IntelHexError
import threading
import FmlxLogger
import logging
import time
from FormulatrixCorePy import FmlxController

class Record():
    VERSION = '1.0.0'

    def __init__(self,log_handler = None) -> None:
        self.Address = 0
        self.UpperAddress = 0
        self.ByteCount = 0
        self.RecordType = 0
        self.Data = []
        self.Checksum = 0
        self._logger = logging.getLogger('BootRecord')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel = logging.CRITICAL))
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.info('BootRecord version : {0}'.format(Record.VERSION))

    def CalculateChecksum(self):
        sum = self.ByteCount & 0xff
        sum += (self.Address >> 8) & 0xff
        sum += (self.Address) & 0xff
        sum += self.RecordType & 0xff
        for idx in range(self.ByteCount):
            sum += self.Data[idx]
        sum &= 0xff
        sum = 0x100 - sum
        return sum & 0xff

    def VerifyChecksum(self):
        expectedChecksum = self.CalculateChecksum()
        if (self.Checksum != expectedChecksum):
            raise IntelHexError('Checksum error: Expected {0} but found {1}'.format(
                expectedChecksum, self.Checksum))

    def ParseHex(self, text, index, length):
        value = 0
        length -= 1
        while (length >= 0):
            value <<= 4
            c = ord(text[index])
            index += 1
            if ((c >= ord('0')) and (c <= ord('9'))):
                value += c - ord('0')

            elif ((c >= ord('a')) and (c <= ord('f'))):
                value += c - ord('a') + 10

            elif ((c >= ord('A')) and (c <= ord('F'))):
                value += c - ord('A') + 10

            else:
                raise IntelHexError(
                    'Cannot parse hex value in line: {0}'.format(text))
            length -= 1
        return value

    def Parse(self, text, upperAddress):
        self.ByteCount = self.ParseHex(text, 1, 2)
        self.UpperAddress = upperAddress
        self.RecordType = self.ParseHex(text, 7, 2)
        if(self.RecordType == 0 or self.RecordType == 1):
            pass
        elif(self.RecordType == 4):
            self.UpperAddress = int(self.ParseHex(text, 9, 4))
        elif(self.RecordType == 5):
            self.UpperAddress = int((self.ParseHex(text, 9, 4)))
        else:
            self._logger.warning('Illegal record type : {0} in line: {1}'.format(self.RecordType, text))
            # raise IntelHexError(
            #     'Illegal record type : {0} in line: {1}'.format(self.RecordType, text))

        self.Address = self.ParseHex(text, 3, 4) + (self.UpperAddress << 16)
        self.Checksum = self.ParseHex(text, self.ByteCount * 2 + 9, 2)
        for idx in range(self.ByteCount):
            self.Data += [int(self.ParseHex(text, 9 + idx * 2, 2))]

        self.VerifyChecksum()


class BootloaderApp():
    VERSION = '1.0.0'
    class BootloaderFailError(Exception):
        def __init__(self, failedAddress, expectedData, actualData, message):
            self._failedAddress = failedAddress
            self._expectedData = expectedData
            self._actualData = actualData
            self._message = message
            pass

        def __str__(self):
            return 'Fail to {0} with details : failed address : {1}, expected data : {2}, actual data : {3}'.format(self._message, hex(self._failedAddress), hex(self._expectedData), hex(self._actualData))

    class ResetOption():
        Hang = 0
        Hardware = 1
        Default = 2

    class McuPlatform():
        TexasInstrument = 0
        STM32F4 = 1
        IntelHexFormat=2
        NXP546 = 3
        ATSAME54 = 4

    OP_USERAPP_GET_VERSION = 1
    OP_USERAPP_GET_APP_NAME = 2
    OP_USERAPP_FIRMARE_RESET = 9
    OP_BOOTLOADER_GET_VERSION = 0x7F00
    OP_BOOTLOADER_GET_APP_NAME = 0x7F01
    OP_BOOTLOADER_WRITE_MEMORY = 0x7F02
    OP_BOOTLOADER_READ_MEMORY = 0x7f03
    OP_BOOTLOADER_JUMP_TO_MEMORY = 0x7f04
    OP_BOOTLOADER_ERASE_FLASH = 0x7f05
    OP_BOOTLOADER_PROGRAM_FLASH = 0x7f06
    OP_BOOTLOADER_VERIFY_FLASH = 0x7f07
    OP_BOOTLOADER_START_USER_APP = 0x7f08
    OP_BOOTLOADER_ON_ENTRY_EVENT = 0x7ff

    MAX_COMM_RETRY = 3
    def __init__(self, bootloaderController, UserAppController,busIdBootloader,busIdUserApp,resetOption,mcuPlatform,log_handler = None):
        self._userAppController = UserAppController
        self._bootloaderController = bootloaderController
        self._bootloaderAddress = busIdBootloader
        self._userAppAddress = busIdUserApp
        self._bootloaderController+=self.OnBootloaderEntry
        self._resetOption = resetOption
        self._mcuPlatform = mcuPlatform
        self._BootloaderEvent = threading.Event()
        self._logger = logging.getLogger('FirmwareLoader')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel = logging.DEBUG))
        if(log_handler):
            # print(log_handler)
            # time.sleep(3)
            self._logger.addHandler(log_handler)
        self._logger.info('FirmwareLoader : {0}'.format(Record.VERSION))

    # def __init__(self,mcuPlatform):
    #     pass
        # self._userAppController = UserAppController
        # self._bootloaderController = bootloaderController
        # self._bootloaderAddress = 0
        # self._userAppAddress = 0
        # self._bootloaderController+=self.OnBootloaderEntry
        # self._resetOption = resetOption
        # self._BootloaderEvent = threading.Event()
        # self._mcuPlatform = mcuPlatform

    def ParseFile(self, hexFile):
        return IntelHex(hexFile)

    def ResetHardware(self):
        self._BootloaderEvent.clear()
        if(self._resetOption == BootloaderApp.ResetOption.Hang):
            self._logger.debug('reset hardware use firmware reset command')
            self.FirmwareReset()

        elif(self._resetOption == BootloaderApp.ResetOption.Hardware):
            self._logger.debug('reset hardware use hardware reset')
            self._userAppController.ResetFirmware()

        elif(self._resetOption == BootloaderApp.ResetOption.Default):
            # Using try-catch to check whether ResetFirmware() is implemented by the driver
            # Not a common / good practice in C# but it's simple in this case
            try:
                self._userAppController.ResetFirmware()
            except NotImplementedError:
                self.FirmwareReset()
                
    def GenerateRecords(self, filename):
        records = []
        if(self._mcuPlatform == BootloaderApp.McuPlatform.TexasInstrument):
            with open(filename, 'rb') as f:
                hexString = f.read()
            hexStringLines = hexString.splitlines()
            hasEOF = False
            upperAddress = 0
            for lineNumber, text in enumerate(hexStringLines):
                text = text.decode('ascii')
                if(len(text) < 11 or text[0] != ':'):
                    raise IntelHexError(
                        'Illegal format in line #{0}: {1}'.format(lineNumber, text))
                if (hasEOF):
                    raise IntelHexError(
                        'llegal EOF in line #{0}: {1}'.format(lineNumber, text))
                record = Record()
                record.Parse(text, upperAddress)
                upperAddress = record.UpperAddress
                if(record.RecordType == 0):
                    dataList = [hex(evenList<<8 | oddList) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
                    self._logger.debug('parsing record addr : {0}, dataCount : {1}, data : {2}'.format(hex(record.Address),record.ByteCount/2,dataList)) 
                    records.append(record)
                elif(record.RecordType == 1):
                    hasEOF = True

        elif(self._mcuPlatform == BootloaderApp.McuPlatform.STM32F4):
            maxByteCount = 500
            ih = IntelHex(filename)
            segments = ih.segments()
            # print(segments)
            for segment in segments:
                totalByte = segment[1]-segment[0]
                offset_address = segment[0]
                while(totalByte > 0):
                    # print('address',hex(offset_address))
                    record = Record()
                    record.ByteCount = min(maxByteCount,totalByte)
                    record.Address = offset_address 
                    record.Data = list(ih.gets(record.Address,record.ByteCount))
                    offset_address += record.ByteCount
                    totalByte-=record.ByteCount
                    dataList = [hex(evenList<<8 | oddList) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
                    self._logger.debug('parsing record addr : {0}, dataCount : {1}, data : {2}'.format(hex(record.Address),record.ByteCount/2,dataList)) 
                    records.append(record)
 
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.ATSAME54):
            maxByteCount = 256
            ih = IntelHex(filename)
            segments = ih.segments()
            self.s = segments
            for segment in segments:
                totalByte = segment[1]-segment[0]
                offset_address = segment[0]
                while(totalByte > 0):
                    record = Record()
                    record.ByteCount = min(maxByteCount,totalByte)
                    record.Address = offset_address 
                    record.Data = list(ih.gets(record.Address,record.ByteCount))
                    offset_address += record.ByteCount
                    totalByte-=record.ByteCount
                    dataList = [hex(evenList | oddList<<8) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
                    self._logger.debug('parsing record addr : {0}, dataCount : {1}, data : {2}'.format(hex(record.Address),record.ByteCount/2,dataList)) 
                    records.append(record)        
        #return records

        elif(self._mcuPlatform == BootloaderApp.McuPlatform.NXP546):
            maxByteCount = 256
            ih = IntelHex(filename)
            segments = ih.segments()
            for segment in segments:
                totalByte = segment[1]-segment[0]
                offset_address = segment[0]
                while(totalByte > 0):
                    # print('address',hex(offset_address))
                    record = Record()
                    record.ByteCount = min(maxByteCount,totalByte)
                    record.Address = offset_address 
                    record.Data = list(ih.gets(record.Address,record.ByteCount))
                    offset_address += record.ByteCount
                    totalByte-=record.ByteCount
                    dataList = [hex(evenList | oddList<<8) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
                    self._logger.debug('parsing record addr : {0}, dataCount : {1}, data : {2}'.format(hex(record.Address),record.ByteCount/2,dataList)) 
                    records.append(record)        
        return records


    def DetermineAddressRange(self, records):
        addrRanges = []
        addRange = [0, 0]
        for record in records:
            if addRange[1] == 0:
                addRange[0] = record.Address
                addRange[1] = record.ByteCount >> 1
            elif((addRange[0] + addRange[1]) == record.Address):
                addRange[1] += record.ByteCount >> 1
            else:
                addrRanges.append(addRange)
                addRange = [record.Address, record.ByteCount >> 1]

        addrRanges.append(addRange)
        return addrRanges

    def addressToSectorSTM32F4(self,address):
        base16Kbytes = 0x08000000
        base128Kbytes = 0x08020000

        # sector 0 - 3
        for i in range(4):
            baseAddress = base16Kbytes + i * 16 * 1024
            endAddress = baseAddress + 16 * 1024
            if (address >= baseAddress and address < endAddress):
                return i
        
        # sector 4
        if (address >= 0x08010000 and address < 0x08020000):
            return 4

        # sector 5 - 11
        for i in range(7):
            baseAddress = base128Kbytes + i * 128 * 1024
            endAddress = baseAddress + 128 * 1024
            if (address >= baseAddress and address < endAddress):
                return i + 5
        
        # invalid sector
        return -1

    def addressToBlockATSAM(self,address):
        sector = address // 0x2000
        if (sector >= 0 and sector<32):
            return sector
        else:
            raise IndexError('Invalid Address : {0}',format(address))
        
    def addressToSectorNXP546(self,address):
        sector = address // 32768
        if (sector >= 0 and sector<16):
            return sector
        else:
            #invalid sector
            return -1
        
    def addressToPageNXP546(self,address):
        page = address//256
        if (page>=0 and page <2048):
            return page
        else:    
            return -1           #invalid page

    def InvokeBootloader(self):
        self._BootloaderEvent.clear()
        self._logger.debug('try to get bootloader app name')
        try:
            appName = self.GetBootloaderAppName()
            version = self.GetBootloaderVersion()
            self._logger.debug('get bootloader app name success, appname : {0}, version : {1}'.format(appName,version))
            # break
        except TimeoutError:
            self._logger.debug('get bootloader app name fail, because of timeout')
            self.ResetHardware()
            if(self._BootloaderEvent.wait(3)):
                self._logger.debug('Bootloader Event Received! try to get bootloader app name again after reset')
                appName = self.GetBootloaderAppName()
                version = self.GetBootloaderVersion()
                self._logger.debug('get bootloader app name success, appname : {0}, version : {1}'.format(appName,version))
            else:
                raise IntelHexError('Fail to Reset Firmware!')
        except FmlxController.IllegalOpcodeError:
            self._logger.debug('get bootloader app name fail, because of illegal opcode')
            self.ResetHardware()
            if(self._BootloaderEvent.wait(3)):
                self._logger.debug('Bootloader Event Received! try to get bootloader app name again after reset')
                appName = self.GetBootloaderAppName()
                version = self.GetBootloaderVersion()
                self._logger.debug('get bootloader app name success, appname : {0}, version : {1}'.format(appName,version))
                
            else:
                raise IntelHexError('Fail to Reset Firmware!')
        print('Succesfully entering {0} version : {1}',appName,version)

    def UpgradeFirmware(self,appName,appVersion,filename):
        records = self.GenerateRecords(filename=filename)
        self.records = records
        addressRanges = self.DetermineAddressRange(records=records)
        erasedSize = 0
        # UInt32 totalSize = addressRanges.Aggregate((acc, next) => new Pair<UInt32, UInt32> { First = acc.First, Second = acc.Second + next.Second }).Second;
        
        self.InvokeBootloader()
        #erasing 
        if(self._mcuPlatform == BootloaderApp.McuPlatform.STM32F4):
            prevErasedSector = 0xFFFFFFF
            lastAddress = records[len(records) - 1].Address
            for record in records: 
                memorySector = self.addressToSectorSTM32F4(record.Address)
                if (prevErasedSector != memorySector):
                    self._logger.debug('STM32 erasing sector : {0}'.format(memorySector))
                    self.EraseFlash(record.Address, 1)
                    prevErasedSector = memorySector
                # UpdateProgress(Action.EraseFlash, (int)(10 + 20.0 * record.Address / lastAddress));
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.NXP546):
            prevErasedSector = 0xFFFFFFF
            lastAddress = records[len(records) - 1].Address
            for record in records: 
                memorySector = self.addressToSectorNXP546(record.Address)
                if (prevErasedSector != memorySector):
                    self._logger.debug('NXP546 erasing sector : {0}'.format(memorySector))
                    self.EraseFlash(record.Address, 1)
                    prevErasedSector = memorySector
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.TexasInstrument):
            # print('address range',hex(addressRanges)
            self._bootloaderController.ReadTimeout = 10000 # TI need a lot of time to erase
            for i in range(len(addressRanges)-1,-1,-1):
                address,size = addressRanges[i]
                self._logger.debug('TI erasing address : {0}, size : {1}'.format(hex(address),size))
                self.EraseFlash(address, size)
                erasedSize += size
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.ATSAME54):
            lastSector = -1
            for record in records:
                sector = self.addressToBlockATSAM(record.Address)
                if(sector is not lastSector):
                    lastSector=sector
                    self._logger.debug('erasing sector : {0}, address {1}'.format(sector,hex(record.Address)))
                    self.EraseFlash(record.Address,1)

        # raise Exception('wkwk')
        self._bootloaderController.ReadTimeout = 2000 # back to Normal timeout value
        # writing
        if(self._mcuPlatform == BootloaderApp.McuPlatform.STM32F4):
            for i in range(len(records)-1,-1,-1):
                self.ProgramRecord(records[i])
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.TexasInstrument):
            for i in range(len(records)):
                self.ProgramRecord(records[i])
        if(self._mcuPlatform == BootloaderApp.McuPlatform.ATSAME54):
            # raise Exception('stop it!')
            # for i in range(len(records)-1,-1,-1):
            
            #     self.ProgramRecord(records[i])
            for i in range(len(records)-1,-1,-1):
                print('writing : {0} , size : {1}'.format(hex(records[i].Address),records[i].ByteCount))
                self.ProgramRecord(records[i])
            # for record in records:
            #     self.ProgramRecord(record)
            # self._bootloaderController.ReadTimeout = 3000 
        elif(self._mcuPlatform == BootloaderApp.McuPlatform.NXP546):
            self._bootloaderController.ReadTimeout = 3000
            for i in range(len(records)-1,-1,-1):
                # print('writing : {0} , size : {1}'.format(hex(records[i].Address),records[i].ByteCount))
                self.ProgramRecord(records[i])

        
        # verifying..
        for i in range(len(records)):
            self.VerifyRecord(records[i])

        # start application
        print('Verify Success, starting app..')
        self.StartUserApp()
        time.sleep(5)
        print('App Started! Name : {0} version : {1}'.format(self.GetUserAppName(),self.GetUserAppVersion()))
            
    def ProgramRecord(self,record):
        args = []
        args += [ctypes.c_uint32(record.Address)] # address
        args += [ctypes.c_uint32(record.ByteCount >> 1)] # bytecount
        args += [ctypes.c_uint16(1)] # do verify
        dataList = [hex(evenList<<8 | oddList) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
        self._logger.info('writing address : {0}, bytecount : {1} /2 = {2}, data = {3}'.format(hex(record.Address),record.ByteCount,record.ByteCount>>1,dataList))
        for i in range(0,record.ByteCount,2):
            data =  (record.Data[i] & 0xff) << 8
            data += record.Data[i+1] & 0xff
            args += [ctypes.c_uint16(data)]
        
        response = self._bootloaderController.SendCommand( BootloaderApp.OP_BOOTLOADER_PROGRAM_FLASH, self._bootloaderAddress, *args)    
        isSuccess = response.FetchBool()
        if(not isSuccess):
            flashStatus = response.FetchUInt16()
            failedAddress = response.FetchUInt32()
            expectedData = response.FetchUInt16()
            actualData = response.FetchUInt16()
            raise BootloaderApp.BootloaderFailError(
                failedAddress, expectedData, actualData, 'Writing')

    def VerifyRecord(self,record):
        args = []
        args += [ctypes.c_uint32(record.Address)]
        args += [ctypes.c_uint32(record.ByteCount >> 1)]
        for i in range(0,record.ByteCount,2):
            data =  record.Data[i] << 8
            data += record.Data[i+1]
            args += [ctypes.c_uint16(data)]
        dataList = [hex(evenList<<8 | oddList) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
        self._logger.info('verifying address : {0}, bytecount : {1} /2 = {2}, data = {3}'.format(hex(record.Address),record.ByteCount,record.ByteCount>>1,dataList))
        response = self._bootloaderController.SendCommand( BootloaderApp.OP_BOOTLOADER_VERIFY_FLASH, self._bootloaderAddress, *args)    
        isSuccess = response.FetchBool()
        if(not isSuccess):
            flashStatus = response.FetchUInt16()
            failedAddress = response.FetchUInt32()
            expectedData = response.FetchUInt16()
            actualData = response.FetchUInt16()
            raise BootloaderApp.BootloaderFailError(
                failedAddress, expectedData, actualData, 'Verifying')

    # basic User Application API
    def GetUserAppVersion(self):
        self._logger.debug('Get User App Version')
        response = self._userAppController.SendCommand(
            BootloaderApp.OP_USERAPP_GET_VERSION, self._userAppAddress)
        return response.FetchString()

    def GetUserAppName(self):
        self._logger.debug('Get User App Name')
        response = self._userAppController.SendCommand(
            BootloaderApp.OP_USERAPP_GET_APP_NAME, self._userAppAddress)
        return response.FetchString()

    def FirmwareReset(self):
        tempTimeout = self._userAppController.ReadTimeout
        self._userAppController.ReadTimeout = 50
        try:
            self._userAppController.SendCommand(BootloaderApp.OP_USERAPP_FIRMARE_RESET, self._userAppAddress)
        except TimeoutError:
            pass # expect a timeout error
        except FmlxController.IllegalOpcodeError:
            pass # also maybe expect a illegal opcode error
        finally:
            self._userAppController.ReadTimeout = tempTimeout

    # basic bootloader API
    def OnBootloaderEntry(self, fmlxPacket):
        print('Bootloader event received! OP :',fmlxPacket.Opcode)
        if(fmlxPacket.Opcode != BootloaderApp.OP_BOOTLOADER_ON_ENTRY_EVENT and fmlxPacket.Opcode != 0x7fff):
            print('wrong opcode!')
            return
        print('opcode is right!')
        self._BootloaderEvent.set()

    def GetBootloaderVersion(self):
        response = self._bootloaderController.SendCommand(
            BootloaderApp.OP_BOOTLOADER_GET_VERSION, self._bootloaderAddress)
        return response.FetchString()

    def GetBootloaderAppName(self):
        response = self._bootloaderController.SendCommand(
            BootloaderApp.OP_BOOTLOADER_GET_APP_NAME, self._bootloaderAddress)
        return response.FetchString()

    def EraseFlash(self, addr, length):
        args = []
        args += [ctypes.c_uint32(addr)]
        args += [ctypes.c_uint32(length)]
        print('Erasing, address : {0}, length : {1}'.format(hex(addr),length))
        response = self._bootloaderController.SendCommand(
            BootloaderApp.OP_BOOTLOADER_ERASE_FLASH, self._bootloaderAddress, *args)
        isSuccess = response.FetchBool()
        if(not isSuccess):
            flashStatus = response.FetchUInt16()
            failedAddress = response.FetchUInt32()
            expectedData = response.FetchUInt16()
            actualData = response.FetchUInt16()
            raise BootloaderApp.BootloaderFailError(
                failedAddress, expectedData, actualData, 'Erase')

    def StartUserApp(self):
        self._logger.debug('Start User App')
        try:
            self._bootloaderController.SendCommand(BootloaderApp.OP_BOOTLOADER_START_USER_APP, self._bootloaderAddress)
        except TimeoutError:
            print('Start User App Success')

    @staticmethod
    def RecordToHex(record):
        return [hex(evenList<<8 | oddList) for evenList,oddList in zip(record.Data[0:-1:2],record.Data[1:-1:2])]
        
