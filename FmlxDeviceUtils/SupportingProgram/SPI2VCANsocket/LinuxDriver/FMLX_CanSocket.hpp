#include <linux/can.h>
#include <linux/can/raw.h>
#include <endian.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include <iomanip>
#include <iostream>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstring>
#ifndef FMLX_CANSOCKET_HEADER
#define FMLX_CANSOCKET_HEADER
struct CanSocketFrame
{
    int32_t flag;
    int32_t messageId;
    int32_t status;
    int32_t dlc;
    int64_t time;
    __u8 canData[8];
};

enum ChannelType
{
    ctVcan = 0,
    ctCan = 1,
    ctSlcan = 2
};

extern "C" struct Socket_Desc *CreateHandle(int canChannel, ChannelType channelType);
extern "C" void DeleteHandle(void *pHandle);
extern "C" void BusOn(void *pHandle);
extern "C" void BusOff(void *pHandle);
extern "C" void FlushReceiveQueue(void *pHandle);
extern "C" void FlushTransmitQueue(void *pHandle);
extern "C" int Create(void *pHandle);
extern "C" int Close(void *pHandle);
extern "C" int SetAcceptanceFilter(void *pHandle, unsigned int can_id, unsigned int can_mask);
extern "C" void Write(void *pHandle, struct CanSocketFrame *pFrameIn);
extern "C" void Read(void *pHandle, struct CanSocketFrame *pFrameOut);
#endif