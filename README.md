# TMU to MQTT
TMU USB thermometer (www.papouch.com) to MQTT bridge

# Prerequisites
1. logrotate daemon is installed
1. systemd daemon is installed
1. python >= 3.7 is installed
1. python module manager `pip` is installed

# Installation
Run `sudo bash ./install.sh`   
Script will
1. check prerequisites   
1. install tmu2mqtt to /opt/tmu2mqtt folder   
1. install default configuration
1. install tmu2mqtt service and logrotate configuration
1. start tmu2mqtt service

# Configuration
Configuration is by default read from file `/etc/tmu2mqtt.cfg`
File has ini-style structure. 
Required section is `mqtt` containing configuration needed for MQTT client.
At least one section `tmuN` shall be present, where N is number from 1 to 9.

## Example
```
[mqtt]
id=tmu2mqtt

[tmu2]
id=tmu2
port=/dev/ttyUSB0

```

# After installation
1. modify tmu2mqtt bridge configuration   
   `sudo nano /etc/tmu2mqtt.cfg`   
   > Do not forget to restart service daemon - see below
1. modify tmu2mqtt logrotate configuration  
   `sudo nano /etc/logrotate.d/tmu2mqtt`


# Usage
1. check tmu2mqtt service status
   `sudo systemctl status tmu2mqtt`
1. restart tmu2mqtt service
   `sudo systemctl restart tmu2mqtt`
