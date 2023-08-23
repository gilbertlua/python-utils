''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../Include'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
from Formulatrix.Core.Protocol import FmlxController,FmlxTimeoutException
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time
import threading
from functools import partial
import argparse
import inspect
from enum import Enum
import ntpath
ntpath.basename("a/b/c")
if(sys.version_info[0] >= 3):
    import tkinter as tk
    from tkinter import ttk
    from tkinter import filedialog
    from tkinter import messagebox
else:
    import Tkinter as tk
    #from Tkinter import ttk
    import ttk                          #python2 separate ttk package
    #from Tkinter import messagebox
    import tkMessageBox as messagebox
    import tkFileDialog as filedialog
    import tkMessageBox


class CYaml2Gui(tk.Frame):

    class menu_type(Enum):
        enum_op_menu = 0
        enum_user_app_menu = 1

    def _descCallback(self,fmlxDevice,index):
        try:
            messagebox.showinfo('{0} description '.format(fmlxDevice._commands[index]['name']),message='desc : {0} '.format(fmlxDevice._commands[index]['desc']))
        except(KeyError):
            messagebox.showinfo('{0}'.format(fmlxDevice._commands[index]['name']),message='No Description for this commands')

    def _addPlotCallback(self, fmlxDevice, index):
        print('Add plot to selected function')

    def _fun(self,fmlxDevice,index,textBoxObjs):
        data_types = []
        for data_type in fmlxDevice._commands[index]['arg']:
            data_types+=[data_type['type']]
        args = []
        try:
            for i,textBox in enumerate(textBoxObjs):        
                if(data_types[i] in ['Double','Float']):
                    args +=[float(textBox.get("1.0",'end-1c'))]
                elif(data_types[i] in ['Int32','UInt32','Int16','UInt16']):
                    args +=[int(textBox.get("1.0",'end-1c'))]
                elif (data_types[i] in ['Boolean']):
                    val = 1 if textBox.get() == 'True' else 0
                    args+=[int(val)]
                elif(data_types[i] in ['String']):
                    args +=[str(textBox.get("1.0",'end-1c'))]
                elif(data_types[i] in ['Array_UInt16_c','Array_Int16_c','Array_UInt32_c','Array_Int32_c','Array_UInt16','Array_Int16','Array_UInt32','Array_Int32']):
                    s = list(map(int,textBox.get("1.0",'end-1c').split(',')))
                    args +=[s]
                elif(data_types[i] in ['Array_Float_c','Array_Double_c','Array_Float','Array_Double']):
                    s = list(map(float,textBox.get("1.0",'end-1c').split(',')))
                    args +=[s]
            value = getattr(fmlxDevice,fmlxDevice._commands[index]['name'])(*args)
            print('{0}({1}) --> {2}'.format(fmlxDevice._commands[index]['name'],','.join(map(str,args)),value))
        except ValueError:
            print('Error, Please fill all input arguments')

    def _comboBoxCommandCountCallback(self,device_index,event):
        selectedIndex = int(self._comboBoxCommandCounts[device_index].get())
        for i in range(selectedIndex):
            self._opcodeFrames[device_index][i].grid(column = 0, row = 2+i, sticky = 'w',columnspan = 2)
        for i in range(selectedIndex,self._max_sub_frame):
            self._opcodeFrames[device_index][i].grid_remove()

    def _comboBoxSelectedCallback(self,device_index,frame_index,combobox_index,event):
        x = frame_index
        e = device_index
        # destroy the prev grid if there is any
        for inputTxt in self._inputsTxts[e][x]:
            inputTxt.destroy()
        for commandArgumentsLabel in self._commandsArgumentsLabels[e][x]:
            commandArgumentsLabel.destroy()
        if(self._buttonsCommands[e][x] != []):
            self._buttonsCommands[e][x].destroy()
        if(self._buttonsDescs[e][x]):
            self._buttonsDescs[e][x].destroy()
        if(self._buttonAddPlots[e][x]):
            self._buttonAddPlots[e][x].destroy()
        # then show the grid of the selected index
        rowButton = 1    
        # show all arguments
        inputTxt = []
        commandLabelArgument = []
        if(combobox_index==None):
            selectedCommandIndex = int(self._comboBoxs[e][x].get().split('.')[0])
        else:
            selectedCommandIndex=combobox_index
        for i,arg in enumerate(self._fmlxDevices[e]._commands[selectedCommandIndex]['arg']):
            commandLabelArgument+=[ttk.Label(self._opDetailFrames[e][x],text='{0} ({1}) :'.format(arg['name'],arg['type']))]
            if (arg['type']=='Boolean'):
                inputTxt+=[ttk.Combobox(self._opDetailFrames[e][x],width=10,state='readonly',values=('True','False'))]
            else:
                inputTxt += [tk.Text(self._opDetailFrames[e][x],height = 1,width = 10)]
            inputTxt[i].grid(column = 1, row = i+2,padx=5,pady=5,sticky = tk.W )
            commandLabelArgument[i].grid(column = 0, row = i+2 ,padx=5,pady=5,sticky = tk.W)
            rowButton += 1 
        self._inputsTxts[e][x]=inputTxt
        self._commandsArgumentsLabels[e][x]=commandLabelArgument
        commands_callback = partial(self._fun,self._fmlxDevices[e],selectedCommandIndex,inputTxt)
        descs_callback = partial(self._descCallback,self._fmlxDevices[e],selectedCommandIndex)
        self._buttonsCommands[e][x] = ttk.Button(self._opDetailFrames[e][x],text='Send',command = commands_callback)
        self._buttonsDescs[e][x] = ttk.Button(self._opDetailFrames[e][x],text='Desc',command = descs_callback)
        self._buttonsCommands[e][x].grid(column = 1, row = rowButton+1,padx=5,pady=5,sticky = tk.W)
        self._buttonsDescs[e][x].grid(column = 0, row = rowButton+1,padx=5,pady=5,sticky = tk.W)
        rowButton+=1
        ret = self._fmlxDevices[e]._commands[selectedCommandIndex]['ret']

        if len(ret) != 0:
            self._buttonAddPlots[e][x] = ttk.Button(self._opDetailFrames[e][x], text='Plot', command=self._addPlotCallback)
            self._buttonAddPlots[e][x].grid(column=0, row=rowButton + 1, padx=5, pady=5, sticky=tk.W)

    def _comboBoxAutoSearchCallback(self,device_index,selected_index,event):
        x = selected_index
        e = device_index
        value = event.widget.get()
        if value == '':
            self._comboBoxs[e][x]['values'] = self._comboBoxLists[e]
        else:
            data = []
            for item in self._comboBoxLists[e]:
                if value.lower() in item.lower():
                    data.append(item)
            self._comboBoxs[e][x]['values'] = data
            
    def _comboBoxPublisherCallback(self):
        pass
    
    def __init__(self,fmlxDevices,windowtitle='yaml2gui'):
        self._comboBoxsSelectedCallbacks = []
        self._comboBoxs = []
        self._fmlxDevices = fmlxDevices
        self._max_sub_frame = 4
        self._opFrames = []
        self._comboBoxCommandCounts = []
        self._comboBoxLists = []
        self._opcodeFrames = []
        self._opDetailFrames = []
        self._commands_callbacks = []
        self._descs_callbacks = []
        self._buttonsCommands = []
        self._buttonsDescs = []
        self._inputsTxts = []
        self._buttonAddPlots = []
        self._buttonAddSeqs = []
        self._commandsArgumentsLabels = []
        self._window = tk.Tk()
        self._window.title(windowtitle)
        self._window.geometry('900x700')
        
        # scrollbar = tk.Scrollbar(self._window)
        # scrollbar.grid( column = 3, row = 0,sticky = 'nse', rowspan=3)
        
        # creating Combobox for the num of command box count
        tk.Frame(self._window).grid(row=1, column=1, sticky="w")
        coloum_shift = 0
        for e,fmlxDevice in enumerate(self._fmlxDevices):
            try:
                app_name = fmlxDevice.get_app_name()
                version = fmlxDevice.get_version()
            except FmlxTimeoutException:
                print('warning, timeout..')
                app_name = 'Disconnected'
                version = 'x.x.x'
            except TimeoutError: # CorePy compability
                print('warning, timeout..')
                app_name = 'Disconnected'
                version = 'x.x.x'
            
            device_address = fmlxDevice._address

            opFramesText = '{0} {1} addr : {2}'.format(app_name,version,device_address)
            # frame for device specific opcode
            self._opFrames.append(ttk.LabelFrame(self._window, text=opFramesText))
            # tk.Scrollbar(self._opFrames[e], orient="vertical").grid(row=0, column=2, sticky='ns',rowspan = 5)
            

            ttk.Button(self._opFrames[e],text='Get EEPROM Config',command = fmlxDevice.get_eeprom_config).grid(column = 0,row = 0)
            ttk.Button(self._opFrames[e],text='Set EEPROM Config',command = fmlxDevice.set_eeprom_config).grid(column = 1,row = 0)
            
            ttk.Label(self._opFrames[e],text='count : ').grid(column = 0, row = 1,sticky=tk.W)
            self._comboBoxCommandCounts.append(ttk.Combobox(self._opFrames[e], width=2,state = 'readonly'))
            self._comboBoxCommandCounts[e]['values'] = list(range(1,self._max_sub_frame+1))
            self._comboBoxCommandCounts[e].bind("<<ComboboxSelected>>", partial(self._comboBoxCommandCountCallback,e))
            self._comboBoxCommandCounts[e].current(self._max_sub_frame-1)
            self._comboBoxCommandCounts[e].grid(column = 1, row = 1,sticky = tk.W)
            self._comboBoxLists.append([])
            for index,command in enumerate(fmlxDevice._commands):
                tabName = '{0}.{1} , op : {2}'.format(index,command['name'],command['op'])
                self._comboBoxLists[e]+=[tabName]
            
            self._opFrames[e].grid(column = coloum_shift+e, row = 0,sticky = 'nsew')
            self._opcodeFrames.append([])
            self._opDetailFrames.append([])
            for i in range(self._max_sub_frame):
                #create group box
                self._opcodeFrames[e].append(ttk.LabelFrame(self._opFrames[e] , text='Opcode List'))
                # opcodeFrames[i].pack(fill=tk.BOTH,expand=0)
                self._opDetailFrames[e].append(ttk.LabelFrame(self._opcodeFrames[e][i], text='Detail'))
                self._opDetailFrames[e][i].grid(column = 0, row = 2,sticky = tk.W)

            self._commands_callbacks.append([])
            self._descs_callbacks.append([])
            self._buttonsCommands.append([])
            self._buttonsDescs.append([])
            self._inputsTxts.append([])
            self._buttonAddPlots.append([])
            self._buttonAddSeqs.append([])
            self._commandsArgumentsLabels.append([])
            self._comboBoxsSelectedCallbacks.append([])
            for i in range(self._max_sub_frame):
                self._commands_callbacks[e].append([])
                self._descs_callbacks[e].append([])
                self._buttonsCommands[e].append([])
                self._buttonsDescs[e].append([])
                self._inputsTxts[e].append([])
                self._commandsArgumentsLabels[e].append([])
                self._buttonAddPlots[e].append([])
                self._buttonAddSeqs[e].append([])

            # creating Combobox
            self._comboBoxs.append([])
            for i in range(self._max_sub_frame):
                self._comboBoxs[e].append([])
                self._comboBoxs[e][i] = ttk.Combobox(self._opcodeFrames[e][i], width=40)
                self._comboBoxs[e][i]['values'] = self._comboBoxLists[e]
                self._comboBoxs[e][i].bind('<KeyRelease>', partial(self._comboBoxAutoSearchCallback,e,i))
                self._comboBoxsSelectedCallbacks[e]+=[partial(self._comboBoxSelectedCallback,e,i,None)]
                self._comboBoxs[e][i].bind("<<ComboboxSelected>>", self._comboBoxsSelectedCallbacks[e][i])
                self._comboBoxs[e][i].grid(column = 0, row = 1,sticky = tk.W)

             # initially, show all the subframes
            for i in range(self._max_sub_frame):
                self._opcodeFrames[e][i].grid(column = 0, row = 2+i, sticky = 'w',columnspan = 2)
        
        # frame for publisher
        # self._publisherFrame = ttk.LabelFrame(self._window, text='Publisher')
        # self._publisherFrame.grid(column = 1, row = 1,sticky = tk.W)
        # tk.Text(self._publisherFrame,height = 1,width = 10).grid()

        # frame for user specific button
        self._userAppMainFrame = ttk.LabelFrame(self._window, text='UserApp')
        self._userAppMainFrame.grid(column = e+1, row = 0,sticky = 'nsew')
        self._comboBoxUserAppCount = ttk.Combobox(self._userAppMainFrame, width=10,state = 'readonly')
        self._comboBoxUserAppCount['values'] = list(range(1,self._max_sub_frame+1))
        self._comboBoxUserAppCount.bind("<<ComboboxSelected>>", self._comboBoxUserAppCountCallback)
        self._comboBoxUserAppCount.current(self._max_sub_frame-1)
        self._comboBoxUserAppCount.grid(column = 0, row = 0,sticky = tk.W)
        self._userAppFrames = []
        self._userAppDetailFrames = []
        for i in range(self._max_sub_frame):
            #create group box
            self._userAppFrames += [ttk.LabelFrame(self._userAppMainFrame , text='User Menu {0}'.format(i+1))]
            # opcodeFrames[i].pack(fill=tk.BOTH,expand=0)
            self._userAppDetailFrames += [ttk.LabelFrame(self._userAppFrames[i], text='Detail')]
            self._userAppDetailFrames[i].grid(column = 0, row = 1,sticky = tk.W)
        
        self._comboBoxUserAppName = []
        self._comboBoxUserAppValueList = []
        # creating Combobox for user app
        for i in range(self._max_sub_frame):
            self._comboBoxUserAppName += [ttk.Combobox(self._userAppFrames[i], width=10,state = 'readonly')]
            self._comboBoxUserAppName[i].bind("<<ComboboxSelected>>", partial(self._comboBoxUserAppNameCallback,i,None))
            self._comboBoxUserAppName[i].grid(column = 0, row = 0,sticky = 'nswe',columnspan = 2)
            self._comboBoxUserAppName[i]['values'] = self._comboBoxUserAppValueList
        
        self._userAppArgs = []
        self._userAppCallbacks = []
        self._userAppTxtInputs = []
        self._userAppInputLabels = []
        self._userAppButton = []
        for i in range(self._max_sub_frame):
            self._userAppArgs.append([])
            self._userAppCallbacks.append([])
            self._userAppTxtInputs.append([])
            self._userAppInputLabels.append([])
            self._userAppButton.append([])
        
        self._numOfUserApp = 0

        for i in range(self._max_sub_frame):    
            self._userAppFrames[i].grid(column = 0, row = 1+i, sticky = 'w',columnspan = 2)
            
    def _comboBoxUserAppCountCallback(self,event):
        selectedIndex = int(self._comboBoxUserAppCount.get())
        for i in range(selectedIndex):
            self._userAppFrames[i].grid(column = 0, row = 1+i, sticky = 'w',columnspan = 2)
        for i in range(selectedIndex,self._max_sub_frame):
            self._userAppFrames[i].grid_remove()

    def _userAppButtonCallback(self,callback,textBoxObjs):    
        args = []
        try:
            for textBox in textBoxObjs:
                args +=[float(textBox.get("1.0",'end-1c'))]
            callback(*args)
        except ValueError:
            print('Error, Please fill all input arguments')

    def _comboBoxUserAppNameCallback(self,frame_index,combobox_index,event):
        x = frame_index
        # destroy the prev grid if there is any
        for inputTxt in self._userAppTxtInputs[x]:
            inputTxt.destroy()
        for commandArgumentsLabel in self._userAppInputLabels[x]:
            commandArgumentsLabel.destroy()
        if(self._userAppButton[x] != []):
            self._userAppButton[x].destroy()
        if(combobox_index==None):
            selectedIndex = int(self._comboBoxUserAppName[x].get().split('.')[0])
        else:
            selectedIndex=combobox_index
        args = self._userAppArgs[x][selectedIndex]
        self._userAppInputLabels[x] = []
        self._userAppTxtInputs[x] = []
        irow=0
        for i,arg in enumerate(args):
            irow+=1
            self._userAppInputLabels[x]+=[ttk.Label(self._userAppFrames[x] ,text='{0} :'.format(arg.name))]
            self._userAppTxtInputs[x]+= [tk.Text(self._userAppFrames[x] ,height = 1,width = 10)]
            self._userAppInputLabels[x][i].grid(column = 0, row = irow,padx=3,pady=3)
            self._userAppTxtInputs[x][i].grid(column = 1, row = irow,padx=3,pady=3)
            if(arg.default != inspect._empty):
                self._userAppTxtInputs[x][i].insert(tk.END,arg.default)    
        callback=partial(self._userAppButtonCallback,self._userAppCallbacks[x][selectedIndex],self._userAppTxtInputs[x])       
        self._userAppButton[x] = ttk.Button(self._userAppFrames[x],text='execute', width=30,command = callback)
        self._userAppButton[x].grid(column = 0, row = irow+1,padx=5,pady=5,columnspan = 2)
        
    def add_button(self,text,callback):
        self._comboBoxUserAppValueList+=['{0}.{1}'.format(self._numOfUserApp,text)]
        for i in range(self._max_sub_frame):
            self._userAppArgs[i] += [list(inspect.signature(callback).parameters.values())]
            self._userAppCallbacks[i]+=[callback]
            self._comboBoxUserAppName[i]['values'] = self._comboBoxUserAppValueList 
        self._numOfUserApp+=1

    def add_hotkey(self,tkinter_bind_modifier,enum_menu,frame_index):
        if(enum_menu == 0):
            self._window.bind(tkinter_bind_modifier, lambda event : self._buttonsCommands[frame_index].invoke())
        elif(enum_menu == 1):
            self._window.bind(tkinter_bind_modifier, lambda event : self._userAppButton[frame_index].invoke())


    def set_op_menu(self,device_index,frame_index,index):
        self._comboBoxs[device_index][frame_index].current(index)
        self._comboBoxsSelectedCallbacks[device_index](frame_index,index,None)

    def set_user_app_menu(self,frame_index,index):
        self._comboBoxUserAppName[frame_index].current(index)
        self._comboBoxUserAppNameCallback(frame_index,index,None)


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
        return filedialog.asksaveasfile(title=window_title).names

