import os
import sys
import clr
import copy
import yaml

sys.path.append(os.path.abspath('../Include'))
clr.AddReference('System')
from System import Boolean, Byte, UInt16, Int16, UInt32, Int32, Double, String, Array, Object

_type_convert = {
    Boolean : 'Boolean',
    UInt16  : 'UInt16',
    UInt32  : 'UInt32',
    Int16   : 'Int16',
    Int32   : 'Int32',
    Double  : 'Double',
    String  : 'String',
    Array[UInt16] : 'Array_UInt16',
    Array[UInt32] : 'Array_UInt32',
    Array[Int16]  : 'Array_Int16',
    Array[Int32]  : 'Array_Int32',
    Array[Double] : 'Array_Double'
}

def convert(inpath, appname = '', firm_version =''):
    """ The only function you need to convert pydict
    opfunc list to YAML opfunc list.

    You can specify the inpath (input path) as path to file
    or directory. The function will automatically trying to
    convert all files inside directory into YAML.

    Requirements: 
    - Your input file(s) must already prepared to contain only
      1 set of command py dict and/or 1 set of event py dict.
    - File may contain command only or event only.
    - Command dict must have 'commands' string in its name and
      (e.g : 'nighthawk_commands' 
    - Event dict must have 'events' string in its name
      (e.g. : 'nighthawk_events')
    """
    yaml.representer.SafeRepresenter.add_representer(_InlineList, _inlinelist_representer)
    yaml.representer.SafeRepresenter.add_representer(_DictNobracket, _dictnobracket_representer)

    inpath = _handle_path(inpath)

    for ind in range(0, len(inpath)):
        with open(inpath[ind],'r') as infile:
            opfuncs_str = _prepare_dictfile(infile)
            opdict = eval(opfuncs_str)
            
            outpath = os.path.splitext(inpath[ind])[0] + '.yaml'
            with open(outpath,'w') as outfile:
                outfile.write('APPNAME: {}\nVERSION: {}\n'.format(appname,firm_version))
            
            if 'commands' in opdict:
                oplist = _handle_items(opdict['commands'], 'cmd')
                _handle_yamldump(outpath, oplist, 'cmd')
            
            if 'events' in opdict:
                oplist = _handle_items(opdict['events'], 'evt')
                _handle_yamldump(outpath, oplist, 'evt') 

# ------------------------- PyYaml custom dumper representers ----------------------------
class _InlineList(list):
    pass

class _DictNobracket(dict):
    pass

def _inlinelist_representer(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

def _dictnobracket_representer(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)

# ----------------------------------- Private Functions ----------------------------------
def _handle_yamldump(outpath, oplist, optype):
    if optype == 'cmd':
        optype_str = 'COMMANDS'
    elif optype == 'evt':
        optype_str = 'EVENTS'
    else:
        raise Warning('Wrong opfunc type, choose \'cmd\' or \'evt\'')

    with open(outpath,'a') as outfile:
        outfile.write('\n{}:\n'.format(optype_str))
        yaml_stream = yaml.safe_dump(oplist)
        yaml_stream = yaml_stream.replace('\n- ', '\n\n- ')
        yaml_stream = yaml_stream.replace('op:', 'op :')
        yaml_stream = yaml_stream.replace('{', '')
        yaml_stream = yaml_stream.replace('}', '')
        outfile.write(yaml_stream)

def _handle_path(inpath):
    if inpath[0] == '/':
        inpath = '.' + inpath

    if os.path.isfile(inpath):
        inpath = [inpath]
    else:
        inpath = [(inpath+'/'+f) for f in os.listdir(inpath) if os.path.isfile(os.path.join(inpath, f))]

    return inpath

def _prepare_dictfile(dfile):
    cmd_keystr = ['commands', '=']
    evt_keystr = ['events', '=']
    cmd_exist = False
    
    result_str = '{\n'
    for line in dfile:
        if all(keystr in line for keystr in cmd_keystr):
            if '[' in line:
                line = '\'commands\' :\n[\n'
            else:
                line = '\'commands\' :'
            
            cmd_exist = True

        if all(keystr in line for keystr in evt_keystr):
            if cmd_exist:
                line_prefix = '\n,'
            else:
                line_prefix = '\n'

            if '[' in line:
                line = line_prefix + '\'events\' :\n[\n'
            else:
                line = line_prefix + '\'events\' :'
        
        result_str += line

    result_str += '}'

    return result_str

def _handle_items(opitems, optype):
    oplist = []
    for item in opitems:
        funcname = item['name']
        temp_dict = {funcname : []} 
        temp_dict[funcname].append(_DictNobracket({'op' : item['opcode']}))

        if optype == 'cmd':
            temp_dict[funcname].append(_handle_argret('arg', item['arg_defs']))
            temp_dict[funcname].append(_handle_argret('ret', item['ret_defs']))
        elif optype == 'evt':
            temp_dict[funcname].append(_handle_argret('ret', item['evt_def']))
        else:
            raise Warning('select proper optype, cmd or evt')
        
        oplist.append(copy.deepcopy(temp_dict))
    
    return oplist

def _handle_argret(keyword, aritems):
    if not aritems:
        return _DictNobracket({keyword : None})

    if type(aritems) is tuple:
        aritems = [aritems]
    
    result = []

    for item in aritems:
        arname = item[0]
        artype = _type_convert[item[1]]

        if len(item) > 2:
            artype = artype + '_c'
        
        result.append(_DictNobracket({arname : artype}))

    return {keyword : _InlineList(result)}

# ----------------------------------- Main Function ----------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
"""Convert pydict opfunc list to YAML opfunc list.

Usage: %s inpath [appname] [firm_version]

You can specify the inpath (input path) as path to file
or directory. The function will automatically trying to
convert all files inside directory into YAML.

Requirements: 
- Your input file(s) must already prepared to contain only
  1 set of command py dict and/or 1 set of event py dict.
- File may contain command only or event only.
- Command dict must have 'commands' string in its name and
  (e.g : 'nighthawk_commands' 
- Event dict must have 'events' string in its name
  (e.g. : 'nighthawk_events')
""" % os.path.basename(__file__))
        exit(1)
    convert(*sys.argv[1:])
