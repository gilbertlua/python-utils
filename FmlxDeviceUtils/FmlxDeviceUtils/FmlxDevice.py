import os
import sys
import time
import logging
import yaml
import copy
from functools import partial
import collections
from collections import OrderedDict
import itertools
import ctypes
from array import array
from operator import itemgetter
import FmlxLogger

try:
    # pythonnet compability check
    import clr
    path =r'../FmlxDeviceUtils/Include'
    sys.path.append(path)
    clr.AddReference('System')
    clr.AddReference('Formulatrix.Core')
    clr.AddReference('Formulatrix.Core.Protocol')    
    from System import Boolean, Byte, UInt16, Int16, UInt32, Int32, Single, Double, String, Array, Object, IndexOutOfRangeException
    from Formulatrix.Core.Protocol import FmlxController, FmlxPacket, FmlxIllegalOpcodeException, FmlxTimeoutException
    import NetLogger
    isPythonnetImported = True
except ImportError:
    # use python core if the pythonnet is not installed
    print('WARNING no pythonnet installed, use Python Core instead')
    isPythonnetImported = False
except ModuleNotFoundError:
    # use python core if the pythonnet is not installed
    print('WARNING no pythonnet installed, use Python Core instead')
    isPythonnetImported = False

# Formulatrix Core python modules
if(sys.version_info[0] >= 3):
    import FormulatrixCorePy.FmlxPacket
    import FormulatrixCorePy.FmlxController

if(not (sys.version_info < (3,0))):
    from colorama import init, Fore, Back, Style
    init()  # colorama

#completer
import rlcompleter
import readline
readline.parse_and_bind("tab: complete")

# to easily parse the path, to get the filename
import ntpath
ntpath.basename("a/b/c")

class FmlxEnum(object):
    """Custom Enumeration class used for FmlxDeviceUtils"""
    def __init__(self,desc):
        self.enumlist = []
        self.desc = desc

    def __repr__(self):
        self.description()
        return ''

    def description(self):
        if not self.enumlist:
            print ('WARNING: This Enum does not have any items/values')
            return

        if self.desc:
            print ('Fmlx Enum : ' + self.desc)

        print ('Possible values are:')
        for item in self.enumlist:
            desc_text = ''
            if item['desc']:
                desc_text = ', ' + item['desc']
            print ('- {} : {} {}'.format(item['name'], item['val'], desc_text))

    def add_item(self, itemname, itemval, itemdesc):
        enumitem = {'name' : itemname, 'val' : itemval, 'desc' : itemdesc}
        self.__dict__[itemname] = itemval
        self.enumlist.append(enumitem)

class EventHook(object):
    """Class to provide hooking interface of event handlers to device events"""
    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler):
        self._handlers.append(handler)
        return self
        
    def __isub__(self, handler):
        try:
            self._handlers.remove(handler)
        except:
            pass
        return self

    def fire(self, *args, **kwargs):
        for handler in self._handlers:
            try:
                handler(*args, **kwargs)
            except:
                pass

