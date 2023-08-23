import os
import sys
import logging
import logging.handlers
import platform
from datetime import datetime

def SetupLogger(logger,fileName=None,logLevel = logging.NOTSET,verbose=False,verboseLevel=logging.NOTSET, rotateFile=False,rotMaxFileSize=5000000,rotBackupCnt=1,):
    logFileFormat = '%(asctime)s,%(name)s,%(levelname)s,%(message)s'
    logConsoleFormat = '%(name)s - %(message)s'
    log_handler = logger
    if (fileName):
        if (rotateFile):
            fileLogger = CreateRotatingFileHandler(fileName,logLevel,logFileFormat,rotMaxFileSize,rotBackupCnt);
        else:
            fileLogger = CreateFileHandler(fileName,logLevel,True,logFileFormat)
        log_handler.addHandler(fileLogger)    
    if (verbose):
        verboseLogger = CreateConsoleHandler(verboseLevel,logConsoleFormat)
        log_handler.addHandler(verboseLogger)
    
    return log_handler

def CreateFileHandler(fileName = None,logLevel = logging.NOTSET,isFileNameUsingDate = False, loggingFormat = '%(asctime)s.%(msecs)03d,%(name)s,%(levelname)s,%(message)s'):
    try:
        os.stat('log')
    except FileNotFoundError:
        os.mkdir('log')
    # create file handler which logs even debug messages
    if(isFileNameUsingDate):
        str_date ='_'
        str_date +=datetime.now().strftime("%Y%m%d%H%M%S%f")[0:-3]
    else:
        str_date = ''
    
    if(fileName):
        if(platform.system()=='Windows'):
            fh = logging.FileHandler('log\{0}{1}.log'.format(fileName,str_date))
        elif(platform.system()=='Linux' or platform.system()=='linux'):
            fh = logging.FileHandler('log/{0}{1}.log'.format(fileName,str_date))
    else:
        if(platform.system()=='Windows'):
            fh = logging.FileHandler('log\FmlxLogger{0}.log'.format(str_date))
        elif(platform.system()=='Linux' or platform.system()=='linux'):
            fh = logging.FileHandler('log/FmlxLogger{0}.log'.format(str_date))
    fileFormater = logging.Formatter(loggingFormat,'%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fileFormater)
    fh.setLevel(logLevel)

    return fh

def CreateRotatingFileHandler(fileName = None,logLevel = logging.NOTSET, loggingFormat = '%(asctime)s.%(msecs)03d,%(name)s,%(levelname)s,%(message)s',maxBytes = 10000000,backupCount=1):
    try:
        os.stat('log')
    except FileNotFoundError:
        os.mkdir('log')
    # create file handler which logs even debug messages
    if(fileName):
        if(platform.system()=='Windows'):
            fh = logging.handlers.RotatingFileHandler('log\{0}.log'.format(fileName),maxBytes=maxBytes, backupCount=backupCount)
        elif(platform.system()=='Linux' or platform.system()=='linux'):
            fh = logging.handlers.RotatingFileHandler('log/{0}.log'.format(fileName),maxBytes=maxBytes, backupCount=backupCount)
    else:
        if(platform.system()=='Windows'):
            fh = logging.handlers.RotatingFileHandler('log\FmlxLogger.log')
        elif(platform.system()=='Linux' or platform.system()=='linux'):
            fh = logging.handlers.RotatingFileHandler('log/FmlxLogger.log')
    fileFormater = logging.Formatter(loggingFormat,'%Y-%m-%d %H:%M:%S')
    fh.setFormatter(fileFormater)
    fh.setLevel(logLevel)

    return fh

def CreateConsoleHandler(logLevel = logging.NOTSET, loggingFormat = '%(name)s - %(message)s'):
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logLevel)

    formatter = logging.Formatter(loggingFormat)
    ch.setFormatter(formatter)
    return ch
