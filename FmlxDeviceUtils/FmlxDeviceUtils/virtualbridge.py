import logging
import time

import canlib
import sys
import clr
import os
from threading import Thread

sys.path.append(r"../Include")
sys.path.append(r"../FmlxDeviceUtils")
#clr.AddReference("Formulatrix.Core.Protocol")
#clr.AddReference("Formulatrix.Core.Protocol.Can.KVaser.Win")
#clr.AddReference("Formulatrix.Core.Protocol.SLCan.Win")
#clr.AddReference("Formulatrix.Core.Protocol.Serial.Win")
#sys.path.append(r"../../VirtualCanBridge/VirtualCanBridge/bin/Release")
clr.AddReference("VirtualBridge")


from VirtualBridge import SerialCanConnector

class VirtualBridge:
    def __init__ (self,comport,vcanlibchannel):
        self.vcanbridge = SerialCanConnector(comport,vcanlibchannel)
        self.isConnected = False
    def connect(self):
        self.vcanbridge.Connect()
        if self.vcanbridge.isConnected==True:
            self.isConnected=True
        else:
            self.isConnected=False
    def disconnect(self):
        if self.vcanbridge.isConnected==True:
            self.vcanbridge.Disconnect()
    
    def isConnect(self):
        return self.isConnected
