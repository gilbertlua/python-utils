#include "SpiWrapper.h"

int SpiOpen(uint8_t mode,const char* path,uint32_t speedHz, bool lsbFirst, uint8_t bitsPerWord)
{
	// printf("open : %s\n",path);
	int ret = -1;
	
	int fd = open(path, O_RDWR);
	if (fd < 0)
	{
		// Open failed
		// TODO: handle
        perror("Spi Open Fail:");
		return fd;
	}
    
    ret = ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speedHz);
	if (ret < 0)
	{
		// Set max speed failed
		// TODO: properly handle
		perror("Spi Set Speed Fail:");
		close(fd);
		return -1;
	}
	
	uint8_t modeFlags = 0;
	switch (mode)
	{
		case 0: modeFlags = SPI_MODE_0; break;
		case 1: modeFlags = SPI_MODE_1; break;
		case 2: modeFlags = SPI_MODE_2; break;
		case 3: modeFlags = SPI_MODE_3; break;
		default: modeFlags = SPI_MODE_0;
	}
	modeFlags |= (lsbFirst? SPI_LSB_FIRST: 0);
	
	ret = ioctl(fd, SPI_IOC_WR_MODE, &modeFlags);
	if (ret < 0)
	{
		// Set mode failed
		// TODO: properly handle
		perror("Set mode failed:");
		close(fd);
		return -1;
	}
	return fd;
}

bool SpiClose(int fd)
{
	close(fd);
    return true;
}

int spiTransfer(int fd,char* pBuf, size_t len)
{
	
	struct spi_ioc_transfer tr;
	memset(&tr, 0, sizeof(tr));
	tr.tx_buf = (uint64_t) pBuf;
	tr.rx_buf = (uint64_t) pBuf;
	tr.len = len;
	
	int ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
	if(ret<0)
    {
        perror("transfer fail:");
    }

	return ret;
}

int GpioInit(unsigned int pin)
{
	// Check if already exported
	char buf[48];
	snprintf(buf, sizeof(buf), "/sys/class/gpio/gpio%d", pin);
	if (access(buf, F_OK) != 0)
	{
		GpioExportPin(pin);
	}
	snprintf(buf, sizeof(buf), "/sys/class/gpio/gpio%d/value", pin);
	while (access(buf, W_OK) == -1);
	// TODO: need timeout while waiting
	
	int fd = open(buf, O_RDWR);
	lseek(fd, 0, SEEK_SET);

	return fd;
}

int GpioGetLastErrno()
{
	// currently unsupported
	return 0;
}

void GpioWrite(int fd,bool on)
{
	char buf[2];
	buf[0] = on ? '1' : '0';
	buf[1] = '\0';
	lseek(fd, 0, SEEK_SET);
	if (write(fd, buf, 1) != 1)
	{
		perror("write fail:");
		// m_LastErrno = errno;
		return;
	}

}
	
int GpioRead(int fd)
{
	char buf[2];
	lseek(fd, 0, SEEK_SET);
	if (read(fd, buf, sizeof(buf)) != sizeof(buf))
	{
		//m_LastErrno = errno;
		// perror("read fail:");
		return -1;
	}
	return (buf[0] != '0');
}

void GpioSetEdge(unsigned int pin,int edge)
{
	const char EDGE_NONE[] = "none";
	const char EDGE_FALLING[] = "falling";
	const char EDGE_RISING[] = "rising";
	const char EDGE_BOTH[] = "both";

	// if (m_Dir) return;
	
	char edgeStr[48];
	snprintf(edgeStr, sizeof(edgeStr), "/sys/class/gpio/gpio%d/edge", pin);
	
	int fd = open(edgeStr, O_WRONLY);
	if (fd < 0)
	{
		// m_LastErrno = errno;
		perror("open edge fail:");
		return;
	}

	switch (edge)
	{
	case 0:
		if (write(fd, EDGE_NONE, sizeof(EDGE_NONE)) != sizeof(EDGE_NONE))
		{
			// m_LastErrno = errno;
			perror("write edge none fail:");
			return;
		}
		break;
	
	case 1:
		if (write(fd, EDGE_FALLING, sizeof(EDGE_FALLING)) != sizeof(EDGE_FALLING))
		{
			// m_LastErrno = errno;
			perror("write edge fall fail:");
			return;
		}
		break;

	case 2:
		if (write(fd, EDGE_RISING, sizeof(EDGE_RISING)) != sizeof(EDGE_RISING))
		{
			// m_LastErrno = errno;
			perror("write edge rise fail:");
			return;
		}
		break;

	case 3:
		if (write(fd, EDGE_BOTH, sizeof(EDGE_BOTH)) != sizeof(EDGE_BOTH))
		{
			// m_LastErrno = errno;
			perror("write edge both fail:");
			return;
		}
		break;
	}
}

