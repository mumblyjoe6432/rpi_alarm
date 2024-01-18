rpi_alarm
=========

Raspberry Pi Alarm Script with sunrise lights

Before running, you must run the command pigpiod

This does actually work at reboot with cron, however, the line must look like this:
@reboot sleep 30 && export PULSE_SERVER="unix:/run/user/$(id -u)/pulse/native" && python /path/to/smartbed.py 2>/path/to/stderr.log

Actually, you may be able to omit the export command, it probably works fine without the sleep. If that doesn't work, the export command may need to be modified for your specific system.
