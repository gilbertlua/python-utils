#include "CanSocket.h"
#include "SpidevSpi.h"
#include "SysfsGpio.h"
#include <sys/types.h>
#include <stdio.h>
#include <thread> // std::thread
#include <chrono>
#include <cstring>
#include <signal.h>
#include <unistd.h>


#define VERSION "0.0.1"
#define SPI_FRAME_SIZE 12
#define POWER_MANAGEMENT_ADDRESS_TX 0x577
#define POWER_MANAGEMENT_ADDRESS_RX 0x578

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
        std::cout << frame.canData[i] << ' ';
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
    uint32_t spiSpeed = 16000000;
    if (argc > 1)
    {
        std::string str = argv[1];
        try
        {
            spiSpeed = std::stoul(str);
        }
        catch (...)
        {
            std::cout << "invalid argument, set to 16MHz speed\n";
        }
    }
    // initialization -------------------------------------------------------------------------
    std::cout << "FMLX SPI2VCAN Daemon Init Ver : " << VERSION << '\n';
    std::cout << "SPI FREQ = " << spiSpeed << "\n";

    CCanSocket canSocket(CCanSocket::ctVcan, 0);
    CSpidevSpi spiTx("/dev/spidev0.0", spiSpeed);
    CSpidevSpi spiRx("/dev/spidev0.1", spiSpeed);
    spiRx.Open(0, false, 8);
    spiTx.Open(0, false, 8);
    CSysfsGpio gpio(1);
    gpio.SetDir(0);
    gpio.setEdge(CSysfsGpio::edgeFalling);
    // -----------------------------------------------------------------------------------------

    // receive thread --------------------------------------------------------------------------
    auto rxLambda = [](CSpidevSpi *pRxSpi, CSysfsGpio *pGpio, CCanSocket *pCanSocket) {
        std::cout << "receive thread id : " << (long int)syscall(224) << '\n';
        char dataRx[SPI_FRAME_SIZE];
        CCanSocket::CanSocketFrame frame;
        bool isValid = true;
        while (1)
        {
            // wait for has data notification
            if (pGpio->WaitForEdge(CSysfsGpio::edgeFalling, 1))
                continue;
            // set to detect rising edge    
            // pGpio->setEdge(CSysfsGpio::edgeRising);
            memset(dataRx, 0, SPI_FRAME_SIZE);
            pRxSpi->Transfer(dataRx, SPI_FRAME_SIZE);
        
            // check whether the 12 byte data is succesfully send by checking the rising edge of has data pin 
            // if(!pGpio->Read())
            //     return;
            
            switch (dataRx[0])
            {
            // if it's can frame data
            case 't':
                frame.messageId = *(uint16_t *)&dataRx[1]; // 2 bytes
                std::cout << "id:" << frame.messageId << "\n";
                if (dataRx[3] <= 8)
                {
                    frame.dlc = dataRx[3];
                    memcpy(frame.canData, &dataRx[4], frame.dlc);
                    isValid = true;
                }
                else
                {
                    isValid = false;
                }
                break;

            // if it's configuration data
            case 'p':
            case 'F': // status flag
            case 'V': // version
            case 'N': // serial number
                frame.messageId = POWER_MANAGEMENT_ADDRESS_RX;
                frame.dlc = 8;
                memcpy(frame.canData, &dataRx[1], frame.dlc);
                isValid = true;
                break;
            default:
                std::cout << "warning, header not recognized : \n";
                PrintSpiFrame(dataRx, SPI_FRAME_SIZE);
                break;
            }

            if (isValid)
                pCanSocket->Write(frame);
            else
            {
                std::cout << "warning, frame not recognized : \n";
                PrintSpiFrame(dataRx, SPI_FRAME_SIZE);
            }
            isValid = false;
        }
    };
    std::thread spiReceiveThread(rxLambda, &spiRx, &gpio, &canSocket);
    std::this_thread::sleep_for(std::chrono::milliseconds(10)); // let it print first
    // -----------------------------------------------------------------------------------------

    // transmit thread for spi2can --------------------------------------------------------------------------
    std::cout << "transmit thread id : " << ::getpid() << '\n';
    char dataTx[SPI_FRAME_SIZE];
    while (1)
    {
        CCanSocket::CanSocketFrame frame;
        canSocket.Read(&frame);
        if (frame.status == 0)
        {
            // std::cout << frame.messageId << ' ' << frame.dlc << ' ';
            // for (uint8_t i = 0; i < 8; i++)
            //     std::cout << static_cast<uint16_t>(frame.canData[i]) << ' ';
            // std::cout << '\n';
            dataTx[0] = 't';
            *(uint16_t *)&dataTx[1] = frame.messageId; // 2 bytes
            if (frame.dlc > 8)
                frame.dlc = 8;
            dataTx[3] = frame.dlc;
            memcpy(&dataTx[4], frame.canData, dataTx[3]);
            spiTx.Transfer(dataTx, SPI_FRAME_SIZE);

            // if it's also for other config configuration
            if (frame.messageId == POWER_MANAGEMENT_ADDRESS_TX)
            {
                dataTx[0] = frame.canData[0];
                switch (frame.canData[0])
                {
                case 'p': // power management status request
                case 'O': // open CAN Channel
                case 'C': // close CAN channel
                case 's': // NACK
                case 'F': // status flag
                case 'V': // version
                case 'N': // serial number
                    break;

                case 'M': // set CAN acceptance mask
                case 'm': // set CAN acceptance id
                    *(uint32_t *)&dataTx[1] = *(uint32_t *)&frame.canData[1];
                    break;

                case 'S': // setup CAN bit rates
                    dataTx[1] = frame.canData[1];
                    break;
                }
                spiTx.Transfer(dataTx, SPI_FRAME_SIZE);
            }
        }
    }
    // -----------------------------------------------------------------------------------------

    // should never get here
    return 0;
}