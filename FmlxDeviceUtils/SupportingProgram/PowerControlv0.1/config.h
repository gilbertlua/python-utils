#ifndef CONFIG_H_
#define CONFIG_H_
#include <stdint.h>

/************************************************************
 * Pin Mapping
 ************************************************************/
const int triggerPin = 4;
const int shutdownPin = 18;

/************************************************************
 * Shutdown Option
 ************************************************************/
const char shutdownCommand[] = "sudo shutdown -h now";
const uint64_t checkingPeriod = 300000; //microseconds

#endif
