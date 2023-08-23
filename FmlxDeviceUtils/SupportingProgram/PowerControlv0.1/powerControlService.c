#include <stdio.h>
#include <wiringPi.h>
#include <stdlib.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <unistd.h>
#include "config.h"
#include <string.h>

enum rpiState{
	stateWaitReady=0,
	stateStandby=1,
	stateShutdown=2,
}state;

void gpioInit(void)
{
	//setup the gpio library
	if(wiringPiSetupGpio() < 0)
	{
		printf("PowerControl Service error, unable to setup wiringPi\n");
		exit(0);
	}

	// pull the trigger pin low first
	digitalWrite(triggerPin,LOW);
	pinMode(triggerPin, OUTPUT);

	pinMode(shutdownPin, INPUT);
	pullUpDnControl(shutdownPin, PUD_UP); //LOW active
}

int main(int argc, char *argv[])
{
	char *strProcess[argc+1];
    if(argc>0)
    {
        for(int i = 0;i<(argc-1);i++)
        {
            strProcess[i] = argv[1+i];
			printf("process %s!\n",strProcess[i]);
        }
    }
    else
    {
        printf("no pid processed!\n");
    }
	state = stateWaitReady;
	gpioInit();
	printf("PowerControl Service starting \n");
	printf("Wait State\n");
	while(1){
		usleep(checkingPeriod);
		switch(state)
		{
			case stateWaitReady:
				if(digitalRead(shutdownPin))
				{
					printf("Standby State\n");
					digitalWrite(triggerPin,HIGH);
					state = stateStandby;
				}
				break;
				
			case stateStandby:
				if(!digitalRead(shutdownPin))
				{
					printf("shutdown pressed\n");
					if(argc>0)
					{
						printf("Turning off processes\n");	
						for(int i = 0;i<(argc-1);i++)
						{
							char char_command[80];
							memset(char_command,0,sizeof(char_command));
							strcat(char_command,"pkill -SIGINT ");
							strcat(char_command,strProcess[i]);
							system(char_command);
						}
						sleep(5);
					}
					state= stateShutdown;
				}
				break;
				
			case stateShutdown:
				printf("Preparing to Shutdown\n");
				digitalWrite(triggerPin,LOW);
				system(shutdownCommand);
				return 0;
		}
	}
		
}
