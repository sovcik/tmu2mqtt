#!/bin/bash
#set -x
svcname="tmu2mqtt"
svcfld="tmu2mqtt"

echo "Installing ${svcname} service"

function check_installed {
    local status=$?
    if [ $status -ne 0 ]; then
        echo "error: not installed"
        exit 1
    fi
    echo "ok"
}

function check_running {
    local cnt=`ps aux | grep -c ${1}`
    # assuming running if at least two lines found in ps result
    if [ $cnt -gt 1 ]; then
        echo "ok"
        return 0
    fi
    echo "error: not running"
}

echo "Checking if python3 is installed"
sudo python3 --version > /dev/null
check_installed

echo "Checking if pip is installed"
sudo python3 -m pip --version > /dev/null
check_installed

echo "Installing required python packages"
sudo python3 -m pip install paho-mqtt pyserial

echo "Copying script to /opt/${svcfld} folder"
[ -d /opt/${svcfld} ] || sudo mkdir /opt/${svcfld}
sudo cp ./tmu2mqtt.py /opt/${svcfld}

if [ -f /etc/${svcname}.cfg ] 
then 
    echo "Configuration file already exists. Keeping existing configuration."
else
    echo "Config file does not exist"
    echo "Copying example configuration to /etc"
    sudo cp ./${svcname}.cfg.example /etc/${svcname}.cfg
fi

echo "Creating log file and configuring logrotate"
[ -f /var/log/${svcname}.log ] || sudo touch /var/log/${svcname}.log

if [ -f /etc/logrotate.d/${svcname} ] 
then 
    echo "Logrotate already configured. Keeping existing configuration."
else
    echo "Copying default logrotate configuration"
    sudo cp ./${svcname}.logrotate /etc/logrotate.d/${svcname}
    sudo systemctl restart logrotate
fi

echo "Creating service"
sudo cp ./${svcname}.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable ${svcname}.service

echo "Starting service"
sudo systemctl start ${svcname}.service

echo "*** Installation complete"
echo "Modify script configuration in /etc/${svcname}.cfg"
echo "Restart script service using: sudo systemctl restart ${svcname}"
echo "Check service status using: sudo systemctl status ${svcname}"