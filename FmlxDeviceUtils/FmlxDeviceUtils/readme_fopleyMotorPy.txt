#harus import ini
import fopleyMotor
import fopleyUtilities as fu 

# connect pakek fmlxdeviceconnector dulu
drv,address=FmlxDeviceConnector.FmlxDeviceConnectorSingle(address=15,driver_name='KVaser')

# misalnya cell pakek instance c cuman buat contoh aja
c = FmlxDevice(drv, address, path_wambo_trinamic)
c.connect()

# fopleyMotor.CFopleyMotorModular
# constructornya diisi :
# 1. instance fmlx device, buat contoh disini makek 'c'
# 2. motor id-nya
# 3. string yg keluar kalo ada event, ini diisi terserah sesuai selera
# 4. enginerring value, klo gak diisi defaultnya 1
# 5. show_log, klo ada event, di print apa nggak. klo gak diisi nilai defaultnya 1

# misal motor 0 namanya elevelator
MOTOR_ID_ELEVATOR = 0
motor_elevator = fopleyMotor.CFopleyMotorModular(c,MOTOR_ID_ELEVATOR,'elevator')
# misal motor 1 namanya door
MOTOR_ID_DOOR = 1
motor_door = fopleyMotor.CFopleyMotorModular(c,MOTOR_ID_DOOR,'rover door')

# terus cara makeknya kayak kita makek yaml biasa, tapi tanpa motor id.
# misal mau nggerakin motor elevator id 0
# biasanya kita makek ini
c.move_motor_abs(0,1000,1000,1000,1000)
# bisa jadi kayak gini
motor_elevator.move_motor_abs(1000,1000,1000)
# bedanya tanpa motor id

#terus buat nge-wait movementnya, biasanya kita makek event handler yg bikin kodenya jadi panjang, contoh :
def handle_motor_move_done(motor_id,status,position):
    global move_done
    move_done = 1
    print('motor xxx done, bla222')
c.motor_move_done+= handle_motor_move_done
# terus bikin fungsi
def wait_move():
    global move_done
    while(move_done == 0):
        pass
# terus baru bikin sequencenya misal :
def maju_mundur():
    c.move_motor_abs(0,1000,1000,1000,1000)
    wait_move()
    c.move_motor_abs(0,0,1000,1000,1000)  
    wait_move()  

# kalo makek CfopleyMotor gak perlu nulis event handler atau wait move lagi karena udah dihandle di dalem classnya
# jadinya kayak gini klo pakek CFopleyMotor
def maju_mundur():
    motor_elevator.move_motor_abs(1000,1000,1000,1000)
    motor_elevator.wait_move() # fungsi wait move ini cuman buat motor elevator
    motor_elevator.move_motor_abs(1000,1000,1000,1000)
    motor_elevator.wait_move()
