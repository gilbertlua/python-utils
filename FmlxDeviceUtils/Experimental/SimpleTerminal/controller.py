try:
    import tkinter as Tk # python 2
except ModuleNotFoundError:
    import tkinter as Tk # python 3
from GUI.simple_terminal_view import simple_terminal_view

import sys
import clr
import time
import signal

sys.path.append(r"../../Include")
sys.path.append(r"../../FmlxDeviceUtils")
# sys.path.append(r"automation")
#clr.AddReference("Formulatrix.Core.Protocol")
from FmlxDevice import FmlxDevice

class Controller:
    def __init__(self):
        self.root = Tk.Tk()
        drv=None
        address=0
        path_yaml=r"./DeviceOpfuncs/mini_wambo.yaml"
        self.mw = FmlxDevice(drv, address, path_yaml)
        self.update=None
        self.view = simple_terminal_view(self.root, self)
        self.selectedcommand=None
        self.populateCommand()
    def run(self):
        self.root.title("FMLX Terminal")
        self.root.geometry("1200x650")
        self.root.deiconify()
        self.root.mainloop()
    def getCommand(self,x):
        for command in self.mw._commands:
            if(command['name']==x):
                return command
        return None
    def WriteSelectedCommand(self,params):
        hasargumentEmpty=False
        msg=self.selectedcommand['name']
        msg=msg+"("
        valuelist=[]
        print(params)
        for param in params:
            if(list(param.values())[0]==''):
                hasargumentEmpty=True
            valuelist.append(list(param.values())[0])
        
        msg=msg+(", ".join(valuelist))
        msg=msg+")"       
           
        if(not hasargumentEmpty):
            self.update(msg)
    def executeSelectedCommand(self):
        print('execute')
    def getListName(self, arglist):
        list=[]
        for arg in arglist:
            list.append(arg['name'])
        return list
    def selected(self,x):
        self.selectedcommand=self.getCommand(x)        
        if(self.selectedcommand != None):
            self.clearFrame()
            description=""
            if("desc" in self.selectedcommand):
                description=self.selectedcommand['desc']
            self.updateDiscription(description,x)
            argListname=self.getListName(self.selectedcommand['arg'])
            for commandArg in self.selectedcommand['arg']:
                if commandArg['type']=="Boolean":
                    self.createComboBoxField(commandArg['name'])
                else:
                    self.createField(commandArg['name'])
    def populateCommand(self):        
        for command in self.mw._commands:
            self.addCommand(str(command['name']))
