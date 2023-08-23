import RPi.GPIO as GPIO
import wiringpi
import spidev
import time

#completer
import rlcompleter
import readline
readline.parse_and_bind("tab: complete")

# GPIO board means we refer to wiringpi pin numbering system
# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(4, GPIO.IN)

# wiringpi setup using wiringpi pin numbering system
PIN_HAS_DATA = 21 # bcm5 wiringpi 21
wiringpi.wiringPiSetup()
# wiringpi.pinMode(4,wiringpi.INPUT)
wiringpi.pinMode(PIN_HAS_DATA,wiringpi.INPUT) # bcm5

spi_tx = spidev.SpiDev()
spi_tx.open(0,0)
spi_tx.max_speed_hz=16000000

spi_rx = spidev.SpiDev()
spi_rx.open(0,1)
spi_rx.max_speed_hz=16000000

test_packet=[1,2,3,4,5,6,7,8,9,10]

def read_has_data():
    return wiringpi.digitalRead(PIN_HAS_DATA)

def read_data(size=1):
    return spi_rx.readbytes(size)

def write_data(data):
    spi_rx.writebytes(data)

def read_frame():
    while(read_has_data()==1):
        pass
    size_data=read_data(2)
    size = size_data[0]<<8 | size_data[1]
    print size,read_data(size)

def get_version():
    data=[12,0,0,0,0,0,0,0,22,0,1,0,27,0]
    write_data(data)

counter = 0

def comm_test():
    global counter
    print counter
    get_version()
    time.sleep(0.1)
    read_frame()
    counter+=1