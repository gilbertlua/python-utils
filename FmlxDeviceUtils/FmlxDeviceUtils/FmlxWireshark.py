#!/usr/bin/python
# -*- coding: utf-8 -*-
import ntpath
from datetime import datetime
import FmlxDeviceConnector
from FmlxDevice import FmlxDevice
from Formulatrix.Core.Protocol import FmlxController, IFmlxDriver, FmlxTimeoutException, FmlxPacket
import sys
import clr
import time
import threading
import yaml
# import wx
import os
import struct
import logging
import FmlxLogger

import FormulatrixCorePy.FmlxPacket
import FormulatrixCorePy.FmlxController
import ctypes

from colorama import init, Fore, Back, Style
init()  # colorama

sys.path.append(r"../Include")
sys.path.append(r"../FmlxDeviceUtils")
clr.AddReference('Formulatrix.Core.Protocol')


class CFmlxPacketSnifferSingle():
    VERSION = '1.0.0'

    def __init__(self, slaveDriver, masterDriver, yamlPath, deviceName, useSinglePrecision=False, loghandler=None, filteredOpcodesList = None ):
        self._logger = logging.getLogger('{0}'.format(deviceName))
        self._logger.setLevel(logging.DEBUG)
        if(loghandler):
            self._logger.addHandler(loghandler)
        self._consoleLogger = logging.getLogger('{0}'.format(deviceName))
        self._consoleLogger.setLevel(logging.INFO)
        self._consoleLogger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.INFO,loggingFormat = '%(asctime)s,%(name)s,%(message)s'))
        self._logger.info('Fmlx Sniffer version : {0}'.format(CFmlxPacketSnifferSingle.VERSION))
        self._consoleLogger.debug('Fmlx Sniffer version : {0}'.format(CFmlxPacketSnifferSingle.VERSION))

        _gen_opfuncs_fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), './generic_opfuncs.yaml')
        self._slaveDriver = slaveDriver
        self._masterDriver = masterDriver
        self._yamlPath = yamlPath
        self._deviceName = deviceName
        self._useSinglePrecision = useSinglePrecision
        self._filteredOpcodes = filteredOpcodesList
        self._list_opcommands, self._list_events = extractYaml(_gen_opfuncs_fpath)
        (list_opcommands, list_events) = extractYaml(yamlPath)
        self._list_opcommands += list_opcommands
        self._list_events += list_events
        
        # convert the opcode list into opcode key based dictionary for faster search process
        self._dict_opcommands = dict()
        self._dict_opevents = dict()
        
        for opcommand in self._list_opcommands:
            self._dict_opcommands.update([(opcommand['op'],[opcommand['name'],opcommand['arg'],opcommand['ret']])])
        for opcommand in self._list_events:
            self._dict_opevents.update([(opcommand['op'],[opcommand['name'],opcommand['ret']])])
        
        self._filteredOpcodes = filteredOpcodesList
        self._ResponseAvaiable = threading.Event()
        self._IsStarted = False
        self._responsePacket = None

    def Start(self):
        self._IsStarted = True
        self._logger.debug('Starting!')
        self._masterDriver.Connect()
        self._slaveDriver.Connect()
        self._masterThreadInstance = threading.Thread(target=self.commandThread)
        self._slaveThreadInstance = threading.Thread(target=self.responseThread)
        self._masterThreadInstance.daemon = True
        self._slaveThreadInstance.daemon = True
        self._masterThreadInstance.start()
        self._slaveThreadInstance.start()
        self._lastOp = None

    def commandThread(self):
        receivedData = []
        hasRemainingData = False
        packetId = None
        while(self._IsStarted):
            if(not hasRemainingData):
                receivedData+=self._masterDriver.Read()
            packet = FormulatrixCorePy.FmlxPacket.FmlxPacket(receivedData,self._useSinglePrecision)

            if(not packet.IsSizePacketReceived):
                # print('1',receivedData)
                hasRemainingData = False
                continue

            if(not packet.IsSizeValid):
                # print('2',receivedData)
                hasRemainingData = False
                continue
            
            if(not packet.IsSizeLegal):
                # print('3',receivedData)
                while(not packet.IsSizeLegal and len(receivedData) >= 2):
                    receivedData = receivedData[2:] # shift until valid data size is found ( < 524 )
                    packet = FormulatrixCorePy.FmlxPacket.FmlxPacket(receivedData,self._useSinglePrecision)
                hasRemainingData = False
                continue

            if(not packet.IsAllDataReceived):
                # print('4',receivedData)
                hasRemainingData = False
                continue
            
            if(not packet.VerifyChecksum()):
                # print('5',receivedData)
                receivedData = receivedData[2:] # shift until valid data found
                hasRemainingData = False
                continue
            
            # print('xxx')
            if(packetId==None):
                packetId = packet.PacketId
            elif(packetId == packet.PacketId):
                self._logger.info('Same Packet ID : {0}'.format(packetId))

            # opname = get_op_name(packet.Opcode,self._list_opcommands)
            # opargs = get_op_args(packet.Opcode,self._list_opcommands)
            if(packet.Opcode in self._dict_opcommands):
                opname = self._dict_opcommands[packet.Opcode][0]
                opargs = self._dict_opcommands[packet.Opcode][1]
            else:
                opname = 'NoneOp:{0}'.format(packet.Opcode)
                oprets = []
            
            commandNames = []
            commandValues = []
            for oparg in opargs:
                commandNames+=[oparg['name']]
                commandValues+=[self.dataFetcher(oparg['type'],packet)]
            
            # print('{0} Command {1} : {2}'.format(self._deviceName,opname,list(zip(names,values))))
            if(not packet.Opcode in self._filteredOpcodes):
                text = '\033[32mPID:{0},\033[36mOP:{1}:CMD,{2},{3}\033[0m'.format(packet.PacketId,packet.Opcode,opname,list(zip(commandNames,commandValues)))
                # print(text)
                self._consoleLogger.info(text)
                self._logger.debug('Command {0} : {1}'.format(opname,list(zip(commandNames,commandValues))))

            receivedData=receivedData[packet.Size+2:]
            if(len(receivedData)>0):
                hasRemainingData = True
            
            if(not self._ResponseAvaiable.wait(self._masterDriver.ReadTimeout/1000)):
                continue
            # self._ResponseAvaiable.wait()
            self._ResponseAvaiable.clear()
            # opname = get_op_name(packet.Opcode,self._list_opcommands)
            # oprets = get_op_rets(packet.Opcode,self._list_opcommands)
            if(packet.Opcode in self._dict_opcommands):
                opname = self._dict_opcommands[packet.Opcode][0]
                oprets = self._dict_opcommands[packet.Opcode][2]
            else:
                opname = 'NoneOp:{0}'.format(packet.Opcode)
                oprets = []
            responseNames = []
            responseValues = []
            for oparg in oprets:
                responseNames+=[oparg['name']]
                responseValues+=[self.dataFetcher(oparg['type'],self._responsePacket)]
            if(packet.Opcode in self._filteredOpcodes):
                continue
            # self._logger.info('Command {0} : {1} <-> Response : {2}'.format(opname,list(zip(commandNames,commandValues)),list(zip(responseNames,responseValues))))
            text = '\033[33m{0}:RSP,{1}:{2}\033[0m'.format(packet.Opcode,opname,list(zip(responseNames,responseValues)))
            # print(text)
            self._consoleLogger.info(text)
            self._logger.debug('Response {0} : {1}'.format(opname,list(zip(responseNames,responseValues))))    
            
            
    def responseThread(self):
        receivedData = []
        hasRemainingData = False
        while(self._IsStarted):
            if(not hasRemainingData):
                receivedData+=self._slaveDriver.Read()
            packet = FormulatrixCorePy.FmlxPacket.FmlxPacket(receivedData,self._useSinglePrecision)
            
            if(not packet.IsSizePacketReceived):
                # print('1',receivedData)
                hasRemainingData = False
                continue
            
            if(not packet.IsSizeValid):
                # print('2',receivedData)
                hasRemainingData = False
                continue
            
            if(not packet.IsSizeLegal):
                # print('3',receivedData)
                while(not packet.IsSizeLegal and len(receivedData) >= 2):
                    receivedData = receivedData[2:] # shift until valid data size is found ( < 524 )
                    packet = FmlxPacket(receivedData,self._useSinglePrecision)
                hasRemainingData = False
                continue

            if(not packet.IsAllDataReceived):
                # print('4',receivedData)
                hasRemainingData = False
                continue
            
            if(not packet.VerifyChecksum()):
                # print('5',receivedData)
                receivedData = receivedData[2:] # shift until valid data found
                hasRemainingData = False
                continue
            
            # event goes here
            if(packet.Opcode >= 512 and packet.Opcode != ctypes.c_uint16(-42).value):
                # opname = get_op_name(packet.Opcode,self._list_events)
                # oprets = get_op_rets(packet.Opcode,self._list_events)
                if(packet.Opcode in self._dict_opevents):
                    opname = self._dict_opevents[packet.Opcode][0]
                    oprets = self._dict_opevents[packet.Opcode][1]
                else:
                    opname = 'NoneOp:{0}'.format(packet.Opcode)
                    oprets = []
                names = []
                values = []
                for opret in oprets:
                    names+=[opret['name']]
                    values+=[self.dataFetcher(opret['type'],packet)]
                if(packet.Opcode in self._filteredOpcodes):
                    continue
                
                str_date = datetime.now().strftime("%Y-%m-%d,%H:%M:%S.%f")[0:-3]
                text = '\033[32mPID:{0},\033[35mOP:{1},EVT,{2}:{3}\033[0m'.format(packet.PacketId,packet.Opcode,opname,list(zip(names,values)))
                # print(text)
                self._consoleLogger.info(text)
                self._logger.debug('Event {0} : {1}'.format(opname,list(zip(names,values))))    
                receivedData=receivedData[packet.Size+2:]
                if(len(receivedData)>0):
                    hasRemainingData = True
                continue

            # print('{0} xxx'.format(self._deviceName))
            self._responsePacket = packet
            self._ResponseAvaiable.set() 
            receivedData=receivedData[packet.Size+2:]
            if(len(receivedData)>0):
                hasRemainingData = True
                
    def dataFetcher(self,dataTypeString,fmlxPacket):
        fethcer_callback_list = {
            'Boolean': fmlxPacket.FetchBool,
            'UInt16': fmlxPacket.FetchUInt16,
            'Int16': fmlxPacket.FetchInt16,
            'UInt32': fmlxPacket.FetchUInt32,
            'Int32': fmlxPacket.FetchInt32,
            'Double': fmlxPacket.FetchDouble,
            'String': fmlxPacket.FetchString,

            # Array with count
            'Array_UInt16_c': fmlxPacket.FetchUInt16,
            'Array_Int16_c': fmlxPacket.FetchInt16,
            'Array_UInt32_c': fmlxPacket.FetchUInt32,
            'Array_Int32_c': fmlxPacket.FetchInt32,
            'Array_Double_c': fmlxPacket.FetchDouble,
            'Array_Boolean_c': fmlxPacket.FetchBoolArray,

            # Array without count
            'Array_UInt16': fmlxPacket.FetchUInt16,
            'Array_Int16': fmlxPacket.FetchInt16,
            'Array_UInt32': fmlxPacket.FetchUInt32,
            'Array_Int32': fmlxPacket.FetchInt32,
            'Array_Double': fmlxPacket.FetchDouble,
            'Array_Boolean': fmlxPacket.FetchBoolArray
        }
        try:
            return fethcer_callback_list[dataTypeString]()
        except IndexError:
            return 'Not Enough data to parse {0}'.format(dataTypeString)

