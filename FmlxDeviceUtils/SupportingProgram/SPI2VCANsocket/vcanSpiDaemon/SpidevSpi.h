#ifndef SPIDEV_SPI_H__
#define SPIDEV_SPI_H__

#include <string>
#include <mutex>

class CSpidevSpi
{
public:
	CSpidevSpi(const char* path, uint32_t speedHz);
	virtual ~CSpidevSpi();
	
	bool Open(uint8_t mode, bool lsbFirst, uint8_t bitsPerWord);
	bool Close();
	int Transfer(char* pBuf, size_t len) const;
	
private:
	const std::string m_Path;
	const uint32_t m_SpeedHz;
	
	int m_Fd;

	static std::mutex mtx;
};

#endif // SPIDEV_SPI_H__