if __name__ == "__main__":
    # command line argument to config the yaml2gui
    parser = argparse.ArgumentParser(description="Formulatrix Yaml2GUI")
    parser.add_argument('-p', '--yamlPath',
                        help="yaml file path", type=str, nargs='?')
    parser.add_argument('-d', '--driverName',
                        help="driver name",choices=['FVaser','KVaser','FTDI','TCP','SerialPort','BleDevice','KVCanBridge'] ,  type=str, nargs='?')
    parser.add_argument('-c', '--comPort',
                        help="com port",type=str, nargs='?')
    parser.add_argument('-a', '--address', help="app FmlxProtocol address (busId)", type=int)
    
    args = parser.parse_args()
    if(args.yamlPath):
        filename = args.yamlPath
    else:
        print('Get your yaml file : ')
        filename = getPath(True, 'Your Yaml File')
        print(filename)

    if(args.driverName):
        driverName = args.driverName
    else:
        driverName = ''

    if(args.comPort):
        comPort = args.comPort
    else:
        comPort = ''

    if(args.address):
        address = args.address
    else:
        address = ''

    drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle(address=address,driver_name=driverName,comport=comPort)

    d = FmlxDevice(drv, address, filename)
    d.connect()

    CYaml2Gui(d,ntpath.split(filename)[1][:-5])