int GpioGetEdge(unsigned int pin)
{
	const char EDGE_NONE[] = "none";
	const char EDGE_FALLING[] = "falling";
	const char EDGE_RISING[] = "rising";
	const char EDGE_BOTH[] = "both";
	char edgeStr[48];
	snprintf(edgeStr, sizeof(edgeStr), "/sys/class/gpio/gpio%d/edge", pin);
	
	int fd = open(edgeStr, O_RDONLY);
	if (fd < 0)
	{
		// m_LastErrno = errno;
		return edgeError;
	}
	
	lseek(fd, 0, SEEK_SET);
	
	char buf[8];
	if (read(fd, buf, sizeof(buf)) < 0)
	{
		// m_LastErrno = errno;
		perror("get edge fail:");
		return edgeError;
	}
	
	if (memcmp(buf, EDGE_NONE, sizeof(EDGE_NONE)-1) == 0)
	{
		return edgeNone;
	}
	else if (memcmp(buf, EDGE_FALLING, sizeof(EDGE_FALLING)-1) == 0)
	{
		return edgeFalling;
	}
	else if (memcmp(buf, EDGE_RISING, sizeof(EDGE_RISING)-1) == 0)
	{
		return edgeRising;
	}
	else if (memcmp(buf, EDGE_BOTH, sizeof(EDGE_BOTH)-1) == 0)
	{
		return edgeBoth;
	}
	
	return edgeError;
}
	
void GpioSetDir(int fd,unsigned int pin,int dir)
{
	const char DIRECTION_IN[] = "in";
	const char DIRECTION_OUT[] = "out";

	if (dir && (GpioGetEdge(pin) != edgeNone))
	{
		GpioSetEdge(pin,edgeNone);
	}
	
	char directionStr[48];
	snprintf(directionStr, sizeof(directionStr),
		"/sys/class/gpio/gpio%d/direction", pin);
	
	int fd_local = open(directionStr, O_WRONLY);
	if (fd_local < 0)
	{
		perror("open dir fail:");
		return;
	}

	if (dir)
	{
		if (write(fd_local, DIRECTION_OUT, sizeof(DIRECTION_OUT))
			!= sizeof(DIRECTION_OUT))
		{
			perror("write dir 1 fail:");
			return;
		}
	}
	else
	{
		if (write(fd_local, DIRECTION_IN, sizeof(DIRECTION_IN))
			!= sizeof(DIRECTION_IN))
		{
			perror("write dir 0 fail:");
			return;
		}
	}

}
	
int GpioGetRealDir(unsigned int pin)
{
	const char DIRECTION_IN[] = "in";
	const char DIRECTION_OUT[] = "out";
	
	char directionStr[48];
	snprintf(directionStr, sizeof(directionStr),
		"/sys/class/gpio/gpio%d/direction", pin);
	
	int fd = open(directionStr, O_RDONLY);
	if (fd < 0)
	{
		perror("open real dir fail:");
		return -1;
	}
	
	lseek(fd, 0, SEEK_SET);
	
	char buf[8] = "";
	if (read(fd, buf, sizeof(buf)) < 0)
	{
		perror("read real dir fail:");
		return -1;
	}
	
	if (memcmp(buf, DIRECTION_IN, sizeof(DIRECTION_IN)-1) == 0)
	{
		return 0;
	}
	else if (memcmp(buf, DIRECTION_OUT, sizeof(DIRECTION_OUT)-1) == 0)
	{
		return 1;
	}
	
	return -1;
}

void GpioExportPin(unsigned int pin)
{
	int fd = open("/sys/class/gpio/export", O_WRONLY);
	if (fd < 0)
	{
		perror("open export pin fail:");
		return;
	}
	
	char pinStr[4];
	int pinStrLen = snprintf(pinStr, sizeof(pinStr), "%d", pin);
	if (write(fd, pinStr, pinStrLen) != pinStrLen)
	{
		perror("write export pin fail:");
		close(fd);
		return;
	}
	close(fd);
}

void GpioUnexportPin(unsigned int pin)
{
	int fd = open("/sys/class/gpio/unexport", O_WRONLY);
	if (fd < 0)
	{
		perror("open unexport pin fail:");
		return;
	}
	
	char pinStr[4];
	int pinStrLen = snprintf(pinStr, sizeof(pinStr), "%d", pin);
	if (write(fd, pinStr, pinStrLen) != pinStrLen)
	{
		perror("write unexport pin fail:");
		close(fd);
		return;
	}
	close(fd);
}

		
int GpioWaitForEdge(int fd,int timeoutMs)
{
	struct pollfd m_PollFd;
    m_PollFd.fd=fd;
    m_PollFd.events=POLLPRI;
	int ret = poll(&m_PollFd, 1, timeoutMs);
		
	if (ret < 0)
	{
		// perror("wait edge error:");
		return -1;
	}
	else if (ret == 0)
	{
		// printf("error=0\n");
		return -1;
	}
	else if (ret == 1)
	{
		// printf("success\n");
		return GpioRead(fd);
	}
    return 0;
}

