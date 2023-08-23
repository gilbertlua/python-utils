import sys
import os
from FmlxWireshark import CFmlxPacketSniffer,CDataParser,CYamlParser
import argparse

def getPath(isLoad=True, window_title=None):
    if(sys.version_info[0] >= 3):
        import tkinter as tk
        from tkinter import filedialog
    else:
        import Tkinter as tk
        import tkFileDialog as filedialog

    root = tk.Tk()
    root.withdraw()
    if(isLoad):
        return filedialog.askopenfilename(title=window_title)
    else:
        return filedialog.asksaveasfile(title=window_title).name

# command line argument to config this script
parser = argparse.ArgumentParser(description="Formulatrix RawData2FmlxProtocolConverter")
parser.add_argument('-y', '--yamlPath',
                    help="yaml file path", type=str, nargs='?')
parser.add_argument('-l', '--logFilePath',
                    help="log file path", type=str, nargs='?')
parser.add_argument('-a', '--address', help="app FmlxProtocol address (busId)", type=int)
parser.add_argument('-s', '--saveLog', help="save log data", action='store_true')
    
args = parser.parse_args()
if(not args.address):
    address = int(input('your device address :'))
else:
    address = args.address
# address = 15
# address = 1

if(not args.yamlPath):
    yaml_path = getPath(1,'your yaml path')
else:
    yaml_path = args.yamlPath
# yaml_path = 'd:\ElectronicSVN\Supporting Products\Script\DeviceOpfuncs\wambo_trinamic.yaml'
# yaml_path = 'd:\\ElectronicSVN\\Supporting Products\\Script\\DeviceOpfuncs\\nighthawk.yaml'

if(not args.logFilePath):
    log_file_path = getPath(1,'your log files')
else:
    log_file_path = args.logFilePath
# log_file_path = 'd:/log/wamic kvaser log file.txt'
# log_file_path = 'd:/log/candump file.txt'

list_opcommands = {}
list_events = {}
# extract generic opfunc first
yamlParser = CYamlParser()
(list_opcommands, list_events,list_pub) = yamlParser.extractYaml('generic_opfuncs.yaml')

# then extract device specific opfunc
temp_opcommands = {}
temp_events = {}    
(temp_opcommands, temp_events,list_pub) = yamlParser.extractYaml(yaml_path)
list_opcommands += temp_opcommands
list_events += temp_events
slaveDataParser = CDataParser()
masterDataParser = CDataParser()

CAN_ID_INDEX = 0
TIMESTAMP_INDEX = 0
DLC_INDEX = 0
DATA_INDEX = 0
is_hex = False
data_type = None
file_buffer = ''
with open(log_file_path,'rb') as f:
    sample = f.readline()
    if('can' in str(sample)):
        sample_split = sample.split()
        if('can' in str(sample_split[0])):
            print('candump data type without timestamp')
            CAN_ID_INDEX = 1
            DLC_INDEX = 2
            DATA_INDEX = 3
            TIMESTAMP_INDEX = None
            is_hex = True
            data_type = 'candump'
        else:
            print('candump data type with timestamp')
            CAN_ID_INDEX = 2
            DLC_INDEX = 3
            DATA_INDEX = 4
            TIMESTAMP_INDEX = 0
            is_hex = True
            data_type = 'candump'
    else:
        print('kvaser data type')
        CAN_ID_INDEX = 1
        DLC_INDEX = 2
        DATA_INDEX = 3
        TIMESTAMP_INDEX = -2
        is_hex = False
        data_type = 'kvaser'

