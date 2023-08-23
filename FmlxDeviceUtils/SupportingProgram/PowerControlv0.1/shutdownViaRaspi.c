#include <stdio.h>
#include <wiringPi.h>
#include <stdlib.h>
#include "config.h"

int main(void)
{
    if(wiringPiSetupGpio() < 0)
	{
		printf("Cannot command system to shutdown, unable to setup wiringPi\n");
		exit(0);
    }
    
    //power controller service already set the triggerPin direction
    digitalWrite(triggerPin, LOW);
    
    printf("Preparing to Shutdown\n");
    system(shutdownCommand);

    return 0;
}