class CFmlxPacketSniffer():

    def Execute(self):
        self.executeMaster()
        self.executeSlave()

    def executeSlave(self):
        for i in range(self.__drivers_count):
            if(self.__slave_driver[i].BytesInReadQueue != 0):
                self.__dataBufferSlave[i] += self.__slave_driver[i].Read(
                    self.__slave_driver[i].BytesInReadQueue)

            if(self.__dataBufferSlave[i] == []):
                continue
            if(sys.version_info[0] < 3):
                if(((time.clock() - self.__masterCmdTimeoutTimer[i])>1) and (self.__masterCmdTimeout[i]==False)):
                    self.__masterCmdTimeout[i] = True
                    print ('{0} --> Timeout! ( >1s ) '.format(self.__masterLogText[i]))
            else:
                if(((time.perf_counter() - self.__masterCmdTimeoutTimer[i])>1) and (self.__masterCmdTimeout[i]==False)):
                    self.__masterCmdTimeout[i] = True
                    print ('{0} --> Timeout! ( >1s ) '.format(self.__masterLogText[i]))
            
            
            # check whether the data lenght is eligible
            if((len(self.__dataBufferSlave[i])-2) < self.__SlaveDataParser.get_packet_size(self.__dataBufferSlave[i])):
                continue
            
            packet_id = self.__SlaveDataParser.get_packet_id(self.__dataBufferSlave[i])

            op = self.__SlaveDataParser.get_packet_opcode(
                self.__dataBufferSlave[i])

            self.__SlaveDataParser.reset_last_integer()

            if(op < 512):
                self.__masterCmdTimeout[i] = True
                if(len(self.__bufferedSlaveRspnData[i]) > 0):
                    data = self.__bufferedSlaveRspnData[i]
                    self.__bufferedSlaveRspnData[i] = []
                else:
                    data = self.__SlaveDataParser.get_packet_data(
                        self.__dataBufferSlave[i])

                try:
                    last_opcode = self.__last_command_opcode[i].pop(0)
                except IndexError:
                    if(packet_id!=self.__last_slave_packet_id[i]):
                        # print 'haha'
                        self.__last_slave_packet_id[i] = packet_id
                        self.__bufferedSlaveRspnData[i] = data
                    # print self.__bufferedSlaveRspnData[i]
                    # else:
                    #     print 'same id',packet_id,self.__last_slave_packet_id[i]
                    continue
                
                opname = get_op_name(
                    last_opcode, self.__list_opcommands[i])
                oprets = get_op_rets(
                    last_opcode, self.__list_opcommands[i])
                name = []
                value = []
                for opret in oprets:
                    name += [opret['name']]
                    data, retvalue = self.__SlaveDataParser.parse_data_funcs[opret['type']](
                        data)
                    value += [retvalue]

                interval_time = time.time() - self.__masterCmdTimestamp[i]
                string_value = ' \033[31m<----> \033[33m+{:0.3f} rspn:('.format(
                    interval_time)

                l = len(oprets)
                for j in range(l):
                    if(name[j] == None):
                        break
                    string_value += name[j]
                    string_value += ': '
                    string_value += str(value[j])
                    if(j < (l-1)):
                        string_value += ','
                string_value += ')'

                self.__masterLogText[i] += string_value
                # print (last_opcode,self.__filtered_opcode[i])
                if(last_opcode in self.__filtered_opcode[i]):
                    pass
                else:
                    print (self.__masterLogText[i])
                    if(self.__file):
                        self.__file.write(self.__masterLogText[i])
                        self.__file.write('\n')

            # events
            else:
                data = self.__SlaveDataParser.get_packet_data(
                    self.__dataBufferSlave[i])
                opname = get_op_name(op, self.__list_events[i])
                oprets = get_op_rets(op, self.__list_events[i])
                name = []
                value = []
                for opret in oprets:
                    name += [opret['name']]
                    data, retvalue = self.__SlaveDataParser.parse_data_funcs[opret['type']](
                        data)
                    value += [retvalue]

                string_value = '('
                l = len(oprets)
                for j in range(l):
                    if(name[j] == None):
                        break
                    string_value += name[j]
                    string_value += ': '
                    string_value += str(value[j])
                    if(j < (l-1)):
                        string_value += ','
                string_value += ')'

                str_date = datetime.now().strftime(
                    "%Y-%m-%d,%H:%M:%S.%f")[0:-3]
                text = '\033[32m{1},{0} \033[35m{4}:evnt<--{2}:{3}'.format(
                    self.__device_name[i], str_date, opname, string_value, op)
                print (text)
                if(self.__file):
                    self.__file.write(text)
                    self.__file.write('\n')

            data_read = self.__SlaveDataParser.get_packet_size(
                self.__dataBufferSlave[i]) + 2
            self.__dataBufferSlave[i] = self.__dataBufferSlave[i][data_read:]

    def executeMaster(self):
        for i in range(self.__drivers_count):

            if(self.__master_driver[i].BytesInReadQueue != 0):
                self.__dataBufferMaster[i] += self.__master_driver[i].Read(
                    self.__master_driver[i].BytesInReadQueue)

            # check whether the data lenght is eligible
            if((len(self.__dataBufferMaster[i])-2) < self.__MasterDataParser.get_packet_size(self.__dataBufferMaster[i])):
                continue

            self.__masterCmdTimeout[i] = False

            packet_id = self.__MasterDataParser.get_packet_id(
                self.__dataBufferMaster[i])

            opcode = self.__MasterDataParser.get_packet_opcode(
                self.__dataBufferMaster[i])

            same_packet_id = False
            # this line is to handle retry count, for example at save_configuration
            if(self.__last_master_packet_id[i] != packet_id):
                self.__last_master_packet_id[i] = packet_id
                self.__last_command_opcode[i].append(opcode)
                if(sys.version_info[0] < 3):
                    self.__masterCmdTimeoutTimer[i] = time.clock()
                else:
                    self.__masterCmdTimeoutTimer[i] = time.perf_counter()
            else:
                same_packet_id = True
                # print ('warning, same packet id! pid:{0}, opcode:{1}, name:{2}'.format(packet_id,opcode,self.get_op_name(opcode, self.__list_opcommands[i])))

            data = self.__MasterDataParser.get_packet_data(
                self.__dataBufferMaster[i])
            opname = get_op_name(opcode, self.__list_opcommands[i])
            opargs = get_op_args(opcode, self.__list_opcommands[i])
            name = []
            value = []
            for oparg in opargs:
                name += [oparg['name']]
                data, retvalue = self.__MasterDataParser.parse_data_funcs[oparg['type']](
                    data)
                self.__prevDataMaster = retvalue
                value += [retvalue]

            string_value = '('
            l = len(opargs)
            for j in range(l):
                if(name[j] == None):
                    break
                string_value += name[j]
                string_value += ': '
                string_value += str(value[j])
                if(j < (l-1)):
                    string_value += ','
            string_value += ')'
            str_date = datetime.now().strftime("%Y-%m-%d,%H:%M:%S.%f")[0:-3]
            text = '\033[32m{1},{0} \033[36m{4}:cmd:{2}:{3} , pid :{5}'.format(
                self.__device_name[i], str_date, opname, string_value, opcode,packet_id)
            if(same_packet_id == True):
                print ('{0} --> warning, same packet id! '.format(text))
            self.__masterLogText[i] = text
            self.__masterCmdTimestamp[i] = time.time()
            data_read = self.__MasterDataParser.get_packet_size(
                self.__dataBufferMaster[i]) + 2
            self.__dataBufferMaster[i] = self.__dataBufferMaster[i][data_read:]

    def __init__(self, driver_count, slave_driver, master_driver, yaml_path, device_name,useSinglePrecision=False, log_file_path=None, filtered_opcode = None ):
        if(driver_count != len(slave_driver)):
            raise Exception('driver count :{0}, meanwhile slave driver count :{1}'.format(
                driver_count, len(slave_driver)))
        if(driver_count != len(master_driver)):
            raise Exception('driver count :{0}, meanwhile master driver count :{1}'.format(
                driver_count, len(master_driver)))
        if(driver_count != len(yaml_path)):
            raise Exception('driver count :{0}, meanwhile yaml count :{1}'.format(
                driver_count, len(yaml_path)))
        if(driver_count != len(device_name)):
            raise Exception('driver count :{0}, meanwhile device name count :{1}'.format(
                driver_count, len(device_name)))
        print ('fmlx wireshark')
        if(log_file_path != None):
            print ('log file path :', log_file_path)
        print ('devices list :', device_name)

        _gen_opfuncs_fpath = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), './generic_opfuncs.yaml')
        self.__drivers_count = driver_count
        self.__bufferedSlaveRspnData = [[]]
        self.__dataBufferSlave = [[]]
        self.__dataBufferMaster = [[]]
        self.__last_command_opcode = [[]]
        self.__list_opcommands = [{}]
        self.__list_events = [{}]
        self.__filtered_opcode = [[]]

        for i in range(self.__drivers_count):
            self.__bufferedSlaveRspnData.append([])
            self.__dataBufferSlave.append([])
            self.__dataBufferMaster.append([])
            self.__last_command_opcode.append([])
            self.__list_opcommands.append({})
            self.__list_events.append({})
            self.__filtered_opcode.append([])

        self.__slave_driver = []
        self.__master_driver = []
        self.__prevDataSlave = 0
        self.__prevDataMaster = 0
        self.__SlaveDataParser = CDataParser(useSinglePrecision)
        self.__MasterDataParser = CDataParser(useSinglePrecision)
        self.__device_name = []
        self.__masterLogText = [''] * self.__drivers_count
        self.__masterCmdTimestamp = [0] * self.__drivers_count
        self.__masterCmdTimeoutTimer = [0] * self.__drivers_count
        self.__masterCmdTimeout = [False] * self.__drivers_count
        self.__last_master_packet_id = [None] * self.__drivers_count
        self.__last_slave_packet_id = [None] * self.__drivers_count

        # extract generic opfunc first
        i = 0
        for i in range(self.__drivers_count):
            self.__slave_driver += [slave_driver[i]]
            self.__master_driver += [master_driver[i]]
            self.__device_name += [device_name[i]]
            (self.__list_opcommands[i], self.__list_events[i]) = extractYaml(
                _gen_opfuncs_fpath)

        # then extract device specific opfunc
        i = 0
        list_opcommands = {}
        list_events = {}
        for i in range(self.__drivers_count):
            self.__slave_driver += [slave_driver[i]]
            self.__master_driver += [master_driver[i]]
            self.__device_name += [device_name[i]]
            (list_opcommands, list_events) = extractYaml(yaml_path[i])
            self.__list_opcommands[i] += list_opcommands
            self.__list_events[i] += list_events
        if(filtered_opcode != None):
            for index,filters in enumerate(filtered_opcode):    
                self.__filtered_opcode[index] +=filters

        # print (self.__filtered_opcode[0])

        self.__file = None
        if(log_file_path != None):
            i = 0
            while(1):
                incFilename = '{}{}.txt'.format(log_file_path, i)
                if(os.path.isfile(incFilename)):
                    i += 1
                else:
                    break
            else:
                incFilename = '{}.txt'.format(log_file_path)
            self.__file = open(incFilename, 'w')

    def __del__(self):
        self.__file.close()
        print ('bye!')

