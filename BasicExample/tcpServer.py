''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
import ctypes
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils/'
sys.path.append(lib_path)
from FormulatrixCorePy.FmlxDrivers.TcpFmlxDriver import TcpServer
from FormulatrixCorePy.FmlxController import FmlxControllerSlave

address = 22
drv = TcpServer(hostName='localhost',port=322)

def illegalOpcode(pComm):
    pComm.SendError(FmlxControllerSlave.ErrorOpcode.ILLEGAL_OPCODE)

def getAppName(pComm):
    pComm.WriteRsp('FmlxProtocolSlave Test')

def getVersion(pComm):
    pComm.WriteRsp('3.2.2')

def echoUint32(pComm):
    pComm.WriteRsp(ctypes.c_uint32(pComm.ReadCmdUint32()))

commandCallbacks = [
    illegalOpcode,
    getVersion,
    getAppName,
    echoUint32
    ]

hostIfc = FmlxControllerSlave(drv, address = address,commandCallbacks=commandCallbacks,useSinglePrecision = True)