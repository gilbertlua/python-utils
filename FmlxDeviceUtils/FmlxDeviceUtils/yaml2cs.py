import yaml
import argparse
import sys
import os
from operator import itemgetter
from collections import OrderedDict
# to easily parse the path, to get the filename
import ntpath
ntpath.basename("a/b/c")

commands = []
events = []
enums = []


def stringTabLevel(level):
    return '\t'*level


def handle_file(filepath):
    global commands, events, enums
    """ Extract opcode functions lists from YAML files
    Parameters:
    filepath -- path to YAML file that contain list of opcode functions
    """
    if filepath:
        # device opfuncs path is specified
        with open(filepath, 'r') as opfuncs_file:
            opfuncs_list = yaml.load(opfuncs_file.read())

            if 'COMMANDS' in opfuncs_list:
                commands += extract_opfuncs(opfuncs_list['COMMANDS'])

            if 'EVENTS' in opfuncs_list:
                events += extract_opfuncs(opfuncs_list['EVENTS'])


def extract_opfuncs(items, depth=0):
    """ Extract opfunc items and convert them into structured py dictionaries
    Parameters:
    items  -- list of opfunc items from YAML conversion
    depth  -- current subitem level inside opfunc list (check 
                the opfunction's YAML format)

    Opfunction Dictionary Schema:
    opfunc = { 
        'op'   : opcode
        'name' : opfunction_name
        'arg'  : [ {'name': argument_name, 'type' : argument_data_type}, ... ]
        'ret'  : [ {'name': func_return_name, 'type' : func_return_data_type}, ... ]
    }
    note : null value will be replaced by empty list
    """
    if items is None:
        return []

    # check if items only contain single item or is a opfunc description
    if (not hasattr(items, '__len__')) or (isinstance(items, str)):
        return items

    # print (items)

    # process items based on current item depth level
    items_binder = []
    item_dict = {}
    for item in items:
        key_name = (list(item)[0])
        # print (key_name)
        if depth == 0:
            # top level (opfunc name)
            item_dict = {}
            item_dict['name'] = key_name
            item_dict.update(extract_opfuncs(item[key_name], 1))
            items_binder.append(item_dict)

        elif depth == 1:
            # opfunc attribute levels
            item_dict[key_name] = extract_opfuncs(item[key_name], 2)
            items_binder = item_dict

        elif depth == 2:
            # arg and return list level
            item_dict = {}
            item_dict['name'] = key_name
            item_dict['type'] = item[key_name]
            items_binder.append(item_dict)

    return items_binder


def make_events():
    """ Convert extracted events into functions """
    global events
    temp_event = {}
    for event in events:
        if not event['op']:
            raise Warning(
                'Opcode is unspecified for event : {}'.format(event['name']))
        # create event dictionaries
        temp_event[event['op']] = {'name': event['name'], 'ret': event['ret']}

    events = temp_event


def camelCase(st, splitter='_'):
    x = st.split(splitter)
    output = ''
    for i in range(len(x)):
        if(i == 0):
            output += x[i]
            continue
        output += x[i].title()
    return output


def pascalCase(st, splitter='_'):
    x = st.split(splitter)
    output = ''
    for i in range(len(x)):
        output += x[i].title()
    return output


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


# command line argument to config the plotter
parser = argparse.ArgumentParser(description="Formulatrix Yaml2cs")
parser.add_argument('-p', '--yamlPath',
                    help="yaml file path", type=str, nargs='?')
parser.add_argument('-s', '--savePath',
                    help="save file path", type=str, nargs='?')

args = parser.parse_args()
if(args.yamlPath):
    filename = args.yamlPath
else:
    print('Get your yaml file : ')
    filename = getPath(True, 'Your Yaml File')
    print(filename)

# extrach the opname
_gen_opfuncs_fpath = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'generic_opfuncs.yaml')
handle_file(_gen_opfuncs_fpath)
handle_file(filename)
make_events()
commands = sorted(commands, key=itemgetter('op'))
events = OrderedDict(sorted(events.items()))

# event handler
# parse the yamls
function_list = []
arg_list = []
ret_list = []
op_list = []
count = 0
for key in events:
    function_list.append(events[key]['name'])
    ret_list.append(events[key]['ret'])
    op_list.append(key)
    count += 1

