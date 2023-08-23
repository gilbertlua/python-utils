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

motor_x = fopleyMotor.CFopleyMotorModular(w0,0,'motor x')
motor_y = fopleyMotor.CFopleyMotorModular(w0,1,'motor y')
motor_z = fopleyMotor.CFopleyMotorModular(w1,0,'motor z')
motor_teta = fopleyMotor.CFopleyMotorModular(w1,1,'motor teta')
motor_hand = fopleyMotor.CFopleyMotorModular(w2,0,'motor hand')

def maju_mundur():
    motor_x.move_motor_abs(300,1000,1000,1000)
    motor_y.move_motor_abs(300,1000,1000,1000)
    motor_x.wait_move()
    motor_y.wait_move()
    motor_x.move_motor_abs(-300,1000,1000,1000)
    motor_y.move_motor_abs(-300,1000,1000,1000)
    motor_x.wait_move()
    motor_y.wait_move()