# fmlxcansocket build script
rm -rf libFMLX_SpiWrapper.so
gcc -Wall -fPIC -c SpiWrapper.c -o FMLX_SpiWrapper.o
gcc -Wall -shared -o libFMLX_SpiWrapper.so FMLX_SpiWrapper.o
sudo cp libFMLX_SpiWrapper.so /usr/lib