cs_file = 'using System;\n'
cs_file += 'using Formulatrix.Core.Protocol;\n'
cs_file += 'using Formulatrix.Core.Logger;\n\n'

cs_file += 'namespace insert_your_namespace_here\n{\n'
# first make the delegate and the event handler :
for i in range(count):
    cs_file += stringTabLevel(
        1)+'public delegate void {0}Handler('.format(pascalCase(function_list[i]))
    if(len(ret_list[i]) > 0):
        for ret in ret_list[i]:
            if(not 'Array' in ret['type']):
                cs_file += '{0} {1}'.format(ret['type'], ret['name'])
            else:
                pass
            cs_file += ','
        cs_file = cs_file[0:-1]  # delete the last comma
    cs_file += ');\n'

# class name
class_name = ntpath.split(filename)[1][:-5]
cs_file += '\n\tpublic class '
cs_file += pascalCase(class_name)
cs_file += '\n\t{\n'

# add event handler
for i in range(count):
    cs_file += '\t\tpublic event {0}Handler {1};\n'.format(
        pascalCase(function_list[i]), pascalCase(function_list[i]))

# add event fmlxpacket parser
cs_file += '\n\t\tprivate void _eventHandler(FmlxPacket packet)\n\t\t{\n'
cs_file += '\t\t\tpacket.Reset();\n'
cs_file += '\t\t\tswitch (packet.EventCode)\n\t\t\t{\n'

for i in range(count):
    cs_file += '\t\t\t\tcase {0}:\n'.format(op_list[i])
    cs_file += '\t\t\t\t{\n'
    if(len(ret_list[i]) > 0):
        for ret in ret_list[i]:
            if(not 'Array' in ret['type']):
                if(ret['type'] != 'Boolean'):
                    cs_file += '\t\t\t\t\t{0} {1} = packet.Fetch{2}();\n'.format(
                        ret['type'], camelCase(ret['name']), ret['type'])
                else:
                    cs_file += '\t\t\t\t\t{0} {1} = packet.Fetch{2}();\n'.format(
                        ret['type'], camelCase(ret['name']), 'Bool')
            else:
                pass
        cs_file += '\t\t\t\t\tif (_logger != null)\n'
        cs_file += '\t\t\t\t\t{\n'
        cs_file += '\t\t\t\t\t\t_logger.LogInfo(\"Event {0}, '.format(pascalCase(function_list[i]))
        # if the event contains some return value :
        for index,ret in enumerate(ret_list[i]):
            cs_file +=  '{0} : {{{1}}} '.format(camelCase(ret['name']),index)
        if(index != (len(ret_list[i]) - 1)):
            cs_file += ','
        cs_file+='\",'
        for index,ret in enumerate(ret_list[i]):
            cs_file +=  '{0}'.format(camelCase(ret['name']))
            if(index != (len(ret_list[i]) - 1)):
                cs_file += ','
        else:
            cs_file +=');'
        cs_file += '\n\t\t\t\t\t}\n'
        
        cs_file += '\t\t\t\t\tif ({0} != null)\n'.format(
            pascalCase(function_list[i]))
        cs_file += '\t\t\t\t\t{\n'
        cs_file += '\t\t\t\t\t\t{0}('.format(pascalCase(function_list[i]))
        for ret in ret_list[i]:
            cs_file += camelCase(ret['name'])
            cs_file += ','
        cs_file = cs_file[0:-1]
        cs_file += ');'
        cs_file += '\n\t\t\t\t\t}\n'
    else:
        cs_file += '\t\t\t\t\tif (_logger != null)\n'
        cs_file += '\t\t\t\t\t{\n'
        cs_file += '\t\t\t\t\t\t_logger.LogInfo(\"Event {0}\"); '.format(pascalCase(function_list[i]))
        cs_file += '\n\t\t\t\t\t}\n'

        cs_file += '\t\t\t\t\tif ({0} != null)\n'.format(
            pascalCase(function_list[i]))
        cs_file += '\t\t\t\t\t{\n'
        cs_file += '\t\t\t\t\t\t{0}();'.format(pascalCase(function_list[i]))
        cs_file += '\n\t\t\t\t\t}\n'

    cs_file += '\t\t\t\t}\n'
    cs_file += '\t\t\t\tbreak;\n\n'
cs_file += '\t\t\t}\n\n'
cs_file += '\t\t\t}\n\n'

