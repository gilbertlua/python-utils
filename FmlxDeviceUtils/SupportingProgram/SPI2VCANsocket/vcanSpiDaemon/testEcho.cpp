#include "CanSocket.h"
#include "SpidevSpi.h"
#include "SysfsGpio.h"
#include <sys/types.h>
#include <stdio.h>
#include <thread> // std::thread
#include <chrono>
#include <ctime>
#include <time.h>
#include <cstring>
#include <signal.h>
#include <unistd.h>

#define SPI_FRAME_SIZE 12

// Get current date/time, format is YYYY-MM-DD.HH:mm:ss
inline const std::string currentDateTime()
{
    char buf[40];
    timespec tS;
    clock_gettime(CLOCK_REALTIME, &tS);
    sprintf(buf, "%lu.%lu", tS.tv_sec, tS.tv_nsec);
    return buf;
}

inline void PrintCanFrame(CCanSocket::CanSocketFrame frame)
{
    std::cout << "received id : " << frame.messageId << ' ';
    std::cout << "dlc : " << frame.dlc << " data : ";
    for (uint8_t i = 0; i < 8; i++)
        std::cout << static_cast<uint16_t>(frame.canData[i]) << ' ';
    std::cout << '\n';
}

inline void PrintSpiFrame(char *data, uint16_t size)
{
    for (uint8_t i = 0; i < size; i++)
    {
        printf("%d ", *(data + i));
    }
    std::cout << '\n';
}

int main(int argc, char *argv[])
{
    bool isRunning = true;
    bool isDataReceived = false;
    CCanSocket canSocket(CCanSocket::ctVcan, 0);

    auto rxLambda = [](CCanSocket *pCanSocket, bool *state, bool *isDataReceived) {
        CCanSocket::CanSocketFrame frame;
        char compareData[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        uint64_t i = 0;
        while (1)
        {
            pCanSocket->Read(&frame);
            if (frame.status != 0)
                continue;

            if (frame.messageId != 1410 || frame.dlc != 8)
            {
                PrintCanFrame(frame);
                std::cout << "fail! Wrong msgId / wrong dlc\n";
                *state = false;

                return;
            }
            if (memcmp(frame.canData, compareData, 8) != 0)
            {
                PrintSpiFrame(compareData, 8);
                PrintCanFrame(frame);
                std::cout << "fail! Wrong Data\n";
                *state = false;
                return;
            }
            i++;
            *(uint64_t *)compareData = i;
            *isDataReceived = true;
        }
    };

    std::thread receiveThread(rxLambda, &canSocket, &isRunning, &isDataReceived);
    std::this_thread::sleep_for(std::chrono::milliseconds(10)); // let it print first

    CCanSocket::CanSocketFrame frame;
    uint64_t i = 0;
    char compareData[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    frame.messageId = 1418;
    frame.dlc = 8;

    while (!isDataReceived)
        ;

    while (isRunning)
    {
        memcpy(frame.canData, compareData, 8);
        std::cout << frame.messageId << ' ' << frame.dlc << ' ';
        for (uint8_t i = 0; i < 8; i++)
            std::cout << static_cast<uint16_t>(frame.canData[i]) << ' ';
        std::cout << '\n';
        canSocket.Write(frame);
        i++;
        *(uint64_t *)compareData = i;
        std::this_thread::sleep_for(std::chrono::microseconds(200));
    }
    char clearData[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    memcpy(frame.canData, clearData, 8);
    canSocket.Write(frame);
    return -1;
}
