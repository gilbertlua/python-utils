

#ifndef _SYSFS_GPIO_H__
#define _SYSFS_GPIO_H__

#include <sys/poll.h>
#include <cstdint>
#include <vector>
#include <functional>
// #include <atomic>
// #include <thread>
// #include <mutex>

class CSysfsGpio
{
public:
	enum Edge
	{
		edgeError = -1,
		edgeNone = 0,
		edgeFalling,
		edgeRising,
		edgeBoth
	};
	
	typedef std::function<void(int)> TCallback;
	
public:

	CSysfsGpio(unsigned int pin);
	virtual ~CSysfsGpio();
	
	void Write(bool on);
	bool Read();
	void SetDir(int dir);
	int GetDir();
	
	int WaitForEdge(Edge edge, int timeoutMs=-1);
	// void StartWatcher(Edge edge, const TCallback& cb);
	// void StopWatcher();
	// void AddTogglePin(CSysfsGpio *gpioToggle);

	int GetLastErrno();

	void setEdge(Edge edge);
	Edge getEdge();
	Edge getRealEdge();
	
private:
	void exportPin();
	void unexportPin();

	int getRealDir();
	
	void watcherThread();

private:
	static const char EDGE_NONE[];
	static const char EDGE_FALLING[];
	static const char EDGE_RISING[];
	static const char EDGE_BOTH[];
	static const char DIRECTION_IN[];
	static const char DIRECTION_OUT[];
	
	const unsigned int m_Pin;
	// CSysfsGpio *m_pToggle;
	int m_ValueFd;
	pollfd m_PollFd;
	int m_Dir;
	Edge m_Edge;
	
	// std::thread m_WatcherThread;
	// std::atomic<bool> m_IsWatcherRunning;
	// std::mutex m_WatcherMutex;
	// TCallback m_EdgeCallback;
	
	int m_LastErrno;
};

#endif // _SYSFS_GPIO_H__