class CDataParser:
    # def generate_fmlxpacket(self,payload):
    #     p = FmlxPacket
    #     if len(payload) < 2 or len(payload) % 2 > 0:
    #         return p
    #     for i in range(0, len(payload), 2):
    #         i16, = struct.unpack('H', bytearray([payload[i], payload[i + 1]]))
    #         try:
    #             p.Add(UInt16(i16))
    #         except:
    #             pass
    #     return p

    def reset_last_integer(self):
        self.__last_integer_data_value = 0

    def fetch_data_Boolean(self, data):
        if(len(data) < 2):
            return [], '\033[31mnot enough data to parse boolean\033[33m'
        return data[2:], bool(struct.unpack('H', bytearray([data[0], data[1]]))[0])

    def fetch_data_UInt16(self, data):
        if(len(data) < 2):
            return [], '\033[31mnot enough data to parse uint16\033[33m'
        if(self.__update_integer_value):
            self.__last_integer_data_value = struct.unpack(
                'H', bytearray([data[0], data[1]]))[0]
            return data[2:], self.__last_integer_data_value
        return data[2:], struct.unpack('H', bytearray([data[0], data[1]]))[0]

    def fetch_data_Int16(self, data):
        if(len(data) < 2):
            return [], '\033[31mnot enough data to parse int16\033[33m'
        if(self.__update_integer_value):
            self.__last_integer_data_value = struct.unpack(
                'H', bytearray([data[0], data[1]]))[0]
            return data[2:], self.__last_integer_data_value
        return data[2:], struct.unpack('H', bytearray([data[0], data[1]]))[0]

    def fetch_data_UInt32(self, data):
        if(len(data) < 4):
            return [], '\033[31mnot enough data to parse uint32\033[33m'
        return data[4:], struct.unpack('L', bytearray([data[0], data[1], data[2], data[3]]))[0]

    def fetch_data_Int32(self, data):
        if(len(data) < 4):
            return [], '\033[31mnot enough data to parse int32\033[33m'
        return data[4:], struct.unpack('i', bytearray([data[0], data[1], data[2], data[3]]))[0]

    def fetch_data_Double(self, data):
        if(not self._isSinglePrecision):
            if(len(data) < 8):
                return [], '\033[31mnot enough data to parse double\033[33m'
            # print data
            return data[8:], struct.unpack('d', bytearray([data[0], data[1], data[2], data[3], data[4], data[5],  data[6], data[7]]))[0]
        else:
            if(len(data) < 4):
                return [], '\033[31mnot enough data to parse int32\033[33m'
            return data[4:], struct.unpack('f', bytearray([data[0], data[1], data[2], data[3]]))[0]
    
    def fetch_data_array(self, type, count, data):
        # exhaust data fetching until end of packet
        retValue = []
        self.__update_integer_value = 0
        if count <= 0:
            while(len(data) > 0):
                data, value = self.parse_data_funcs[type](data)
                retValue += [value]
        # based on count
        else:
            for i in range(count):
                data, value = self.parse_data_funcs[type](data)
                retValue += [value]
        self.__update_integer_value = 1
        return data, retValue

    def fetch_data_array_UInt16_c(self, data):
        return self.fetch_data_array('UInt16', self.__last_integer_data_value, data)

    def fetch_data_array_Int16_c(self, data):
        return self.fetch_data_array('Int16', self.__last_integer_data_value, data)

    def fetch_data_array_UInt32_c(self, data):
        return self.fetch_data_array('UInt32', self.__last_integer_data_value, data)

    def fetch_data_array_Int32_c(self, data):
        return self.fetch_data_array('Int32', self.__last_integer_data_value, data)

    def fetch_data_array_Double_c(self, data):
        return self.fetch_data_array('Double', self.__last_integer_data_value, data)

    def fetch_data_array_Boolean_c(self, data):
        return self.fetch_data_array('Boolean', self.__last_integer_data_value, data)

    def fetch_data_array_UInt16(self, data):
        return self.fetch_data_array('UInt16', self.__last_integer_data_value, data)

    def fetch_data_array_Int16(self, data):
        return self.fetch_data_array('Int16', self.__last_integer_data_value, data)

    def fetch_data_array_UInt32(self, data):
        return self.fetch_data_array('UInt32', self.__last_integer_data_value, data)

    def fetch_data_array_Int32(self, data):
        return self.fetch_data_array('Int32', self.__last_integer_data_value, data)

    def fetch_data_array_Double(self, data):
        return self.fetch_data_array('Double', self.__last_integer_data_value, data)

    def fetch_data_array_Boolean(self, data):
        return self.fetch_data_array('Boolean', self.__last_integer_data_value, data)

    def fetch_data_String(self, data):
        if(len(data) < 2):
            return [], ''
        char_value = 0xff
        string_value = ''
        data_count = 0
        self.__update_integer_value = 0
        while(char_value != 0):
            data_count += 1
            data, char_value = self.fetch_data_UInt16(data)
            if(char_value != 0):
                string_value += chr(char_value)
        self.__update_integer_value = 1
        return data[2*data_count:], string_value

    def get_packet_size(self, buffer):
        if(len(buffer) < 2):
            return 0
        return buffer[0] | buffer[1] << 8

    def get_packet_opcode(self, buffer):
        if len(buffer) >= 12:
            return buffer[10] | buffer[11] << 8
        return 0

    def get_packet_id(self, buffer):
        if len(buffer) >= 6:
            return buffer[4] | buffer[5] << 8
        return 0

    def get_packet_data(self, buffer):
        packet_size = self.get_packet_size(buffer)
        if(packet_size == 0):
            return []
        # print len(buffer), packet_size
        num_of_data = len(buffer) - 14
        if(num_of_data == 0):
            return []
        return buffer[12:-2]

    def getFieldSeqId(self, datagram):
        if len(datagram) >= 4:
            return datagram[2] | datagram[3] << 8
        return 0

    def getFieldRsv(self, datagram):
        if len(datagram) >= 8:
            return datagram[6] | datagram[7] << 8
        return 0

    def getFieldAddr(self, datagram):
        if len(datagram) >= 10:
            return datagram[8] | datagram[9] << 8
        return 0

    def getFieldData(self, datagram):
        fld_len = self.get_packet_size(datagram)
        if self.get_packet_size(datagram) <= 12:
            return []
        else:
            if len(datagram) < 14:
                return []
            elif len(datagram) >= fld_len + 2:
                return datagram[12:]
        return []

    def getFieldChecksum(self, datagram):
        fld_len = self.get_packet_size(datagram)
        if fld_len == 0:
            return 0
        if fld_len == 12:
            return datagram[-4] | datagram[-6] << 8
        elif len > 12:
            data = self.getFieldData(datagram)
            if len(data) > 0:
                return datagram[-4] | datagram[-6] << 8
        return 0

    def __init__(self,useSinglePrecision = False):
        self.__last_integer_data_value = 0
        self.__update_integer_value = 1
        self._isSinglePrecision = useSinglePrecision
        self.parse_data_funcs = {
            'Boolean': self.fetch_data_Boolean,
            'UInt16': self.fetch_data_UInt16,
            'Int16': self.fetch_data_Int16,
            'UInt32': self.fetch_data_UInt32,
            'Int32': self.fetch_data_Int32,
            'Double': self.fetch_data_Double,
            'String': self.fetch_data_String,

            # Array with count
            'Array_UInt16_c': self.fetch_data_array_UInt16_c,
            'Array_Int16_c': self.fetch_data_array_Int16_c,
            'Array_UInt32_c': self.fetch_data_array_UInt32_c,
            'Array_Int32_c': self.fetch_data_array_Int32_c,
            'Array_Double_c': self.fetch_data_array_Double_c,
            'Array_Boolean_c': self.fetch_data_array_Boolean_c,

            # Array without count
            'Array_UInt16': self.fetch_data_array_UInt16,
            'Array_Int16': self.fetch_data_array_Int16,
            'Array_UInt32': self.fetch_data_array_UInt32,
            'Array_Int32': self.fetch_data_array_Int32,
            'Array_Double': self.fetch_data_array_Double,
            'Array_Boolean': self.fetch_data_array_Boolean,
        }

