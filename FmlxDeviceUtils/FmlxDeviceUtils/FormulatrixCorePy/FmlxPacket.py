import os
import struct
import threading
import ctypes
import logging
try: 
    import queue
except ImportError:
    import Queue as queue


class FmlxPacket(object):
    MAX_DATA_SIZE = 512
    HEADER_SIZE = 14
    # define the positions of each parameter
    SIZE_INDEX = 0
    SEQUENCEID_INDEX = 2   # Notice: this is used by FindPacket, it should be 0
    PACKETID_INDEX = 4
    RESERVED_INDEX = 6     # Notice: this is used by FindPacket, it should be 0
    ADDRESS_INDEX = 8      # Notice: this is used by FindPacket, it should be 0
    OPCODE_INDEX = 10
    DATA_INDEX = 12
    MAX_PACKET_SIZE = MAX_DATA_SIZE + HEADER_SIZE

    _PacketID = 0xFFFF

    def __init__(self, rawBuffer=None,useSinglePrecision = False):
        if(rawBuffer == None):
            self._rawBuffer = [0]*FmlxPacket.MAX_PACKET_SIZE
            FmlxPacket._PacketID = (FmlxPacket._PacketID+1) % 0x10000
            self._rawBuffer[FmlxPacket.PACKETID_INDEX] = FmlxPacket._PacketID & 0xff
            self._rawBuffer[FmlxPacket.PACKETID_INDEX +
                            1] = (FmlxPacket._PacketID >> 8) & 0xff
            self._rawBuffer[FmlxPacket.SIZE_INDEX] = 12
        else:
            self._rawBuffer = rawBuffer
            self._useSinglePrecision = useSinglePrecision
        self._writeIndex = 0
        self._readIndex = 0

    @property
    def Size(self):
        return self._rawBuffer[FmlxPacket.SIZE_INDEX] | self._rawBuffer[FmlxPacket.SIZE_INDEX + 1] << 8

    @Size.setter
    def Size(self, value):
        self._rawBuffer[FmlxPacket.SIZE_INDEX] = value & 0xff
        self._rawBuffer[FmlxPacket.SIZE_INDEX + 1] = (value >> 8) & 0xff

    @property
    def Address(self):
        return self._rawBuffer[FmlxPacket.ADDRESS_INDEX] | self._rawBuffer[FmlxPacket.ADDRESS_INDEX + 1] << 8

    @Address.setter
    def Address(self, value):
        self._rawBuffer[FmlxPacket.ADDRESS_INDEX] = value & 0xff
        self._rawBuffer[FmlxPacket.ADDRESS_INDEX + 1] = (value >> 8) & 0xff

    @property
    def Opcode(self):
        return self._rawBuffer[FmlxPacket.OPCODE_INDEX] | self._rawBuffer[FmlxPacket.OPCODE_INDEX + 1] << 8

    @Opcode.setter
    def Opcode(self, value):
        self._rawBuffer[FmlxPacket.OPCODE_INDEX] = value & 0xff
        self._rawBuffer[FmlxPacket.OPCODE_INDEX + 1] = (value >> 8) & 0xff

    @property
    def PacketId(self):
        return self._rawBuffer[FmlxPacket.PACKETID_INDEX] | self._rawBuffer[FmlxPacket.PACKETID_INDEX + 1] << 8

    @PacketId.setter
    def PacketId(self,value):
        self._rawBuffer[FmlxPacket.PACKETID_INDEX] = value & 0xff
        self._rawBuffer[FmlxPacket.PACKETID_INDEX + 1] = (value >> 8) & 0xff

    @property
    def Checksum(self):
        return self._rawBuffer[self.Size] | self._rawBuffer[self.Size +1] << 8

    @Checksum.setter
    def Checksum(self, value):
        self._rawBuffer[self.Size] = value & 0xff
        self._rawBuffer[self.Size+1] = (value >> 8) & 0xff

    @property
    def Payload(self):
        return self._rawBuffer[FmlxPacket.DATA_INDEX : self.Size]

    def calculateChecksum(self):
        checksum = 0
        size = self.Size
        idx = 0
        while (size > 0):
            word = self._rawBuffer[idx] | (self._rawBuffer[idx+1]<<8)
            checksum ^= word
            size -= 2
            idx += 2
        return checksum

    def VerifyChecksum(self):
        # print('chk buf:',self.Checksum,'chk calc:',self.calculateChecksum())
        return self.Checksum == self.calculateChecksum()

    # below is currently use on fmlxpacket receive mode
    @property
    def IsSizeValid(self):
        return len(self._rawBuffer) >= FmlxPacket.HEADER_SIZE

    @property
    def IsSizePacketReceived(self):
        return len(self._rawBuffer) >= FmlxPacket.SEQUENCEID_INDEX

    @property
    def IsSizeLegal(self):
        try:
            return self.Size <= FmlxPacket.MAX_PACKET_SIZE
        except IndexError:
            return False

    @property
    def IsEvent(self):
        return self.Opcode >=512 

    @property
    def IsAllDataReceived(self):
        return (len(self._rawBuffer) - 2) >= self.Size

    def Add(self, values):
        if(type(values) == list):
            for value in values:
                self.Add(value)
        elif(type(values) == str):
            values+=chr(0) # add null terminator
            for value in values:
                self.Add(ctypes.c_int16(ord(value)))
        else:
            byte = list(map(int, bytearray(values)))
            size = ctypes.sizeof(values)
            self.checkWriteDataIndex(size)
            from_index = FmlxPacket.DATA_INDEX + self._writeIndex
            until_index = FmlxPacket.DATA_INDEX + self._writeIndex + size
            self._rawBuffer[from_index: until_index] = byte
            self._writeIndex += size
            self.Size += size
            self.Checksum = self.calculateChecksum()

    def checkReadDataIndex(self, parameterSize):
        if((FmlxPacket.DATA_INDEX + self._readIndex + parameterSize) > self.Size):
            raise IndexError(
                'Error parsing packet: Not enough data received to decode parameter. Index = {0}, Parameter Size = {1}, Data Size = {2}. Packet = {3}'.format(self._readIndex,parameterSize,self.Size,self.ToRaw))

    def checkWriteDataIndex(self, parameterSize):
        if((FmlxPacket.DATA_INDEX + self._writeIndex + parameterSize) >= FmlxPacket.MAX_PACKET_SIZE):
            raise IndexError(
                'Error Writing: Write Buffer has not enough space. Index = {0}, Parameter Size = {1}, Data Size = {2}'.format(self._writeIndex,parameterSize,self.Size))

    def FetchBool(self):
        return self.FetchUInt16() != 0

    def FetchInt16(self):
        self.checkReadDataIndex(ctypes.sizeof(ctypes.c_int16))
        from_index = FmlxPacket.DATA_INDEX + self._readIndex
        until_index = FmlxPacket.DATA_INDEX + \
            self._readIndex + ctypes.sizeof(ctypes.c_int16)
        value = struct.unpack('h', bytearray(
            self._rawBuffer[from_index: until_index]))[0]
        self._readIndex += ctypes.sizeof(ctypes.c_int16)
        return value

    def FetchUInt16(self):
        self.checkReadDataIndex(ctypes.sizeof(ctypes.c_uint16))
        from_index = FmlxPacket.DATA_INDEX + self._readIndex
        until_index = FmlxPacket.DATA_INDEX + \
            self._readIndex + ctypes.sizeof(ctypes.c_uint16)
        value = struct.unpack('H', bytearray(
            self._rawBuffer[from_index: until_index]))[0]
        self._readIndex += ctypes.sizeof(ctypes.c_uint16)
        return value

    def FetchInt32(self):
        self.checkReadDataIndex(ctypes.sizeof(ctypes.c_int32))
        from_index = FmlxPacket.DATA_INDEX + self._readIndex
        until_index = FmlxPacket.DATA_INDEX + \
            self._readIndex + ctypes.sizeof(ctypes.c_int32)
        value = struct.unpack('i', bytearray(
            self._rawBuffer[from_index: until_index]))[0]
        self._readIndex += ctypes.sizeof(ctypes.c_int32)
        return value

    def FetchUInt32(self):
        self.checkReadDataIndex(ctypes.sizeof(ctypes.c_uint32))
        from_index = FmlxPacket.DATA_INDEX + self._readIndex
        until_index = FmlxPacket.DATA_INDEX + \
            self._readIndex + ctypes.sizeof(ctypes.c_uint32)
        value = struct.unpack('I', bytearray(
            self._rawBuffer[from_index: until_index]))[0]
        self._readIndex += ctypes.sizeof(ctypes.c_uint32)
        return value

    def FetchFloat(self):
        self.checkReadDataIndex(ctypes.sizeof(ctypes.c_float))
        from_index = FmlxPacket.DATA_INDEX + self._readIndex
        until_index = FmlxPacket.DATA_INDEX + \
            self._readIndex + ctypes.sizeof(ctypes.c_float)
        value = struct.unpack('f', bytearray(
            self._rawBuffer[from_index: until_index]))[0]
        self._readIndex += ctypes.sizeof(ctypes.c_float)
        return value

    def FetchDouble(self):
        if(not self._useSinglePrecision):
            self.checkReadDataIndex(ctypes.sizeof(ctypes.c_double))
            from_index = FmlxPacket.DATA_INDEX + self._readIndex
            until_index = FmlxPacket.DATA_INDEX + \
                self._readIndex + ctypes.sizeof(ctypes.c_double)
            value = struct.unpack('d', bytearray(
                self._rawBuffer[from_index: until_index]))[0]
            self._readIndex += ctypes.sizeof(ctypes.c_double)
            return value
        else:
            return self.FetchFloat()
        
    def FetchString(self):
        items = [chr(self.FetchUInt16())]
        while(items[-1:][0] is not chr(0)):
            items.append(chr(self.FetchUInt16()))
        else:
            items.pop()
        return ''.join(items)

    def FetchBoolArray(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchBool())
            count -= 1
        return items

    def FetchInt16Array(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchInt16())
            count -= 1
        return items

    def FetchUInt16Array(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchUInt16())
            count -= 1
        return items

    def FetchInt32Array(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchInt32())
            count -= 1
        return items

    def FetchUInt32Array(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchUInt32())
            count -= 1
        return items

    def FetchFloatArray(self, count):
        items = []
        while(count > 0):
            items.append(self.FetchFloat())
            count -= 1
        return items

    def FetchDoubleArray(self, count):
        items = []
        while(count > 0):
            if(not self._useSinglePrecision):
                items.append(self.FetchDouble())
            else:
                items.append(self.FetchFloat())
            count -= 1
        return items

    @property
    def ToRaw(self):
        return self._rawBuffer[:self.Size+2]

    def ResetWrite(self):
        self.Size = 12
        self._writeIndex = 0

    def ResetRead(self):
        self._readIndex = 0