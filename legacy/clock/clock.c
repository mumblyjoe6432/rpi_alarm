####
#Created by:	Gabe Thompson
#Date:		April 13, 2012
####
#Description:
#This script controls an algorithm to simulate the sunrise by using PWM to control a GPIO to an LED
#Enter the number of steps (more for smaller changes in light intensity per step) and the number of
#seconds for each step, and the program will calculate the PWM % to increase the light intensity
#an equal amount for each step, and run through until it is at 100%.
####


#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <math.h>
#include "c_gpio.h"

#define DEFAULT_GPIO 4
#define DEFAULT_NUMSTEPS 15
#define DEFAULT_STEP_DURATION 60

typedef struct
{
    int numsteps;
    int gpio;
    int stepduration;
    int debug;
} alarmvars;

alarmvars ValidateInputParam(int argc, char* argv[]);

float logn(float value, float base);

main(int argc, char *argv[])
{
    alarmvars progvals;
    int i=1;
    int status = 0;

    progvals = ValidateInputParam(argc, argv);

    if (progvals.numsteps == -1)
        return;

    if (progvals.debug == 1)
        printf("Input parsed\n");

    // 1000 on this counter means 1s.
    time_t seconds_now, seconds_before;
    int cntr = 0;
    float pwm = 0;
    float offtime = 0;
    float ontime = 0;

    // Time (in seconds) before the next level of pwm is reached
    int pwm_steps = progvals.stepduration;
    if (progvals.debug)
        pwm_steps = 1;

    // The GPIO to control
    const int GPIO_NUM = progvals.gpio;

    cleanup();
    status = setup();
    if (status == 1)
    {
        printf("Failed to setup DEVMEM.  You probably don't have access to the hardware.\n");
        return;
    }
    if (progvals.debug)
        printf("Post-GPIO setup status = %i\n\n", status);
    setup_gpio(GPIO_NUM, OUTPUT, PUD_OFF);

    i=progvals.numsteps;
    while(i > 0)
    {
        pwm = logn(i,progvals.numsteps+1)*100;
        if (progvals.debug == 1)
            printf("PWM=%f\n",pwm);
        offtime = (float)pwm*100;
        ontime = (100-(float)pwm)*100;

        seconds_before = time(NULL);
        seconds_now = time(NULL);
        while(seconds_now < seconds_before + pwm_steps)
        {
            seconds_now = time(NULL);
            output_gpio(GPIO_NUM, LOW);
            usleep(offtime);
            output_gpio(GPIO_NUM, HIGH);
            usleep(ontime);
        }
        i--;
    }
    output_gpio(GPIO_NUM, HIGH);
    cleanup();
    if (progvals.debug == 1)
        printf("***Program Finished***\n\n");
}

alarmvars ValidateInputParam(int argc, char* argv[])
{
    int help = 0;
    int arg = 1;
    int status=0;

    alarmvars output;
    output.numsteps = DEFAULT_NUMSTEPS;
    output.gpio = DEFAULT_GPIO;
    output.stepduration = DEFAULT_STEP_DURATION;
    output.debug = 0;

    if (argc == 0)
        return output;

    for ( arg = 1; arg < argc; arg++ )
    {
        if ( (argv[arg][0] == '-') || (argv[arg][0] == '/') )
        {
            switch( toupper( argv[arg][1] ) )
            {
                case 'S':  //Total light steps
                    output.numsteps = atoi(argv[arg+1]);
                    if (output.debug == 1)
                        printf("Number of Steps  = %i\n", output.numsteps);
                    arg++;
                break;

                case 'G':  //GPIO to use
                    output.gpio = atoi(argv[arg+1]);
                    if (output.debug == 1)
                        printf("GPIO = %i\n", output.gpio);
                    arg++;
                break;

                case 'D':  //debug mode
                    output.debug = 1;
                    printf("\n***DEBUG MODE***\n");
                    printf("\n");
                break;

                case 'L':  //Time length of each light step in seconds
                    output.stepduration = atoi(argv[arg+1]);
                    if (output.debug == 1)
                        printf("Step Duration = %i\n", output.stepduration);
                    arg++;

                case 'H':  //print help menu
                    help = 1;
                break;

                default:
                    printf("Input %s not understood.  Please use format below.\n\n", argv[arg]);
                    help = 1;
                break;
            }
        }
    }

    if (help == 1)
    {
        printf("Alarm Help Menu\n");
        printf("\n");
        printf("Option        Description\n");
        printf("-s <steps>    Total number of steps for the light ramp-up\n");
        printf("-t <time>     Duration time in seconds for each step\n");
        printf("-g <gpio>     The GPIO number attached to the lights\n");
        printf("-d            Will print debug messages\n");
        printf("-h            Prints this help menu\n");
        printf("\n");

        output.numsteps = -1;
        output.gpio = -1;
        output.stepduration = -1;
    }

    return output;
}

float logn( float value, float base)
{
    return log(value)/log(base);
}