class CYamlParser():
    def extractYaml(self,filepath):
        """ Extract opcode functions lists from YAML files
        ....Parameters:
        ....filepath -- path to YAML file that contain list of opcode functions
        ...."""

        opCommands = []
        opEvents = []
        opPublisher = []
        if filepath:
            # device opfuncs path is specified
            with open(filepath, 'r') as opfuncs_file:
                opfuncs_list = yaml.load(
                    opfuncs_file.read(), Loader=yaml.FullLoader)
                if 'COMMANDS' in opfuncs_list:
                    opCommands += self.extractOpfuncs(opfuncs_list['COMMANDS'])
                if 'EVENTS' in opfuncs_list:
                    opEvents += self.extractOpfuncs(opfuncs_list['EVENTS'])
                if 'PUBLISHER' in opfuncs_list:
                    opPublisher += self.extractOpfuncs(opfuncs_list['PUBLISHER'])
                return (opCommands, opEvents, opPublisher)
        return [], [], []

    def get_op_name(self,opcode, list_opcodes):
        for item in list_opcodes:
            if int(opcode) == int(item['op']):
                return item['name']
        return ''

    def get_op_rets(self,opcode, list_opcodes):
        for item in list_opcodes:
            if int(opcode) == int(item['op']):
                return item['ret']
        return {}

    def get_op_args(self,opcode, list_opcodes):
        for item in list_opcodes:
            if int(opcode) == int(item['op']):
                return item['arg']
        return {}

    def extractOpfuncs(self,items, depth=0):
        """ Extract opfunc items and convert them into structured py dictionaries
        ....Parameters:
        ....items  -- list of opfunc items from YAML conversion
        ....depth  -- current subitem level inside opfunc list (check
        ........................the opfunction's YAML format)

        ....Opfunction Dictionary Schema:
        ....opfunc = {
        ............'op'   : opcode
        ............'name' : opfunction_name
        ............'arg'  : [ {'name': argument_name, 'type' : argument_data_type}, ... ]
        ............'ret'  : [ {'name': func_return_name, 'type' : func_return_data_type}, ... ]
        ....}
        ....note : null value will be replaced by empty list
        ...."""

        if items is None:
            return []

        # check if items only contain single item or is a opfunc description

        if not hasattr(items, '__len__') or isinstance(items, str):
            return items

        # process items based on current item depth level

        items_binder = []
        item_dict = {}
        for item in items:
            key_name = (list(item)[0])
            if depth == 0:
                # top level (opfunc name)
                item_dict = {}
                item_dict['name'] = key_name
                item_dict.update(self.extractOpfuncs(item[key_name], 1))
                items_binder.append(item_dict)
            elif depth == 1:
                # opfunc attribute levels
                item_dict[key_name] = self.extractOpfuncs(item[key_name], 2)
                items_binder = item_dict
            elif depth == 2:
                # arg and return list level
                item_dict = {}
                item_dict['name'] = key_name
                item_dict['type'] = item[key_name]
                items_binder.append(item_dict)
        return items_binder