class FmlxDevice(object):
    """Main class to handle the opcode functions related communication with fmlx devices"""
    #generic opfunctions list filepath
    _gen_opfuncs_fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), './generic_opfuncs.yaml')
    #the fmlx core packet fetching functions

    def __init__(self, comm_driver, address, opfuncs_filepath = '',log_handler = None, use_single_precision = False ,usePythonnet = True,retryCount = 3):
        """ Initialize the class
        Parameters:
        comm_driver      -- communication driver
        address          -- target fmlx device address
        opfuncs_filepath -- path to YAML file that contain list of opcode functions
        log_handler      -- logging output handler. Check logging package for available handlers
        """

        if(isPythonnetImported):
            self._usePythonnet = usePythonnet
        else:
            self._usePythonnet = False

        if(not self._usePythonnet and sys.version_info[0] < 3):
            if(not isPythonnetImported):
                raise NotImplementedError('CorePython is Not yet Implemented on python2!, Please use python3 or install Pythonnet first')
            else:
                self._usePythonnet = True

        #setting logging parameters
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.CRITICAL))
        if(log_handler):
            self._logger.addHandler(log_handler)
        self._logger.debug('Python version : {0}, comm driver : {1}, address : {2}, opfuncs file path : {3}, Using Single Precision : {4}, Using Pythonnet : {5}'.format(sys.version,comm_driver,address,opfuncs_filepath,use_single_precision,self._usePythonnet))
        sys.excepthook = self.uncaughtExceptionHandler
        #.NET datatype for FMLX Core function calls
        if(self._usePythonnet):
            #equivalent .NET data type in python
            self._py_datatype = {
                Boolean : bool,
                UInt16  : int,
                UInt32  : int,
                Int16   : int,
                Int32   : int,
                Single  : float,
                Double  : float,
                String  : str,
                Array[UInt16] : partial(array, 'H'),
                Array[Int16]  : partial(array, 'h'),
                Array[UInt32] : partial(array, 'L'),
                Array[Int32]  : partial(array, 'l'),
                Array[Double] : partial(array, 'd')
            }
            self._dotnet_datatype = {
                'Boolean' : Boolean,
                'UInt16'  : UInt16,
                'UInt32'  : UInt32,
                'Int16'   : Int16,
                'Int32'   : Int32,
                'Float'   : Single,
                'Double'  : Double,
                'String'  : String,
                'Array_UInt16' : Array[UInt16],
                'Array_UInt32' : Array[UInt32],
                'Array_Int16'  : Array[Int16],
                'Array_Int32'  : Array[Int32],
                'Array_Float'  : Array[Single],
                'Array_Double' : Array[Double],
                'Array_UInt16_c' : Array[UInt16],
                'Array_UInt32_c' : Array[UInt32],
                'Array_Int16_c'  : Array[Int16],
                'Array_Int32_c'  : Array[Int32],
                'Array_Double_c' : Array[Double]
            }
            self._fetch_funcs = {
                'Boolean' : FmlxPacket.FetchBool,
                'UInt16'  : FmlxPacket.FetchUInt16,
                'Int16'   : FmlxPacket.FetchInt16,
                'UInt32'  : FmlxPacket.FetchUInt32,
                'Int32'   : FmlxPacket.FetchInt32,
                'Float'  : FmlxPacket.FetchFloat,
                'Double'  : FmlxPacket.FetchDouble,
                'String'  : FmlxPacket.FetchString,
                'Array_UInt16_c' : FmlxPacket.FetchUInt16Array,
                'Array_Int16_c'  : FmlxPacket.FetchInt16Array,
                'Array_UInt32_c' : FmlxPacket.FetchUInt32Array,
                'Array_Int32_c'  : FmlxPacket.FetchInt32Array,
                'Array_Float_c' : FmlxPacket.FetchFloatArray,
                'Array_Double_c' : FmlxPacket.FetchDoubleArray,
                'Array_UInt16' : FmlxPacket.FetchUInt16,
                'Array_Int16'  : FmlxPacket.FetchInt16,
                'Array_UInt32' : FmlxPacket.FetchUInt32,
                'Array_Int32'  : FmlxPacket.FetchInt32,
                'Array_Float'  : FmlxPacket.FetchFloat,
                'Array_Double' : FmlxPacket.FetchDouble
            }

        #c datatype for FMLX Core function calls
        else:
            self._c_datatype = {
                'Boolean' : ctypes.c_uint16,
                'UInt16'  : ctypes.c_uint16,
                'UInt32'  : ctypes.c_uint32,
                'Int16'   : ctypes.c_int16,
                'Int32'   : ctypes.c_int32,
                'Float'   : ctypes.c_float,
                'Double'  : ctypes.c_double,
                'String'  : str,
                'Array_UInt16' : lambda x : list(map(ctypes.c_uint16,x)),
                'Array_UInt32' : lambda x : list(map(ctypes.c_uint32,x)),
                'Array_Int16'  : lambda x : list(map(ctypes.c_int16,x)),
                'Array_Int32'  : lambda x : list(map(ctypes.c_int32,x)),
                'Array_Float'  : lambda x : list(map(ctypes.c_float,x)),
                'Array_Double' : lambda x : list(map(ctypes.c_double,x)),
                'Array_UInt16_c' : lambda x : list(map(ctypes.c_uint16,x)),
                'Array_UInt32_c' : lambda x : list(map(ctypes.c_uint32,x)),
                'Array_Int16_c'  : lambda x : list(map(ctypes.c_int16,x)),
                'Array_Int32_c'  : lambda x : list(map(ctypes.c_int32,x)),
                'Array_Float_c'  : lambda x : list(map(ctypes.c_float,x)),
                'Array_Double_c' : lambda x : list(map(ctypes.c_double,x))
            }
            # pythonic return data type
            self._ret_dataType = {
                'Boolean' : bool,
                'UInt16'  : int,
                'UInt32'  : int,
                'Int16'   : int,
                'Int32'   : int,
                'Float'   : float,
                'Double'  : float,
                'String'  : str,
                'Array_UInt16' : list,
                'Array_UInt32' : list,
                'Array_Int16'  : list,
                'Array_Int32'  : list,
                'Array_Float'  : list,
                'Array_Double' : list,
                'Array_UInt16_c' : list,
                'Array_UInt32_c' : list,
                'Array_Int16_c'  : list,
                'Array_Int32_c'  : list,
                'Array_Float_c'  : list,
                'Array_Double_c' : list
            }
            self._fetch_funcs = {
                'Boolean' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchBool,
                'UInt16'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16,
                'Int16'   : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16,
                'UInt32'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32,
                'Int32'   : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32,
                'Float'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloat,
                'Double'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDouble,
                'String'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchString,
                'Array_UInt16_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16Array,
                'Array_Int16_c'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16Array,
                'Array_UInt32_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32Array,
                'Array_Int32_c'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32Array,
                'Array_Float_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloatArray,
                'Array_Double_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDoubleArray,
                'Array_UInt16' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16,
                'Array_Int16'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16,
                'Array_UInt32' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32,
                'Array_Int32'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32,
                'Array_Float'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloat,
                'Array_Double' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDouble
            }

        if(self._usePythonnet):
            if(log_handler):
                self._ctrl = FmlxController(comm_driver,use_single_precision,retryCount,NetLogger.Pythonlogger('Controller',log_handler=log_handler))
            else:
                self._ctrl = FmlxController(comm_driver,use_single_precision,retryCount)                
        else:
            self._ctrl = FormulatrixCorePy.FmlxController.FmlxController(comm_driver,use_single_precision,retryCount,log_handler=log_handler)
        self._address = address  

        #extract enums, command, event functions
        self._commands = []
        self._events = []
        self._enums = [] #minimal enum storage for printing enum list
        self._handle_file(self._gen_opfuncs_fpath)
        self._handle_file(opfuncs_filepath)
        self._opfunc_filepath = opfuncs_filepath

        #make callable command, event handlers
        self._make_commands()
        self._make_events()

        #sort based on opcode
        self._commands = sorted(self._commands, key = itemgetter('op'))
        self._events = OrderedDict(sorted(self._events.items()))

        #activate event listener that handles all events
        if(self._usePythonnet):
            self._ctrl.FmlxMessageReceived += self.handle_event
        else:
            self._ctrl += self.handle_event
        #global event hook, fired for all received events
        self.OnEvent = EventHook()


    def connect(self):
        """Connecting the communication"""
        self._ctrl.Connect()


    def disconnect(self):
        """Disconnecting the communication"""
        self._ctrl.Disconnect()


    def is_connected(self):
        """Check if communication is already connected"""
        return self._ctrl.Connected


    def set_log_handler(self, log_handler):
        """Setting the log output handler.
        Parameters:
        log_handler --- The log handler, check logging package for available handlers"""
        self._logger.addHandler(log_handler)


    def list_commands(self):
        """List all of the supported fmlx command functions"""
        print ('{:6} {:65} {}'.format('Opcode', 'Command Name', 'Function Returns (In Order)'))
        print ('{:6} {:65} {}'.format('------', '------------', '--------------------------'))
        
        for opfunc in self._commands:
            s_funcname = opfunc['name'] + '(' + self._opfunc_args_to_string(opfunc) + ')'

            #create return variables list
            s_return = self._opfunc_returns_to_string(opfunc)
            
            print ('{:6} {:65} {}'.format(opfunc['op'], s_funcname, s_return))


    def list_enums(self):
        """List all of the supported enumerations"""
        print ('Supported Enumerations')
        print ('----------------------')
        for enumitem in self._enums:
            print ('- {} : {}'.format(enumitem['name'], enumitem['desc']))

    def list_events(self):
        """List all of the supported fmlx events functions"""
        print ('{:6} {:25} {:40}'.format('Opcode', 'Event Name', 'Event Returns (In Order)'))
        print ('{:6} {:25} {:40}'.format('------', '----------', '------------------------'))
        
        for key, value in self._events.iteritems():
            s_funcname = value['name']

            #create event return variables list
            s_return = self._opfunc_returns_to_string(value)
            
            print ('{:6} {:25} {:40}'.format(key, s_funcname, s_return))

    def send_command(self,cmdName, opcode, params, rets, *args):
        """Sending command to devices. This acts as a template for opcode commands
        Parameters:
        opcode  -- opcode, obviously
        params  -- list of opfunction parameter
        rets    -- list of opfunction return list
        args    -- arguments to be put into opfunction parameters
        """
        # print (opcode,'<->',params,'<->',rets,'<->',args)
        #checking for incorrect input arguments
        if len(args) != len(params):
            lenparam = len(params)
            if lenparam == 0:
                warntext = 'Function does not take any argument'
            else:
                warntext = 'Function requires {} argument(s), which is/are : ('.format(lenparam)
                param_list = [("%(type)s %(name)s" % param) for param in params]
                warntext += ", ".join(param_list) + ')'
            raise TypeError(warntext)
        
        # for logging purpose only
        paramNames = [param['name'] for param in params]
        self._logger.debug('send_command, cmdName : {0}, op : {1}, params : {2}'.format(cmdName,opcode,list(zip(paramNames,args))))

        if(self._usePythonnet):
            arg_list = [self._dotnet_datatype[param['type']](arg) for param, arg in zip(params, args)]
        else:
            arg_list = [self._c_datatype[param['type']](arg) for param, arg in zip(params, args)]

        #sending the command packet
        try:
            if(self._usePythonnet):
                resp = self._ctrl.SendCommand.Overloads[UInt16, UInt16, Array[Object]](UInt16(opcode), UInt16(self._address), Array[Object](arg_list))
            else:
                resp = self._ctrl.SendCommand(opcode, self._address, *arg_list)

            if(self._usePythonnet):
                pass # TODO implement!
                # self._logger.debug('{:012.6f}:{}:CMD:{:03}'.format(time.perf_counter(), self._address, int(opcode)))
            else:
                pass # TODO implement!
        except ValueError as ex:
            raise

        #extract the return items from response
        results = self._extract_opfunc_rets(list(args), rets, resp)
        
        
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0][1]
        else:
            # for logging purpose only
            # retNames = [ret['name'] for ret in rets]
            # self._logger.debug('received response, rets : {0}'.format(list(zip(retNames,results))))
            return OrderedDict(results)

    @staticmethod
    def getPath(isLoad = True,window_title = None):
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

    def get_eeprom_config(self):
        # if(sys.version_info[0] < 3):
        #     raise Exception('\033[31mcurrently unsuported for python 3.6 and below\033[39m')
        app_name = self.get_app_name()
        version = self.get_version()
        config_string = 'FIRMWARE:\n'
        config_string += '- APP_NAME : {0}\n'.format(app_name)
        config_string += '- VERSION : {0}\n'.format(version)
        config_string += '\n'
        config_string += 'EEPROM_CONFIGS :\n'
        any_eeprom = False
        print('app name : {0} , version : {1}'.format(app_name,version))
        for opfunc in self._commands:
            if not 'eeprom' in opfunc:
                continue
            any_eeprom = True

            # config_string += '- desc : '
            # if 'desc' in opfunc:
            #     config_string += '| \n{0}\n'.format(opfunc['desc'])
            # else:
            #     config_string += 'none\n'
            
            if(opfunc['eeprom'] == 0 ):
                opfunc['eeprom'] = []
            
            isSuccess = False
            
            # list all possible id getter value
            getter_list = []
            try:
                for i in opfunc['eeprom']:
                    getter_list+=[list(range(i['type']))]
            except TypeError:
                raise TypeError('Wrong EEPROM field property on name : {0} op num :{1}'.format(opfunc['name'],opfunc['op']))

            for enum,combination in enumerate(itertools.product(*getter_list)):
                try:
                    data = getattr(self,opfunc['name'])(*combination)
                except FormulatrixCorePy.FmlxController.IllegalOpcodeError:
                    print('\033[31mWARNING No {0} Opcode({1}) in {2} version : {3}\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                except IndexError:
                    print('\033[31mWARNING {0} Opcode({1}) in {2} version : {3} Has not enough data to parse\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                except FmlxIllegalOpcodeException:
                    print('\033[31mWARNING No {0} Opcode({1}) in {2} version : {3}\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                except IndexOutOfRangeException:
                    print('\033[31mWARNING {0} Opcode in({1}) {2} version : {3} Has not enough data to parse\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                except FmlxTimeoutException:
                    print('\033[31mError Timeout {0} Opcode in({1}) {2} version : {3} , skipping get eeprom process..\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                except TimeoutError:
                    print('\033[31mError Timeout {0} Opcode in({1}) {2} version : {3} , skipping get eeprom process..\033[39m'.format(opfunc['name'],opfunc['op'],app_name,version))
                    time.sleep(0.1)
                    break
                
                # if we succesfully get the config, write it to file
                if(not isSuccess):
                    isSuccess = True
                    # function name
                    print_info_header = '{0}'.format(opfunc['name'])
                    config_string += '- {0}:\n'.format(opfunc['name'])

                    # op 
                    print_info_header += ',op:{0}'.format(opfunc['op'])
                    config_string += '  - op: {0}\n'.format(opfunc['op'])

                # delete excluded return value
                del_count = 0
                if('exclude_eeprom' in opfunc):
                    for exclude in opfunc['exclude_eeprom']:
                        del_count+=1
                        try:
                            del data[exclude['name']]
                        except KeyError:
                            error_string = '\nKeyError : No excluded return data named {0}'.format(exclude['name'])
                            error_string += '\nop name : {0}, data :{1}'.format(opfunc['name'],data)
                            raise Exception(error_string)
                
                config_string+='  - data'
                for combo in combination:
                    config_string+= '_{0}'.format(combo)
                config_string+= ':\n'
                print_info = ''
                # getter argument list
                config_string+='    - arg : ['
                for enum,name in enumerate(opfunc['arg']):
                    config_string+=' {0} : {1} '.format(name['name'],combination[enum])
                    print_info+=' {0} : {1} '.format(name['name'],combination[enum])
                    if((enum+1)<len(opfunc['arg'])):
                        config_string +=','    
                config_string+=']\n'

                # return data list
                config_string+='    - ret : ['
                if(type(data) is not collections.OrderedDict):
                    config_string += ' {0} : {1} '.format(opfunc['ret'][0]['name'],data)
                    print_info+=' {0} : {1} '.format(opfunc['ret'][0]['name'],data)
                else:
                    len_ret = len(opfunc['ret']) - del_count
                    for enum,d in enumerate(data.items()):
                        config_string += ' {0} : {1} '.format(d[0],d[1])
                        print_info+=' {0} : {1} '.format(d[0],d[1])
                        if( (enum + 1) != len_ret):
                            config_string += ','
                print(print_info_header,print_info)
                # print(opfunc_name,getter_list)
                config_string+=']\n'

            config_string+='\n'
            # print(print_info)
                
        if(any_eeprom == False):
            raise Exception('No EEPROM config in this yaml file')

        try:
            path = self.getPath(False)
        except ImportError: # no tkinter detected, or possibly using console terminal
            path = input('your filename :')

        print('SAVING....')
        with open(path,'w') as file:
            print('\033[32mSave to : {0}\033[39m\n'.format(path))
            file.write(config_string)

    def set_eeprom_config(self,path = None):
        if(path == None):
            try:
                path = self.getPath(True)
            except ImportError: # no tkinter detected, or possibly using console terminal
                raise Exception('Input Your Path / FileName! ( no tkinter detected )')

        with open(path, 'r') as opfuncs_file:
            configs_list = yaml.load(opfuncs_file.read(),Loader=yaml.Loader)
        # check the app name and version
        config_app_name = configs_list['FIRMWARE'][0]['APP_NAME']
        config_version = configs_list['FIRMWARE'][1]['VERSION']
        target_app_name = self.get_app_name()
        target_version = self.get_version()
        if(config_app_name!=target_app_name):
            raise Exception('invalid app name, config : {0} , target {1}'.format(config_app_name,target_app_name))
        if(config_version!=target_version):
            print('Warning, your config firmware version : {0}, target firmware version {1}'.format(config_version,target_version))
            if(input('it may not be compatible, do you want to proceed?(type \'y\' to proceed) : ') != 'y'):
                print('config set aborted')
                return
        configs_list = configs_list['EEPROM_CONFIGS']
        config_setter_name = []
        config_args = []
        for opfuncs_list in self._commands:
            if not 'getter_op' in opfuncs_list:
                continue
            getter_op = opfuncs_list['getter_op']
            # seek the getter opcode name on the target yaml file
            for command in self._commands:
                if(command['op'] == getter_op):
                    target_getter_name = command['name']
                    break
            else:
                # if no matching found, continue the loop
                continue

            # seek the matching getter op with the stored op
            for op in configs_list:
                config_name = list(op.keys())[0]
                config_op = list(list(op.values())[0][0].values())[0]
                if(getter_op == config_op):
                    if(config_name != target_getter_name):
                        raise Exception('Wrong getter command name, op : {0}, target command name : {1} , config command name : {2}'.format(config_op,target_getter_name,config_name))
                    else:
                        # if all the security check pass, stored it in config args to be send at the end of the loop    
                        config_setter_name += [opfuncs_list['name']]
                        send_data = []
                        for w in list(op.values())[0][1:]:
                            single_data = []
                            for x in w.values():
                                for y in x:
                                    for z in y.values():
                                        if(z!=[]):
                                            # print(z)
                                            value_send = []
                                            for value in z:
                                                value_send.append(list(value.values())[0])
                                            # print(value_send)
                                            single_data += value_send
                            # print(single_data)
                            send_data +=[single_data]  
                        config_args.append(send_data)
                            
        # finally write all the configs into the firmware
        for n in range(len(config_setter_name)):
            # print(config_setter_name[n],config_args[n])
            for config in config_args[n]:
                print(config_setter_name[n],config)
                getattr(self,config_setter_name[n])(*config)
                pass
                
        print('\n\033[32mSET CONFIG SUCCESS!\033[39m\n')

    def handle_event(self, fmlx_packet):
        """ Handle event packets sent by fmlx device """
        if(sys.version_info[0] < 3):
            if(self._usePythonnet):
                pass
                # self._logger.debug('{:012.6f}:{}:EVT:{:03}'.format(time.clock(), self._address, int(fmlx_packet.Opcode)))
            else:
                pass 
        else:
            if(self._usePythonnet):
                pass # TODO implement
                # self._logger.debug('{:012.6f}:{}:EVT:{:03}'.format(time.perf_counter(), self._address, int(fmlx_packet.Opcode)))
            else:
                pass # TODO implement
        if fmlx_packet.Address != self._address:
            return

        if not fmlx_packet.IsEvent:
            return
        
        #fire hooked general event handlers
        #reset current pointed packet data to first index
        self.OnEvent.fire(fmlx_packet)
        if(self._usePythonnet):
            fmlx_packet.Reset()

        opcode = int(fmlx_packet.Opcode)
        if not opcode in self._events.keys():
            print ('WARNING : Opcode {} is received but does not have Event definition'.format(opcode))
            return

        event_name = self._events[opcode]['name']
        event_rets = self._events[opcode]['ret']
        
        #extract the return items from event packet
        results = self._extract_opfunc_rets([], event_rets, fmlx_packet)

        #fire event-specific handler function
        self.__dict__[event_name].fire(**OrderedDict(results))

    def _handle_file(self, filepath):
        """ Extract opcode functions lists from YAML files
        Parameters:
        filepath -- path to YAML file that contain list of opcode functions
        """
        if filepath:
            #device opfuncs path is specified
            with open(filepath, 'r') as opfuncs_file:
                opfuncs_list = yaml.load(opfuncs_file.read(),Loader=yaml.Loader)

                if 'COMMANDS' in opfuncs_list:
                    self._commands += self._extract_opfuncs(opfuncs_list['COMMANDS'])
                    # print(self._commands)
                    # print('\n')
                
                if 'EVENTS' in opfuncs_list:
                    self._events += self._extract_opfuncs(opfuncs_list['EVENTS'])

                if 'ENUMS' in opfuncs_list:
                    self._extract_enums(opfuncs_list['ENUMS'])

    def _extract_enums(self, enumitems):
        """ Extract opfunc items and convert them into structured py dictionaries
        Parameters: 
            - enumitems : list of enum dictionary obtained from YAML file
        """
        if not enumitems:
            return
        
        for enumitem in enumitems:
            # print (list(enumitem)[0])
            enumname = list(enumitem)[0]
            enumdesc = enumitem[enumname][0]['desc']
            enumtype = enumitem[enumname][1]['type']
            enumvals = enumitem[enumname][2]['value']

            #save minimal enum info for list printing
            enuminfo = {'name' : enumname, 'desc' : enumdesc}
            self._enums.append(enuminfo)

            #create enum objects inside FMLXDeviceUtils
            self.__dict__[enumname] = FmlxEnum(enumdesc)
            for eitem in enumvals:
                name = list(eitem)[0]
                val  = eitem[name][0]
                desc = eitem[name][1]
                self.__dict__[enumname].add_item(name, val, desc)

            #create datatype conversion and fetch function
            self._fetch_funcs[enumname] = self._fetch_funcs[enumtype]
            if(self._usePythonnet):
                self._dotnet_datatype[enumname] = self._dotnet_datatype[enumtype]
            else:
                self._c_datatype[enumname] = self._c_datatype[enumtype]

    def _extract_opfuncs(self, items, depth = 0):
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

        #check if items only contain single item or is a opfunc description
        if (not hasattr(items, '__len__')) or (isinstance(items, str)):
            return items

        # print (items)

        #process items based on current item depth level
        items_binder = []
        item_dict = {}
        for item in items:
            key_name =  (list(item)[0])
            # print (key_name)
            if depth == 0 :
                #top level (opfunc name)
                item_dict = {}
                item_dict['name'] = key_name
                item_dict.update(self._extract_opfuncs(item[key_name], 1))
                items_binder.append(item_dict)
            
            elif depth == 1 :
                #opfunc attribute levels
                item_dict[key_name] = self._extract_opfuncs(item[key_name], 2)
                items_binder = item_dict

            elif depth == 2 :
                #arg and return list level
                item_dict = {}
                item_dict['name'] = key_name
                item_dict['type'] = item[key_name]
                items_binder.append(item_dict)

        return items_binder
    
    def _make_commands(self):
        """ Convert extracted commands into functions """
        for cmd in self._commands:
            if not cmd['op']:
                raise Warning('Opcode is unspecified for command : {}'.format(cmd['name']))

            #create callable opcode functions
            self.__dict__[cmd['name']] = partial(self.send_command,cmd['name'], cmd['op'], cmd['arg'], cmd['ret'])
            
            #attach function description
            self._make_opfunc_description(cmd)
            
    def _make_events(self):
        """ Convert extracted events into functions """
        temp_event = {}
        for event in self._events:
            if not event['op']:
                raise Warning('Opcode is unspecified for event : {}'.format(event['name']))

            #create event dictionaries
            temp_event[event['op']] = {'name' : event['name'], 'ret' : event['ret']}

            #create hook interface for every events
            self.__dict__[event['name']] = EventHook()

            #attach function description
            self._make_opfunc_description(event)

        #update the local lists with the new dictionaries
        self._events = temp_event

    def _make_opfunc_description(self, opfunc):
        """ Create callable funtion to describe selected opcode function """
        s_return = self._opfunc_returns_to_string(opfunc)
        try:
            s_args = self._opfunc_args_to_string(opfunc)
        except:
            s_args = ''
        
        try:
            desc_text = opfunc['desc']
        except:
            desc_text = "This opcode doesn't have description field"
        
        output_text = '({}) = {}({}) \n'.format(s_return, opfunc['name'], s_args)
        output_text += '{}\n'.format('-'*(len(output_text) - 2))
        output_text += desc_text

        self.__dict__[opfunc['name']].__dict__['description'] = partial(self._print_description, output_text)

    def _opfunc_returns_to_string(self, opfunc):
        """ Convert list of opfunction returns to comma separated string """
        s_return = ''
        if opfunc['ret']:
            return_list = [("%(type)s %(name)s" % ret) for ret in opfunc['ret']]
            s_return = ", ".join(return_list)
        else:
            s_return = "None"

        return s_return

    def _opfunc_args_to_string(self, opfunc):
        """ Convert list of opfunction arguments to comma separated string """
        s_args = ''
        if opfunc['arg']:
            arg_list = [("%(type)s %(name)s" % arg) for arg in opfunc['arg']]
            s_args = ", ".join(arg_list)

        return s_args 

    def _print_description(self, desc):
        """ Partial Function template for printing opfunction description """
        print (desc)

    def _extract_opfunc_rets(self, args, rets, packet):
        """Extract the return items of opfunctions from packet
        Parameters:
        args   -- list of opfunction arguments
        rets   -- list of opfunction returns
        packet -- the fmlx packet to be extracted
        """
        results = []
        for ret in rets:
            if(self._usePythonnet):
                conv_type = self._py_datatype[self._dotnet_datatype[ret['type']]]
            else:
                conv_type = self._ret_dataType[ret['type']]
            fetch_func = self._fetch_funcs[ret['type']]

            if ret['type'][-2:] == '_c': # array with length info. The info is always in previous index
                argrets = args + [item[1] for item in results] #in old opcodes, it is possible the "previous" is in arguments
                len_ret = argrets[len(argrets) - 1]
                ret_val = conv_type(fetch_func(packet, len_ret))   
            elif ret['type'][:5] == 'Array':
                # array without number of items information
                ret_val = []
                try:
                    #exhaust data fetching until end of packet
                    while True:
                        ret_val.append(fetch_func(packet))
                except:
                    pass

                ret_val = conv_type(ret_val)
            else:
                # single/non-array data
                ret_val = conv_type(fetch_func(packet))
        
            results.append((ret['name'], ret_val))
        
        return results

    def uncaughtExceptionHandler(self,exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        self._logger.critical('Uncaught Exception',exc_info=(exc_type, exc_value, exc_traceback))

class FmlxDevicePublisher(object):
    def __init__(self, comm_driver, address,  use_single_precision = False, usePythonnet = True ):

        if(isPythonnetImported):
            self._usePythonnet = usePythonnet
        else:
            self._usePythonnet = False

        if(not self._usePythonnet and sys.version_info[0] < 3):
            if(not isPythonnetImported):
                raise NotImplementedError('CorePython is Not yet Implemented on python2!, Please use python3 or install Pythonnet first')
            else:
                self._usePythonnet = True

        print('Using Pythonnet : {0}'.format(self._usePythonnet))
        
        #.NET datatype for FMLX Core function calls
        if(self._usePythonnet):
            #equivalent .NET data type in python
            self._py_datatype = {
                Boolean : bool,
                UInt16  : int,
                UInt32  : int,
                Int16   : int,
                Int32   : int,
                Single  : float,
                Double  : float,
                String  : str,
                Array[UInt16] : partial(array, 'H'),
                Array[Int16]  : partial(array, 'h'),
                Array[UInt32] : partial(array, 'L'),
                Array[Int32]  : partial(array, 'l'),
                Array[Double] : partial(array, 'd')
            }
            self._dotnet_datatype = {
                'Boolean' : Boolean,
                'UInt16'  : UInt16,
                'UInt32'  : UInt32,
                'Int16'   : Int16,
                'Int32'   : Int32,
                'Float'   : Single,
                'Double'  : Double,
                'String'  : String,
                'Array_UInt16' : Array[UInt16],
                'Array_UInt32' : Array[UInt32],
                'Array_Int16'  : Array[Int16],
                'Array_Int32'  : Array[Int32],
                'Array_Float'  : Array[Single],
                'Array_Double' : Array[Double],
                'Array_UInt16_c' : Array[UInt16],
                'Array_UInt32_c' : Array[UInt32],
                'Array_Int16_c'  : Array[Int16],
                'Array_Int32_c'  : Array[Int32],
                'Array_Double_c' : Array[Double]
            }
            self._fetch_funcs = {
                'Boolean' : FmlxPacket.FetchBool,
                'UInt16'  : FmlxPacket.FetchUInt16,
                'Int16'   : FmlxPacket.FetchInt16,
                'UInt32'  : FmlxPacket.FetchUInt32,
                'Int32'   : FmlxPacket.FetchInt32,
                'Float'  : FmlxPacket.FetchFloat,
                'Double'  : FmlxPacket.FetchDouble,
                'String'  : FmlxPacket.FetchString,
                'Array_UInt16_c' : FmlxPacket.FetchUInt16Array,
                'Array_Int16_c'  : FmlxPacket.FetchInt16Array,
                'Array_UInt32_c' : FmlxPacket.FetchUInt32Array,
                'Array_Int32_c'  : FmlxPacket.FetchInt32Array,
                'Array_Float_c' : FmlxPacket.FetchFloatArray,
                'Array_Double_c' : FmlxPacket.FetchDoubleArray,
                'Array_UInt16' : FmlxPacket.FetchUInt16,
                'Array_Int16'  : FmlxPacket.FetchInt16,
                'Array_UInt32' : FmlxPacket.FetchUInt32,
                'Array_Int32'  : FmlxPacket.FetchInt32,
                'Array_Float'  : FmlxPacket.FetchFloat,
                'Array_Double' : FmlxPacket.FetchDouble
            }

        #c datatype for FMLX Core function calls
        else:
            self._c_datatype = {
                'Boolean' : ctypes.c_uint16,
                'UInt16'  : ctypes.c_uint16,
                'UInt32'  : ctypes.c_uint32,
                'Int16'   : ctypes.c_int16,
                'Int32'   : ctypes.c_int32,
                'Float'   : ctypes.c_float,
                'Double'  : ctypes.c_double,
                'String'  : str,
                'Array_UInt16' : lambda x : list(map(ctypes.c_uint16,x)),
                'Array_UInt32' : lambda x : list(map(ctypes.c_uint32,x)),
                'Array_Int16'  : lambda x : list(map(ctypes.c_int16,x)),
                'Array_Int32'  : lambda x : list(map(ctypes.c_int32,x)),
                'Array_Float'  : lambda x : list(map(ctypes.c_float,x)),
                'Array_Double' : lambda x : list(map(ctypes.c_double,x)),
                'Array_UInt16_c' : lambda x : list(map(ctypes.c_uint16,x)),
                'Array_UInt32_c' : lambda x : list(map(ctypes.c_uint32,x)),
                'Array_Int16_c'  : lambda x : list(map(ctypes.c_int16,x)),
                'Array_Int32_c'  : lambda x : list(map(ctypes.c_int32,x)),
                'Array_Float_c'  : lambda x : list(map(ctypes.c_float,x)),
                'Array_Double_c' : lambda x : list(map(ctypes.c_double,x))
            }
            # pythonic return data type
            self._ret_dataType = {
                'Boolean' : bool,
                'UInt16'  : int,
                'UInt32'  : int,
                'Int16'   : int,
                'Int32'   : int,
                'Float'   : float,
                'Double'  : float,
                'String'  : str,
                'Array_UInt16' : list,
                'Array_UInt32' : list,
                'Array_Int16'  : list,
                'Array_Int32'  : list,
                'Array_Float'  : list,
                'Array_Double' : list,
                'Array_UInt16_c' : list,
                'Array_UInt32_c' : list,
                'Array_Int16_c'  : list,
                'Array_Int32_c'  : list,
                'Array_Float_c'  : list,
                'Array_Double_c' : list
            }
            self._fetch_funcs = {
                'Boolean' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchBool,
                'UInt16'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16,
                'Int16'   : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16,
                'UInt32'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32,
                'Int32'   : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32,
                'Float'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloat,
                'Double'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDouble,
                'String'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchString,
                'Array_UInt16_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16Array,
                'Array_Int16_c'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16Array,
                'Array_UInt32_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32Array,
                'Array_Int32_c'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32Array,
                'Array_Float_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloatArray,
                'Array_Double_c' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDoubleArray,
                'Array_UInt16' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt16,
                'Array_Int16'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt16,
                'Array_UInt32' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchUInt32,
                'Array_Int32'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchInt32,
                'Array_Float'  : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchFloat,
                'Array_Double' : FormulatrixCorePy.FmlxPacket.FmlxPacket.FetchDouble
            }

        if(self._usePythonnet):
            self._ctrl = FmlxController(comm_driver,use_single_precision)
        else:
            self._ctrl = FormulatrixCorePy.FmlxController.FmlxController(comm_driver,use_single_precision)
        self._address = address
        """ Initialize the class
        Parameters:
        comm_driver      -- communication driver
        address          -- target fmlx device address
        opfuncs_filepath -- path to YAML file that contain list of opcode functions
        log_handler      -- logging output handler. Check logging package for available handlers
        """
        self._gen_opfuncs_fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), './generic_opfuncs.yaml')
        #setting the communication and save address
        self._driver = comm_driver
        self._address = address # address for publisher is 0

        #extract enums, command, event functions
        self._commands = []
        self._events = []
        self._enums = [] #minimal enum storage for printing enum list
        self._publishers = []
        self._handle_file(self._gen_opfuncs_fpath)

        self._use_single_precision = use_single_precision
        self._packet_id = 0
        #make callable command
        self._make_publishers()

        #sort based on opcode
        self._publishers = sorted(self._publishers, key = itemgetter('op'))

    def connect(self):
        """Connecting the communication"""
        self._driver.Connect()


    def disconnect(self):
        """Disconnecting the communication"""
        self._driver.Disconnect()


    def is_connected(self):
        """Check if communication is already connected"""
        return self._driver.Connected

    def _make_publishers(self):
        """ Convert extracted commands into functions """
        for publisher in self._publishers:
            # print (publisher['op'])
            if not 'op' in publisher:
                raise Warning('Opcode is unspecified for command : {}'.format(publisher['name']))

            #create callable opcode functions
            func_string = 'publish_' + publisher['name']
            # print (func_string)
            self.__dict__[func_string] = partial(self.send_publish, publisher['op'], publisher['arg'])
            
            #attach function description
            # self._make_opfunc_description(publisher)

    def send_publish(self, opcode, params, *args):
        # checking for incorrect input arguments
        if len(args) != len(params):
            lenparam = len(params)
            if lenparam == 0:
                warntext = 'Function does not take any argument'
            else:
                warntext = 'Function requires {} argument(s), which is/are : ('.format(lenparam)
                param_list = [("%(type)s %(name)s" % param) for param in params]
                warntext += ", ".join(param_list) + ')'
            raise TypeError(warntext)
        
        if(self._usePythonnet):
            packet = FmlxPacket.Overloads[UInt16,Boolean](2048 + opcode,self._use_single_precision)
            # packet = FmlxPacket(BitConverter.GetBytes(0),self._use_single_precision) # just for the constructor, next must be clear method
            packet.Clear()
            for index,param in enumerate(params):
                packet.Add(self._dotnet_datatype[param['type']](args[index]))
            packet.Address = self._address
            packet.Finalize()
            
            raw_data = []
            for byteData in packet.RawPacket:
                raw_data.append(byteData)
            self._driver.Write(raw_data)
        else:
            packet = FormulatrixCorePy.FmlxPacket.FmlxPacket()
            packet.Opcode = 2048 + opcode
            packet.Address = self._address
            for index,param in enumerate(params):
                packet.Add(self._c_datatype[param['type']](args[index]))
            
            self._driver.Write(packet.ToRaw)

    def _extract_opfuncs(self, items, depth = 0):
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

        #check if items only contain single item or is a opfunc description
        if (not hasattr(items, '__len__')) or (isinstance(items, str)):
            return items

        # print (items)

        #process items based on current item depth level
        items_binder = []
        item_dict = {}
        for item in items:
            key_name =  (list(item)[0])
            # print (key_name)
            if depth == 0 :
                #top level (opfunc name)
                item_dict = {}
                item_dict['name'] = key_name
                item_dict.update(self._extract_opfuncs(item[key_name], 1))
                items_binder.append(item_dict)
            
            elif depth == 1 :
                #opfunc attribute levels
                item_dict[key_name] = self._extract_opfuncs(item[key_name], 2)
                items_binder = item_dict

            elif depth == 2 :
                #arg and return list level
                item_dict = {}
                item_dict['name'] = key_name
                item_dict['type'] = item[key_name]
                items_binder.append(item_dict)

        return items_binder

    def _handle_file(self, filepath):
        """ Extract opcode functions lists from YAML files
        Parameters:
        filepath -- path to YAML file that contain list of opcode functions
        """
        if filepath:
            #device opfuncs path is specified
            with open(filepath, 'r') as opfuncs_file:
                opfuncs_list = yaml.load(opfuncs_file.read(),Loader=yaml.Loader)

                if 'PUBLISHER' in opfuncs_list:
                    self._publishers += self._extract_opfuncs(opfuncs_list['PUBLISHER'])
                    # print(self._publishers)