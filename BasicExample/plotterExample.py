''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
from Formulatrix.Core.Protocol import FmlxController
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time
import threading
from multiprocessing.connection import Client
import subprocess
import random
import math

PLOT_COUNT = 1
PORT_NUMBER = 432

def open_plotter_listener():
    import os
    text = "start python3 ..\FmlxDeviceUtils\FmlxDeviceUtils\Plotter.py -n{0} -x {1} -l {2} -p{3} -s".format(PLOT_COUNT,'1000','3',PORT_NUMBER)
    print(text)
    os.system(text)

def connect_plotter():
    global conn
    address = ('localhost', PORT_NUMBER)
    conn = Client(address)

def send_data(plot = 0, data = [322]):
    global conn
    data_string = ' '.join(str(x) for x in data)
    text = 'data p{0} {1}'.format(plot,data_string)
    # print (text)
    conn.send(text)

open_plotter_listener()
connect_plotter()

def test_send_data(loop = 0):
    count = 0
    if(loop == 0):
        while 1:
            for i in range(PLOT_COUNT):      
                send_data(i,[math.sin(1 * count * math.pi / 180 ), math.sin(2 * (120+count) * math.pi / 180), math.sin(4 * (240+count) * math.pi / 180)])
            count+=1
            time.sleep(0.001)
    else:
        for i in range(loop):
            for j in range(PLOT_COUNT):      
                send_data(j,[random.randint(1,100)])
            
# conn.send('close')
# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
# conn.close()

