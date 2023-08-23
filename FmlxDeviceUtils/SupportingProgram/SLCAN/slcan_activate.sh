#!/bin/bash
sudo modprobe slcan
sudo slcand -o -s8 -S 4000000 /dev/ttyAMA0
sudo ip link set up slcan0
sudo ip link set slcan0 txqueuelen 4096
