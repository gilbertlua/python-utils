# daemon build script
g++ -pthread  vcanSpiDaemon/main.cpp vcanSpiDaemon/CanSocket.cpp vcanSpiDaemon/SysfsGpio.cpp vcanSpiDaemon/SpidevSpi.cpp  -o fmlxspi2vcan.out
g++ -pthread  vcanSpiDaemon/testEcho.cpp vcanSpiDaemon/CanSocket.cpp vcanSpiDaemon/SysfsGpio.cpp vcanSpiDaemon/SpidevSpi.cpp  -o testEcho.out
#g++ -pthread  vcanSpiDaemon/testReceive.cpp vcanSpiDaemon/CanSocket.cpp vcanSpiDaemon/SysfsGpio.cpp vcanSpiDaemon/SpidevSpi.cpp  -o testReceive.out
# fmlxcansocket build script
g++ -Wall -fPIC -c LinuxDriver/FMLX_CanSocket.cpp -o LinuxDriver/FMLX_CanSocket.o
g++ -Wall -shared -o LinuxDriver/libFMLX_CanSocket.so LinuxDriver/FMLX_CanSocket.o
sudo cp LinuxDriver/libFMLX_CanSocket.so /usr/lib