class CDataConstructor:
    def __init__(self):
        self.parse_data_funcs = {
            'Boolean': self.add_boolean,
            'UInt16': self.add_uint16,
            'Int16': self.add_int16,
            'UInt32': self.add_uint32,
            'Int32': self.add_int32,
            'Double': self.add_double,
        }
    
    def add_boolean(self,value):
        value = list(bytearray(struct.pack("H", value))) 
        return [value[1]<<8 | value[0]]

    def add_uint16(self,value):
        value = list(bytearray(struct.pack("H", value)))
        return [value[1]<<8 | value[0]] 
    
    def add_int16(self,value):
        value = list(bytearray(struct.pack("h", value)))
        return [value[1]<<8 | value[0]] 
    
    def add_int32(self,value):
        value = list(bytearray(struct.pack("i", value))) 
        return [value[1]<<8 | value[0],value[3]<<8 | value[2]]

    def add_uint32(self,value):
        value = list(bytearray(struct.pack("I", value))) 
        return [value[1]<<8 | value[0],value[3]<<8 | value[2]]

    def add_double(self,value):
        value = list(bytearray(struct.pack("d", value))) 
        return [value[1]<<8 | value[0],value[3]<<8 | value[2],value[5]<<8 | value[4],value[7]<<8 | value[6]]