# private variables
cs_file += '\tprivate UInt16 _busId;\n'
cs_file += '\tprivate IFmlxController _controller;\n'
cs_file += '\tprivate IFmlxLogger _logger;\n'

# bus id setter getter
cs_file += '\tpublic ushort BusID\n\t{\n'
cs_file += '\t\tget{return _busId;}\n'
cs_file += '\t\tset{_busId = value;}\n'
cs_file += '\t}\n\n'

# fmlxController Connector
cs_file += '\tpublic void Connect(IFmlxController controller, IFmlxLogger logger = null)\n\t{\n'
cs_file += '\t\t_controller = controller;\n'
cs_file += '\t\t_logger = logger;\n'
cs_file += '\t\t_controller.FmlxMessageReceived -= _eventHandler;\n'
cs_file += '\t\t_controller.FmlxMessageReceived += _eventHandler;\n'
cs_file += '\t}\n\n'

# constructor
cs_file += '\tpublic '
cs_file += pascalCase(class_name)
cs_file += '()\n\t{\n\t}\n\n'

# commands
function_list = []
arg_list = []
ret_list = []
op_list = []
count = 0
for command in commands:
    function_list.append(command['name'])
    if(len(function_list) > 1):
        if(function_list[-2] == command['name']):
            # print(command['name'])
            function_list.pop()
            continue
    arg_list.append(command['arg'])
    ret_list.append(command['ret'])
    op_list.append(command['op'])
    count += 1

