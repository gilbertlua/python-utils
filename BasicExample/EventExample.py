''' basic fmlx script header '''
''' don't delete it! '''
import sys
import os
lib_path = r'../FmlxDeviceUtils/FmlxDeviceUtils'
sys.path.append(lib_path)
from FmlxDevice import FmlxDevice,FmlxDevicePublisher
import FmlxDeviceConnector

''' insert your additional header/ module here '''
import time
import fopleyMotor

''' your yaml path '''
path_wambo_trinamic= r"../DeviceOpfuncs/wambo_trinamic.yaml"

address = []
address_w0 = 1
address+=[address_w0]
address_w1 = 2
address+=[address_w1]
address_w2 = 3
address+=[address_w2]
drv=FmlxDeviceConnector.FmlxDeviceConnector(address_list=address)
w0 = FmlxDevice(drv[0], address[0], path_wambo_trinamic)
w0.connect()
w1 = FmlxDevice(drv[1], address[2], path_wambo_trinamic)
w1.connect()
w2 = FmlxDevice(drv[2], address[2], path_wambo_trinamic)
w2.connect()

def maju_mundur():
    w0.move_motor_abs(0,300,1000,1000,1000)
    w0_wait_move()
    w0.move_motor_abs(0,-300,1000,1000,1000)
    w0_wait_move()
    

def simple_sequence():
    w1.move_motor_abs(1,300,1000,1000,1000)
    w2_wait_move()
    w2.move_motor_abs(0,500,1000,1000,1000)
    w2_wait_move()

w0_move_done = 0

def w0_wait_move():
    global w0_move_done
    while(w0_move_done==0):
        time.sleep(0.001)
    w0_move_done = 0

def handle_w0_motor_move_done(motor_id,status,position):
    global w0_move_done
    print('w0 motor id:{0} status : {1} position : {2}'.format(motor_id,status,position))
    w0_move_done = 1
w0.motor_move_done+=handle_w0_motor_move_done

w1_move_done = 0

def w1_wait_move():
    global w1_move_done
    while(w1_move_done==0):
        time.sleep(0.001)
    w1_move_done = 0

def handle_w1_motor_move_done(motor_id,status,position):
    global w1_move_done
    print('w1 motor id:{0} status : {1} position : {2}'.format(motor_id,status,position))
    w1_move_done = 1
w1.motor_move_done+=handle_w1_motor_move_done

w2_move_done = 0

def w2_wait_move():
    global w2_move_done
    while(w2_move_done==0):
        time.sleep(0.001)
    w2_move_done = 0

def handle_w2_motor_move_done(motor_id,status,position):
    global w2_move_done
    print('w2 motor id:{0} status : {1} position : {2}'.format(motor_id,status,position))
    w2_move_done = 1
w2.motor_move_done+=handle_w2_motor_move_done

motor_a = fopleyMotor.CFopleyMotorModular(d,0,'motorA')
motor_b = fopleyMotor.CFopleyMotorModular(d,0,'motorB')