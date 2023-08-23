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
#include <cstdlib>
#include "FMLX_CanSocket.hpp"
struct Can_Socket_Buffer {
    struct msghdr msg;
    struct iovec iov;
    char ctrlmsg[CMSG_SPACE(sizeof(struct timeval)) + CMSG_SPACE(sizeof(__u32))];
    struct can_frame frame;
};
struct Socket_Desc {
    char* ifName;
    sockaddr_can  addr;
    int sockfd;
    struct  Can_Socket_Buffer* pRx;
    struct  Can_Socket_Buffer* pTx;
};
int CreateSocket(Socket_Desc* pHandle);
void initMessageHeader(Socket_Desc* pHandle);
int SetAcceptanceFilter(Socket_Desc* pHandle, unsigned int can_id, unsigned int can_mask );
void  resetMessageHeader(Can_Socket_Buffer* buffer, sockaddr_can addr);
int Close(Socket_Desc* pHandle)
{
    ::close(pHandle->sockfd);
    return 0;
}
int SetAcceptanceFilter(Socket_Desc* pHandle, unsigned int can_id, unsigned int can_mask )
{
    int rc;
    struct can_filter filter[1];
    filter[0].can_id   = can_id;
    filter[0].can_mask = can_mask;
    rc = ::setsockopt(
             pHandle->sockfd,
             SOL_CAN_RAW,
             CAN_RAW_FILTER,
             &filter,
             sizeof(filter)
         );
    if (-1 == rc) {
        std::perror("setsockopt filter");
        Close(pHandle);
        return -2;
    }
    return 0;
}
struct  Socket_Desc* CreateHandle(int canChannel, ChannelType channelType)
{
    // std::cout<<"creating handle\n";
    struct  Socket_Desc* pHandle;
    pHandle = (struct Socket_Desc*)malloc (sizeof (struct Socket_Desc));
    pHandle->pRx = (struct Can_Socket_Buffer*) malloc (sizeof (struct Can_Socket_Buffer));
    pHandle->pTx = (struct Can_Socket_Buffer*) malloc (sizeof (struct Can_Socket_Buffer));
    pHandle->ifName = (char*)malloc (IFNAMSIZ * sizeof (char));
    char buffer [5];
    sprintf(buffer, "%d", canChannel);
    char ifname[16];
    switch(channelType)
    {
        case ctVcan:
        std::strncpy(ifname, "vcan\0", 5);
        break;

        case ctCan:
        std::strncpy(ifname, "can\0", 4);
        break;

        case ctSlcan:
        std::strncpy(ifname, "slcan\0", 6);
        break;
    }
    std::strncat(ifname, buffer, 5);
    std::strncat(ifname, "\0", 1);
    std::strncpy(pHandle->ifName, ifname, IFNAMSIZ);
    return pHandle;
}
void DeleteHandle(struct Socket_Desc* pHandle)
{
    free(pHandle->pTx);
    free(pHandle->pRx);
    free(pHandle->ifName);
    free(pHandle);
}
int Create(struct Socket_Desc* handle)
{
    initMessageHeader(handle);
    return CreateSocket(handle);
}
void BusOn(struct Socket_Desc* pHandle)
{}
void BusOff(struct Socket_Desc* pHandle)
{}
void FlushReceiveQueue(struct Socket_Desc* pHandle)
{}
void FlushTransmitQueue(struct Socket_Desc* pHandle)
{}
int CreateSocket(struct Socket_Desc* pHandle)
{
    int rc;
    struct sockaddr_can addr;
    struct ifreq ifr;
    // Open the CAN network interface
    // std::cout<<"ifName "<<pHandle->ifName;
    // std::cout<<"fd"<<pHandle->sockfd<<'\n';
    pHandle->sockfd = ::socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (-1 == pHandle->sockfd) {
        std::cout<<"socket error"<<'\n';
        perror("socket");
        return -1;
    }
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 10000;
    rc = setsockopt(pHandle->sockfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    if (-1 == rc) {
        std::cout<<"socket timeout"<<'\n';
        perror("setsockopt recivetimeout");
        Close(pHandle);
        return -3;
    }
    // Enable reception of CAN FD frames
    int enable = 0;
    rc = ::setsockopt(pHandle->sockfd, SOL_CAN_RAW, CAN_RAW_FD_FRAMES, &enable, sizeof(enable));
    if (-1 == rc) {
        std::cout<<"socket can fd error"<<'\n';
        perror("setsockopt CAN FD");
        Close(pHandle);
        return -3;
    }
    // Get the index of the network interface
    std::strncpy(ifr.ifr_name, pHandle->ifName, IFNAMSIZ);

    if (::ioctl(pHandle->sockfd, SIOCGIFINDEX, &ifr) == -1) {
	    std::cout<<"socket ioctl"<<'\n';
        perror("ioctl");
        Close(pHandle);
        return -4;
    }
    // Bind the socket to the network interface
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    rc = ::bind(
             pHandle->sockfd,
             reinterpret_cast<struct sockaddr*>(&addr),
             sizeof(addr)
         );
    if (-1 == rc) {
        std::cout<<"socket bind error"<<'\n';
        perror("bind");
        Close(pHandle);
        return -5;
    }
    pHandle->addr = addr;
    return 0;
}
void initMessageBuffer(Can_Socket_Buffer* pBuffer, can_frame* pFrame, sockaddr_can* pAddr)
{
    pBuffer->iov.iov_base = pFrame;
    pBuffer->msg.msg_name = pAddr;
    pBuffer->msg.msg_iov = &pBuffer->iov;
    pBuffer->msg.msg_iovlen = 1;
    pBuffer->msg.msg_control = &pBuffer->ctrlmsg;
}
void Write(struct Socket_Desc* pHandle, struct CanSocketFrame* pFrameIn)
{
    struct can_frame* pFrame = &pHandle->pTx->frame;
    memset(pFrame, 0, sizeof(*pFrame));
    pFrame->can_id = pFrameIn->messageId;
    for (int i = 0; i < pFrameIn->dlc; i++)
    {
        pFrame->data[i] = pFrameIn->canData[i];
    }
    pFrame->can_dlc = pFrameIn->dlc;
    resetMessageHeader(pHandle->pTx, pHandle->addr);
    struct ifreq ifr;
    std::strncpy(ifr.ifr_name, pHandle->ifName, IFNAMSIZ);
    ifr.ifr_ifindex = pHandle->addr.can_ifindex;
    if (ioctl(pHandle->sockfd, SIOCGIFMTU, &ifr) == -1) {
        perror("mtu error");
    }
    sendmsg(pHandle->sockfd, &pHandle->pTx->msg, MSG_DONTWAIT/*00*/);
    pFrameIn->status = 0;
}
void initMessageBuffer(Can_Socket_Buffer* pBuffer, sockaddr_can* pAddr)
{
    pBuffer->iov.iov_base = &pBuffer->frame;
    pBuffer->msg.msg_name = pAddr;
    pBuffer->msg.msg_iov = &pBuffer->iov;
    pBuffer->msg.msg_iovlen = 1;
    pBuffer->msg.msg_control = &pBuffer->ctrlmsg;
}
void initMessageHeader(Socket_Desc* pHandle)
{
    initMessageBuffer(pHandle->pTx, &pHandle->addr);
    initMessageBuffer(pHandle->pRx, &pHandle->addr);
}
void resetMessageHeader(Can_Socket_Buffer* pBuffer, sockaddr_can addr)
{
    pBuffer->iov.iov_len = sizeof(pBuffer->frame);
    pBuffer->msg.msg_namelen = sizeof(addr);
    pBuffer->msg.msg_controllen = sizeof(pBuffer->ctrlmsg);
    pBuffer->msg.msg_flags = 0;
}
void Read(struct Socket_Desc*  pHandle, struct CanSocketFrame* pFrameOut)
{
    struct Can_Socket_Buffer* pRx = pHandle->pRx;
    struct can_frame* frame = &pRx->frame;
    resetMessageHeader(pRx, pHandle->addr);
    int nbytes = recvmsg(pHandle->sockfd, &pRx->msg, MSG_WAITALL );
    pFrameOut->dlc = 0;
    pFrameOut->status = -1;
    if(nbytes >= 0)
    {
        pFrameOut->messageId = pRx->frame.can_id;
        pFrameOut->dlc = frame->can_dlc;
        for (int i = 0; i < pFrameOut->dlc; i++)
        {
            pFrameOut->canData[i] = pRx->frame.data[i];
        }
        pFrameOut->status = 0;
    }
}
void DeleteHandle(void* pHandle) {
    DeleteHandle((struct Socket_Desc*) pHandle);
}
void BusOn(void* pHandle) {
    BusOn((struct Socket_Desc*) pHandle);
}
void BusOff(void* pHandle) {
    BusOff((struct Socket_Desc*) pHandle);
}
void FlushReceiveQueue(void* pHandle) {
    FlushReceiveQueue((struct Socket_Desc*) pHandle);
}
void FlushTransmitQueue(void* pHandle) {
    FlushTransmitQueue((struct Socket_Desc*) pHandle);
}
int Create(void* pHandle) {
    // std::cout<<"creating socket\n";
    return Create((struct Socket_Desc*) pHandle);
}
int Close(void* pHandle) {
    return Close((struct Socket_Desc*) pHandle);
}
int SetAcceptanceFilter( void* pHandle, unsigned int can_id, unsigned int can_mask )
{
    return SetAcceptanceFilter((struct Socket_Desc*) pHandle, can_id, can_mask );
}
void print_bytes(const void* object, size_t size)
{
    const unsigned char* const bytes = (const unsigned char* const)object;
    size_t i;
    printf("[ ");
    for(i = 0; i < size; i++)
    {
        printf("%02x ", bytes[i]);
    }
    printf("]\n");
}
void Write(void* pHandle, struct  CanSocketFrame* pFrameIn) {
    Write((struct Socket_Desc*) pHandle, pFrameIn);
}
void Read(void* pHandle, struct CanSocketFrame* pFrameOut) {
    Read((struct Socket_Desc*) pHandle, pFrameOut);
}