for i in range(count):
    # public
    cs_file += '\tpublic '

    # return argument type
    if(len(ret_list[i]) == 0 or len(ret_list[i]) > 1):
        cs_file += 'void '
    elif(len(ret_list[i]) == 1):
        if('Array' in ret_list[i][0]['type']):
            if('UInt16' in ret_list[i][0]['type']):
                cs_file += 'UInt16[] '
            elif('Int16' in ret_list[i][0]['type']):
                cs_file += 'Int16[] '
            elif('UInt32' in ret_list[i][0]['type']):
                cs_file += 'UInt32[] '
            elif('Int32' in ret_list[i][0]['type']):
                cs_file += 'Int32[] '
            elif('Double' in ret_list[i][0]['type']):
                cs_file += 'Double[] '
            elif('Boolean' in ret_list[i][0]['type']):
                cs_file += 'Boolean[] '
        else:
            cs_file += ret_list[i][0]['type']
            cs_file += ' '
            pass

    # function name
    cs_file += pascalCase(function_list[i])

    # argument list
    cs_file += '('
    arg_leght = len(arg_list[i])
    if(arg_leght > 0):
        for j in range(arg_leght):
            arg_type = arg_list[i][j]['type']
            if('Array' in arg_type):
                if('UInt16' in arg_type):
                    cs_file += 'UInt16[]'
                elif('Int16' in arg_type):
                    cs_file += 'Int16[]'
                elif('UInt32' in arg_type):
                    cs_file += 'UInt32[]'
                elif('Int32' in arg_type):
                    cs_file += 'Int32[]'
                elif('Double' in arg_type):
                    cs_file += 'Double[]'
                elif('Boolean' in arg_type):
                    cs_file += 'Boolean[]'
            else:
                cs_file += arg_list[i][j]['type']
            cs_file += ' '
            cs_file += camelCase(arg_list[i][j]['name'])
            if(j < (arg_leght-1)):
                cs_file += ','

    # pass by reference using out for multiple return value
    if(len(ret_list[i]) > 1):
        if(arg_leght > 0):
            cs_file += ', '
        arg_leght = len(ret_list[i])
        for j in range(len(ret_list[i])):
            cs_file += 'out '
            ret_type = ret_list[i][j]['type']
            if('Array' in ret_type):
                if('UInt16' in ret_type):
                    cs_file += 'UInt16[]'
                elif('Int16' in ret_type):
                    cs_file += 'Int16[]'
                elif('UInt32' in ret_type):
                    cs_file += 'UInt32[]'
                elif('Int32' in ret_type):
                    cs_file += 'Int32[]'
                elif('Double' in ret_type):
                    cs_file += 'Double[]'
                elif('Boolean' in ret_type):
                    cs_file += 'Boolean[]'
            else:
                cs_file += ret_list[i][j]['type']
            cs_file += ' '
            # check whether same name for argument and return
            for k in range(len(arg_list[i])):
                if(ret_list[i][j]['name'] in arg_list[i][k]['name']):
                    cs_file += camelCase(ret_list[i][j]['name'])
                    cs_file += 'Out'
                    break
            else:
                cs_file += camelCase(ret_list[i][j]['name'])
            if(j < (arg_leght-1)):
                cs_file += ','

    cs_file += ')\n\t{\n'

    # the command and fetch code
    if(len(ret_list[i]) == 0):
        cs_file += '\t\t_controller.SendCommand('
        cs_file += str(op_list[i])
        cs_file += ',_busId'
        arg_leght = len(arg_list[i])
        # fill the input arguments
        if(arg_leght > 0):
            cs_file += ','
            for j in range(arg_leght):
                cs_file += camelCase(arg_list[i][j]['name'])
                if(j < (arg_leght-1)):
                    cs_file += ','
        cs_file += ');\n'
        cs_file += '\t\tif (_logger != null)\n'
        cs_file += '\t\t{\n'
        cs_file += '\t\t\t_logger.LogInfo(\"Command : {0}'.format(pascalCase(function_list[i]))
        if(arg_leght > 0):   
            cs_file+=', args : '  
            for j in range(arg_leght):
                cs_file += '{0} : {{{1}}}'.format(camelCase(arg_list[i][j]['name']),j)
                if(j < (arg_leght-1)):
                    cs_file += ', '
            cs_file+='\",'
            for j in range(arg_leght):
                cs_file += '{0} '.format(camelCase(arg_list[i][j]['name']))
                if(j < (arg_leght-1)):
                    cs_file += ', '
            cs_file += ');'
        else:
            cs_file += '\");'
        cs_file += '\n\t\t}\n'
        # cs_file += '\t\treturn value;\n'

    # only one return value
    elif(len(ret_list[i]) == 1):
        cs_file+='\t\t'
        if('Array' in ret_list[i][0]['type']):
            if('UInt16' in ret_list[i][0]['type']):
                cs_file += 'UInt16[] '
            elif('Int16' in ret_list[i][0]['type']):
                cs_file += 'Int16[] '
            elif('UInt32' in ret_list[i][0]['type']):
                cs_file += 'UInt32[] '
            elif('Int32' in ret_list[i][0]['type']):
                cs_file += 'Int32[] '
            elif('Double' in ret_list[i][0]['type']):
                cs_file += 'Double[] '
            elif('Boolean' in ret_list[i][0]['type']):
                cs_file += 'Boolean[] '
        else:
            cs_file += ret_list[i][0]['type']
        cs_file+= ' _retValue;\n'
        cs_file += '\t\t_retValue = _controller.Get'

        # return value types
        ret_types = ret_list[i][0]['type']
        if('Array' in ret_types):
            if('Double' in ret_types):
                cs_file += 'DoubleArray'
            elif('Boolean' in ret_types):
                cs_file += 'BoolArray'
            elif('UInt16' in ret_types):
                cs_file += 'UInt16Array'
            elif('Int16' in ret_types):
                cs_file += 'Int16Array'
            elif('UInt32' in ret_types):
                cs_file += 'UInt32Array'
            elif('Int32' in ret_types):
                cs_file += 'Int32Array'

        else:
            cs_file += ret_list[i][0]['type']
        cs_file += '('
        cs_file += str(op_list[i])
        cs_file += ',_busId'
        arg_leght = len(arg_list[i])
        # fill the input arguments
        if(arg_leght > 0):
            cs_file += ','
            for j in range(arg_leght):
                cs_file += camelCase(arg_list[i][j]['name'])
                if(j < (arg_leght-1)):
                    cs_file += ','
        cs_file += ');\n'
        cs_file += '\t\tif (_logger != null)\n'
        cs_file += '\t\t{\n'
        cs_file += '\t\t\t_logger.LogInfo(\"Command {0}, '.format(pascalCase(function_list[i]))
        string_index = 0
        if(arg_leght > 0):
            cs_file+= 'args : '    
            for j in range(arg_leght):
                cs_file += '{0} : {{{1}}}'.format(camelCase(arg_list[i][j]['name']),string_index)
                cs_file += ', '
                string_index+=1
        cs_file+=' return : {{{0}}}\",'.format(string_index)
        if(arg_leght > 0):
            for j in range(arg_leght):
                cs_file += '{0},'.format(camelCase(arg_list[i][j]['name']))
        cs_file+='_retValue);'
        
        cs_file += '\n\t\t}\n'
        cs_file += '\t\treturn _retValue;\n'
        
    else:
        cs_file += '\t\tFmlxPacket response = _controller.SendCommand('
        cs_file += str(op_list[i])
        cs_file += ',_busId'
        arg_leght = len(arg_list[i])
        if(arg_leght > 0):
            cs_file += ','
            for j in range(arg_leght):
                cs_file += camelCase(arg_list[i][j]['name'])
                if(j < (arg_leght-1)):
                    cs_file += ','
        cs_file += ');\n'
        ret_leght = len(ret_list[i])
        # fill the return value
        for j in range(ret_leght):
            cs_file += '\t\t'
            # check whether same name for argument and return
            for k in range(len(arg_list[i])):
                if(ret_list[i][j]['name'] in arg_list[i][k]['name']):
                    cs_file += camelCase(ret_list[i][j]['name'])
                    cs_file += 'Out'
                    break
            else:
                cs_file += camelCase(ret_list[i][j]['name'])
            cs_file += ' = response.Fetch'
            if(ret_list[i][j]['type'] == 'Boolean'):
                cs_file += 'Bool'
                cs_file += '();\n'
            elif('Array' in ret_list[i][j]['type']):
                if('UInt16' in ret_type):
                    cs_file += 'UInt16Array'
                elif('Int16' in ret_type):
                    cs_file += 'Int16Array'
                elif('UInt32' in ret_type):
                    cs_file += 'UInt32Array'
                elif('Int32' in ret_type):
                    cs_file += 'Int32Array'
                elif('Double' in ret_type):
                    cs_file += 'DoubleArray'
                elif('Boolean' in ret_type):
                    cs_file += 'BoolArray'
                cs_file += '((int)'
                cs_file += camelCase(ret_list[i][j-1]['name'])
                cs_file += ');\n'
            else:
                cs_file += ret_list[i][j]['type']
                cs_file += '();\n'
    
        # TODO logger for more than one return arguments
        # arguments name
        cs_file += '\t\tif (_logger != null)\n'
        cs_file += '\t\t{\n'
        cs_file += '\t\t\t_logger.LogInfo(\"Command {0}, '.format(pascalCase(function_list[i]))
        string_index = 0
        if(arg_leght > 0):
            cs_file+= 'args : '    
            for j in range(arg_leght):
                cs_file += '{0} : {{{1}}}'.format(camelCase(arg_list[i][j]['name']),string_index)
                if(j < (arg_leght-1)):
                    cs_file += ', '
                string_index+=1
        cs_file += 'return : '

        #returns name
        for j in range(len(ret_list[i])):
            # check whether same name for argument and return
            for k in range(len(arg_list[i])):
                if(ret_list[i][j]['name'] in arg_list[i][k]['name']):
                    cs_file += '{0} : {{{1}}}'.format(camelCase(ret_list[i][j]['name']),string_index)
                    cs_file += 'Out'
                    string_index+=1
                    break
            else:
                cs_file += '{0} : {{{1}}}'.format(camelCase(ret_list[i][j]['name']),string_index)
                string_index+=1
            if(j < (len(ret_list[i])-1)):
                cs_file += ','
        cs_file += '\",'
        #arguments value
        if(arg_leght > 0):
            for j in range(arg_leght):
                cs_file += '{0}'.format(camelCase(arg_list[i][j]['name']))
                cs_file += ', '
        #return value
        for j in range(len(ret_list[i])):
            # check whether same name for argument and return
            for k in range(len(arg_list[i])):
                if(ret_list[i][j]['name'] in arg_list[i][k]['name']):
                    cs_file += '{0}'.format(camelCase(ret_list[i][j]['name']))
                    cs_file += 'Out'
                    break
            else:
                cs_file += '{0}'.format(camelCase(ret_list[i][j]['name']))
            if(j < (len(ret_list[i])-1)):
                cs_file += ','
        cs_file+=');'
        cs_file += '\n\t\t}\n'

    cs_file += '\t}\n'
cs_file += '\t\t\n}'
cs_file += '\t\n}'

if(args.savePath):
    with open(args.savePath, 'w') as file:
        file.write(cs_file)
else:
    print('Save your cs file : ')
    path = getPath(False)
    with open(args.savePath, 'w') as file:
        file.write(cs_file)