def extractYaml(filepath):
    """ Extract opcode functions lists from YAML files
    ....Parameters:
    ....filepath -- path to YAML file that contain list of opcode functions
    ...."""

    opCommands = []
    opEvents = []
    if filepath:
        # device opfuncs path is specified
        with open(filepath, 'r') as opfuncs_file:
            opfuncs_list = yaml.load(
                opfuncs_file.read(), Loader=yaml.FullLoader)
            if 'COMMANDS' in opfuncs_list:
                opCommands += extractOpfuncs(opfuncs_list['COMMANDS'])
            if 'EVENTS' in opfuncs_list:
                opEvents += extractOpfuncs(opfuncs_list['EVENTS'])
            return (opCommands, opEvents)
    return [], []

def get_op_name(opcode, list_opcodes):
    for item in list_opcodes:
        if int(opcode) == int(item['op']):
            return item['name']
    return ''

def get_op_rets(opcode, list_opcodes):
    for item in list_opcodes:
        if int(opcode) == int(item['op']):
            return item['ret']
    return {}

def get_op_args(opcode, list_opcodes):
    for item in list_opcodes:
        if int(opcode) == int(item['op']):
            return item['arg']
    return {}

def extractOpfuncs(items, depth=0):
    """ Extract opfunc items and convert them into structured py dictionaries
    ....Parameters:
    ....items  -- list of opfunc items from YAML conversion
    ....depth  -- current subitem level inside opfunc list (check
    ........................the opfunction's YAML format)

    ....Opfunction Dictionary Schema:
    ....opfunc = {
    ............'op'   : opcode
    ............'name' : opfunction_name
    ............'arg'  : [ {'name': argument_name, 'type' : argument_data_type}, ... ]
    ............'ret'  : [ {'name': func_return_name, 'type' : func_return_data_type}, ... ]
    ....}
    ....note : null value will be replaced by empty list
    ...."""

    if items is None:
        return []

    # check if items only contain single item or is a opfunc description

    if not hasattr(items, '__len__') or isinstance(items, str):
        return items

    # process items based on current item depth level

    items_binder = []
    item_dict = {}
    for item in items:
        key_name = (list(item)[0])
        if depth == 0:
            # top level (opfunc name)
            item_dict = {}
            item_dict['name'] = key_name
            item_dict.update(extractOpfuncs(item[key_name], 1))
            items_binder.append(item_dict)
        elif depth == 1:
            # opfunc attribute levels
            item_dict[key_name] = extractOpfuncs(item[key_name], 2)
            items_binder = item_dict
        elif depth == 2:
            # arg and return list level
            item_dict = {}
            item_dict['name'] = key_name
            item_dict['type'] = item[key_name]
            items_binder.append(item_dict)
    return items_binder

