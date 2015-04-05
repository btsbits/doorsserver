Please submit pull requests!
I want to make this as useful, secure, and reliable as possible.
Doors Server
============
A python program for Raspberry Pi and Piface Digital to monitor, log, and control home security controls.

# Introduction #
I started this project as a means of checking on the status of and controling my garage door while away from home.  I wanted to be able to ensure that I did not leave it open, and if so, i could close it, even while in another city, state or country.  As of this writing, It does that and more:

 - monitors all doors using "off the shelf" security alarm door sensors
 - sends notifications when selected doors are open beyond a configurable time
 - web interface displays easy to understand status of connected doors
 - toggle garage door opener from web interface
 - log all door activities to a file

# Requirements #

 - [Raspberry Pi](http://raspberrypi.org) SBC (i use model B, but anyone should work)
 - [Piface Digital](http://www.piface.org.uk/products/piface_digital/) and the python modules for it
 - SD card with Debian based OS for Raspberry Pi (I am using Raspbian, but might work with others.)
 - Internet connection to the RPi (a USB WiFi adapter will required on model 'A's but an Ethernet cable can be used for all 'B' models.  Other USB adapters for other types of connections may also be available)
 - at least one sensor/switch that can be wired to the Piface Digital
# Setup #
 - connect door sensor switches to the piface digital input terminals with pin 8 as a common connector for all switches.
 - connect the common and NO pins of piface digital a relay to the wires of the garage door opener button.
 - Install Raspbian OS to SDCard according to the distribution's instructions (if pre-installed, skip this step)
 - connect to the RPi using a USB keyboard and TV/Monitor 
or:
 - use ssh to connect to the RPi from another computer `ssh pi@<ip-address-of-RPi>` (default password is 'raspberry')
 - update system software: `sudo apt-get update && sudo apt-get upgrade`
 - *(There are some steps required to enable SPI for PIface Digital to work on newer versions of Raspbian. I will try to update when i remember what they are. If you find the instuctions somewhere, please let me know or submit a pull request.)*
 - Create a new folder `mkdir /home/pi/doorsserver/` and put doorsserver files in it.
 - Edit 'doors.json' and make sure that proper JSON is used or a fatal error will be generated. Do not remove any top level keys unless specified in the notes keys.
# Usage #

For testing/debugging
---------------------

You can simply run with Python 3 without any arguments:

   

    sudo python3 doorsserver065.py
and you will see the output on screen of door events and the https log.
This uses the defaults as shown in the output from `python3 doorsserver065.py -h
`

    usage: doorsserver065.py [-h] [-v] [-f CONFIGFILE] [-d] [-i] [-n] [-p PORT]
                             [-l LOGFILE]
    
    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         verbose logging/output
      -f CONFIGFILE, --configfile CONFIGFILE
                            specify a JSON formated file to retrive configuration
                            from. (default is: doors.json)
      -d, --daemon          direct errors and output to log files
      -i, --insecure        do not use ssl
      -n, --newtoken        generate a new token
      -p PORT, --port PORT  specify what port to listen on for http requests.
                            (default is: 8880
      -l LOGFILE, --logfile LOGFILE
                            specify the log path and file name prefix. (default
                            is: /var/log/doorsserver065.py)


As a daemon
-------
- edit /etc/rc.local `sudo nano /etc/rc.local`
- add a line similar to this at the end:

 `setsid python3 doorsserver065.py -div -l /var/log/doors65.insecure -p 8888 -f /home/pi/testing.doors.json >>/var/log/doorserver.insecure.rc.log 2>& 1 < /dev/null &`
    

To break that down:

 - `-div` enables 3 options:
	 - daemon: log everything instead of sending it as console output
	 - insecure: don't use https (ssl seems buggy right now, especially with ports that are forwarded on a home router.)
	 - verbose: gives more information, especially when initializing. This helps track problems and please use verbose since this is alpha software (under development and not ready for secure/production use)
 - `-l /var/log/doors65.insecure` log file will be:
	- /var/log/doors.65.insecure.err
	- /var/log/doors.65.insecure.log
	- /var/log/doors.65.insecure.server
	- /var/log/doors.65.insecure.states

 -  `-p 8888` override the default port for the web server and use 8888 instead
 - `-f /home/pi/testing.doors.json` use a different config file located at home/pi/testing.doors.json
 - `>>/var/log/doorserver.insecure.rc.log` if this initial command has any output (it shouldn't since -d was used) add it to the file /var/log/doorserver.insecure.rc.log
 - `2>& 1 < /dev/null &` ignore all stderr and stdin 

The last 2 points are import to ensure the program is run in the background and does not cause problems with anything else in the rc.local script.

Web Interface
-------

To use the web interface, you will need the token specified in the config file's "token" key, or from the console or .log file (must use -v option).  The url is https://ip.of.rpi/?t=tOkeNfrOmconIg or if -i option is used, omit the 's' from https://.  If the main status page works correctly, a cookie is set in the browser and the query portion of the url (part after and including the '?') can be omitted. This cookie is required for the javascript to update door status, trigger garage doors, view logs, and view/edit config (not fully implemented).

If a pin for a garage door is listed in 'garageclose' and a relay (0 or 1) is listed in 'garagerelay' in the config file, you can click on the garage icon to briefly trigger the relay to open or close the garage door.
