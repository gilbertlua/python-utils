'''
Created on Sep 22, 2021

@author: Formulatrix
'''
from Formulatrix.Core.Logger import IFmlxLogger
from System import *
import logging
class Pythonlogger(IFmlxLogger):
    __namespace__ = "Formulatrix.Core.Logger"
    def __init__(self,name,log_handler=None,level = logging.DEBUG):
        self.logger=logging.getLogger(name)
        self.logger.setLevel(level)
        if(log_handler!=None):
            self.logger.addHandler(log_handler)
    
    def LogInfo(self,format, args):
        self.logger.info(format)
    
    def LogWarn(self,format, args):
        self.logger.warning(format)
    
    def LogError(self,format, args):
        self.logger.error(format)
    
    def LogDebug(self,format, args):
        self.logger.debug(format)
    
    def LogException(self, exception, format=None, args=None):
        if(format is None):
            self.logger.error(str(exception))
            return
        self.logger.error(format)
    
    def LogUserAction(self,format, args):
        self.logger.info(format,args)

class Nulllogger(IFmlxLogger):
    __namespace__ = "Formulatrix.Core.Logger"
    def __init__(self,name,log_handler=None,level = logging.DEBUG):
        pass
    
    def LogInfo(self,format, args):
        pass
    
    def LogWarn(self,format, args):
        pass
    
    def LogError(self,format, args):
        pass
    
    def LogDebug(self,format, args):
        pass
    
    def LogException(self, exception, format=None, args=None):
        pass
    
    def LogUserAction(self,format, args):
        pass

