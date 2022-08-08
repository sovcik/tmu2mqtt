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
At least one section `tmuN` shall be present, where N is number from 1 to 99.

Collected data will be published to mqtt broker topic `{mqtt.client_id}/{tmuNN.id}`

## Section \[mqtt\]
* **client_id** - required mqtt client id - has to be unique within mqtt broker. 
* **host** - optional mqtt host name or ip address. Default is `localhost`
* **port** - optional mqtt broker TCP port. Default is `1883`
* **username** - optional username. Default is none.
* **password** - optional password. Default is none.

## Section \[tmuNNN\]
* **port** - required serial port device name, e.g. /dev/ttyUSB0
* **id** - optional TMU device identifier. Default is section name.
* **qos** - optional mqtt QOS level for data from this port. Default is `1`.

## Example (minimum)
```
[mqtt]
client_id=tmu2mqtt

[tmu1]
id=nas_temp
port=/dev/ttyUSB0

[tmu2]
id=server_temp
port=/dev/ttyUSB1

```

# After installation
1. modify tmu2mqtt bridge configuration   
   `sudo nano /etc/tmu2mqtt.cfg`   
   > Do not forget to restart service daemon - see below
1. modify tmu2mqtt logrotate configuration  
   `sudo nano /etc/logrotate.d/tmu2mqtt`
1. modify service startup
   `sudo nano /etc/systemd/system/tmu2mqtt.service`


# Usage
1. check tmu2mqtt service status
   `sudo systemctl status tmu2mqtt`
1. restart tmu2mqtt service
   `sudo systemctl restart tmu2mqtt`
