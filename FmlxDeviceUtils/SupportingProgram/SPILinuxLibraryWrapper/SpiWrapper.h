#ifndef _SPIWRAPPER_
#define _SPIWRAPPER_

#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/poll.h>
#include <poll.h>

#include <sys/ioctl.h>
#include <linux/types.h>
#include <linux/spi/spidev.h>

enum Edge
{
    edgeError = -1,
    edgeNone = 0,
    edgeFalling,
    edgeRising,
    edgeBoth
};

// SPI function list
int SpiOpen(uint8_t mode, const char *path, uint32_t speedHz, bool lsbFirst, uint8_t bitsPerWord);
bool SpiClose(int fd);
int spiTransfer(int fd, char *pBuf, size_t len);

// GPIO and Interrupt function list
int GpioInit(unsigned int pin);
int GpioGetLastErrno();
void GpioWrite(int fd, bool on);
int GpioRead(int fd);
void GpioSetEdge(unsigned int pin, int edge);
int GpioGetEdge(unsigned int pin);
void GpioSetDir(int fd, unsigned int pin, int dir);
int GpioGetRealDir(unsigned int pin);
int GpioWaitForEdge(int fd,int timeoutMs);
void GpioExportPin(unsigned int pin);
void GpioUnexportPin(unsigned int pin);

#endif