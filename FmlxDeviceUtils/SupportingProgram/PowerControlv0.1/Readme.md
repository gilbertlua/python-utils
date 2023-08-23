# Power Control Service

Power Control Service is example code on Raspberry Pi to guide us to implement the safe shutdown program

How to use it :

1. Clone or download this repo
1. on the terminal, type **make** to build the code
1. make the powerControlService executeable by typing **chmod +x powerControlService**
1. go to **/etc** and edit **rc.local** file by typing **sudo nano rc.local** , and add 
**sudo /POWERCONTROL_SERVICE_PATH/powerControlService &**
1. After this, the safe shutdown program will be executed at startup
1. To shutdown the system from raspi, run shutdownViaRaspi