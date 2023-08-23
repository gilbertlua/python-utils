# Make file for Rpi Power Control

all : powerControlService.c shutdownViaRaspi.c config.h
	find . -type f | xargs touch
	gcc -o powerControlService powerControlService.c -l wiringPi
	gcc -o shutdownViaRaspi shutdownViaRaspi.c -l wiringPi

powerControlService : powerControlService.c config.h
	find . -type f | xargs touch
	gcc -o powerControlService powerControlService.c -l wiringPi

shutdownViaRaspi : shutdownViaRaspi.c config.h
	find . -type f | xargs touch
	gcc -o shutdownViaRaspi shutdownViaRaspi.c -l wiringPi

clean :
	find . -type f | xargs touch
	rm -f powerControlService *.o
	rm -f shutdownSystem *.o