with open(log_file_path,'rb') as f:
    master_buffer = []
    slave_buffer = []
    for line in f:
        line_string = line.split()
        if(not is_hex):
            can_id = int(line_string[CAN_ID_INDEX])
        else:
            can_id = int(line_string[CAN_ID_INDEX],16)

        # check if it's for master
        if( (can_id-0x600) == address):
            if(data_type == 'kvaser'):
                dlc = int(line_string[DLC_INDEX])
            elif(data_type == 'candump'):
                dlc = line_string[DLC_INDEX][1] - 48
            if(dlc>0):
                if(not is_hex):    
                    master_buffer += [int(x) for x in line_string[DATA_INDEX:DATA_INDEX+dlc]]
                    master_timestamp = float(line_string[TIMESTAMP_INDEX])
                else:
                    master_buffer += [int(x,16) for x in line_string[DATA_INDEX:DATA_INDEX+dlc]]
                    if(data_type == 'kvaser'):
                        master_timestamp = float(line_string[TIMESTAMP_INDEX])
                    elif(data_type == 'candump'):
                        master_timestamp = float(line_string[TIMESTAMP_INDEX][2:-2])
                    
        # for slave
        elif( (can_id-0x580) == address):
            if(data_type == 'kvaser'):
                dlc = int(line_string[DLC_INDEX])
            elif(data_type =='candump'):
                dlc = line_string[DLC_INDEX][1] - 48
            if(dlc>0):
                if(not is_hex):
                    slave_buffer += [int(x) for x in line_string[DATA_INDEX:DATA_INDEX+dlc]]
                    slave_timestamp = float(line_string[TIMESTAMP_INDEX])
                else:
                    slave_buffer += [int(x,16) for x in line_string[DATA_INDEX:DATA_INDEX+dlc]]
                    if(data_type == 'kvaser'):
                        slave_timestamp = float(line_string[TIMESTAMP_INDEX])
                    elif(data_type == 'candump'):
                        slave_timestamp = float(line_string[TIMESTAMP_INDEX][2:-2])

        size = masterDataParser.get_packet_size(master_buffer)
        if(size!=0 and len(master_buffer)>=(size+2)):
            master_data = master_buffer[:size+2]
            master_buffer = master_buffer[size+2:]
            packet_id = masterDataParser.get_packet_id(master_data)
            opcode = masterDataParser.get_packet_opcode(master_data)
            data = masterDataParser.get_packet_data(master_data)  
            opname = yamlParser.get_op_name(opcode, list_opcommands)
            opargs = yamlParser.get_op_args(opcode, list_opcommands)
            name = []
            value = [] 
            for oparg in opargs:
                name += [oparg['name']]
                data, retvalue = masterDataParser.parse_data_funcs[oparg['type']](data)
                value += [retvalue]
            arg_string_value = '('
            l = len(opargs)
            for j in range(l):
                if(name[j] == None):
                    break
                arg_string_value += '{0}: {1}'.format(name[j],str(value[j]))
                if(j < (l-1)):
                    arg_string_value += ','
            arg_string_value += ')'
            string_value = '{0} pid:{1} op:{2} cmd:{3}:{4}'.format(round(master_timestamp,3),packet_id, opcode, opname,arg_string_value)
            
        size = slaveDataParser.get_packet_size(slave_buffer)
        if(size!=0 and len(slave_buffer)>=(size+2)):
            slave_data = slave_buffer[:size+2]
            slave_buffer = slave_buffer[size+2:]
            packet_id = slaveDataParser.get_packet_id(slave_data)
            opcode_slave = slaveDataParser.get_packet_opcode(slave_data)
            name = []
            value = []  
            if(opcode_slave<512):   
                data = slaveDataParser.get_packet_data(slave_data)  
                opname = yamlParser.get_op_name(opcode, list_opcommands)
                oprets = yamlParser.get_op_rets(opcode, list_opcommands)
    
                for opret in oprets:
                    name += [opret['name']]
                    data, retvalue = slaveDataParser.parse_data_funcs[opret['type']](data)
                    value += [retvalue]

                arg_string_value = '('
                l = len(oprets)
                for j in range(l):
                    if(name[j] == None):
                        break
                    arg_string_value += '{0}: {1}'.format(name[j],str(value[j]))
                    if(j < (l-1)):
                        arg_string_value += ','
                arg_string_value += ')'
                string_value += '<-->rsp:{0} delay:{1}'.format(arg_string_value,round(slave_timestamp-master_timestamp,3))
                print(string_value)
                file_buffer += string_value +'\n'
            else:
                data = slaveDataParser.get_packet_data(slave_data)  
                opname = yamlParser.get_op_name(opcode_slave, list_events)
                oprets = yamlParser.get_op_rets(opcode_slave, list_events)
                for opret in oprets:
                    name += [opret['name']]
                    data, retvalue = slaveDataParser.parse_data_funcs[opret['type']](data)
                    value += [retvalue]

                arg_string_value = '('
                l = len(oprets)
                for j in range(l):
                    if(name[j] == None):
                        break
                    arg_string_value += '{0}: {1}'.format(name[j],str(value[j]))
                    if(j < (l-1)):
                        arg_string_value += ','
                arg_string_value += ')'
                evt_string_value = '{0} pid:{1} op:{2} evt:{3}:{4}'.format(slave_timestamp,packet_id, opcode_slave, opname,arg_string_value)
                print(evt_string_value)
                file_buffer += evt_string_value +'\n'

if(args.saveLog):
    print('Saving..')
    path = getPath(False,'Save your data..')
    # print(path)
    with open(path,'w') as f:
        f.write(file_buffer)
    print('Saved to {0}'.format(path))
else:
    pass