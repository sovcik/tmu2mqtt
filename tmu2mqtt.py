#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial  # from pySerial
import threading
import paho.mqtt.client as mqtt
import time
import logging
import sys
import getopt
import configparser
import signal
from typing import List
from dataclasses import dataclass

runScript = True


@dataclass
class MqttConfig:
    host: str
    username: str
    password: str
    clientId: str
    keepAlive: int
    port: int
    qos: int


@dataclass
class TMUConfig:
    id: str
    port: str


class Config:
    # client, user and device details
    def __init__(self, argv):
        self.mqtt: MqttConfig = MqttConfig()
        self.logfile: str = "./tmu2mqtt.log"
        self.logLevel = logging.INFO
        self.configFile: str = './tmu2mqtt.cfg'

        self.tmus: List[TMUConfig] = []

        self.parse_args(argv)

        if len(self.configFile) > 0:
            self.read_config(self.configFile)

    def help(self):
        print('Usage: '+sys.argv[0] +
              ' -c <configfile> -v <verbose level> -l <logfile>')
        print()
        print('  -c | --config: ini-style configuration file, default is '+self.configFile)
        print('  -v | --verbose: 1-fatal, 2-error, 3-warning, 4-info, 5-debug')
        print('  -l | --logfile: log file name,default is '+self.logfile)
        print()
        print('Example: '+sys.argv[0] +
              ' -c /etc/tmu2mqtt.cfg -v 2 -l /var/log/tmu2mqtt.log')

    def parse_args(self, argv):
        try:
            opts, args = getopt.getopt(
                argv, "hc:v:l:", ["config=", "verbose=", "logfile="])
        except getopt.GetoptError:
            print("Command line argument error")
            self.help()
            sys.exit(2)

        for opt, arg in opts:
            if opt == '-h':
                self.help()
                sys.exit()
            elif opt in ("-c", "--config"):
                self.configFile = arg
            elif opt in ("-v", "--verbose"):
                if arg == "1":
                    self.logLevel = logging.FATAL
                if arg == "2":
                    self.logLevel = logging.ERROR
                if arg == "3":
                    self.logLevel = logging.WARNING
                if arg == "4":
                    self.logLevel = logging.INFO
                if arg == "5":
                    self.logLevel = logging.DEBUG
            elif opt in ("-l", "--logfile"):
                self.logfile = arg

    def read_config(self, cf):
        print('Using configuration file ', cf)
        config = configparser.ConfigParser()
        config.read(cf)

        try:
            seccfg = config['mqtt']
        except KeyError:
            print('Error: configuration file is not correct or missing')
            exit(1)

        self.mqtt.host: str = seccfg.get('host', 'localhost')
        self.mqtt.username: str = seccfg.get('username')
        self.mqtt.password: str = seccfg.get('password')
        self.mqtt.clientId: str = seccfg.get('id', 'tmu2mqtt')
        self.mqtt.qos: int = seccfg.getint('qos', 1)
        self.mqtt.keepAlive: int = seccfg.getint('keepalive', 60)
        self.mqtt.port: int = seccfg.getint('port', 1883)

        for section in config.sections():
            if section.startswith('tmu'):
                port = config.get(section, 'port')
                id = config.get(section, 'id', fallback=section)
                self.tmus.append({port: port, id: id})


@dataclass
class TmuSensor:
    port: serial.Serial
    id: str
    buffer: bytearray


class TMU2MQTT(threading.Thread):
    def __init__(self, mqttClient: mqtt.Client):
        threading.Thread.__init__(self)
        self.running: bool = True
        self.tmuPorts: List[TmuSensor] = []
        self.log = logging.getLogger("tmu2mqtt")

        self.mqtt = mqttClient
        self.mqtt.on_message = self._on_message
        self.mqtt.on_publish = self._on_publish
        self.mqtt.on_connect = self._on_mqtt_connect
        self.mqtt_reconnect = 0

    def stop(self):
        self.log.info("Stopping tmu2mqtt service")
        self.running = False

    def run(self):
        print("Starting " + self.name)
        self.log.info("*** tmu2mqtt bridge starting")
        self.log.info("Starting MQTT client")
        self.mqtt.loop_start()

        print("Starting processing loop")
        while self.running:
            if self.mqtt_reconnect > 0:
                self.log.warning("MQTT Reconnecting...")
                self.mqtt.reconnect()
            else:
                self.readTmuPorts()
                self.processTmuPorts()

    def addPort(self, id, port):
        self.log.info("Adding serial port id=%s at serial port=%s", id, port)
        sensor = TmuSensor(port, id)
        self.tmuPorts.append(sensor)

    # read all ports and store data in buffer
    def readTmuPorts(self):
        for port in self.tmuPorts:
            data = port.port.read()
            if data != b'':
                self.log.debug("received id=%s data=%s",
                               port.id, data.decode('ASCII'))
                port.buffer.join(data)

    # process buffers of TMU ports
    def processTmuPorts(self):
        for port in self.tmuPorts:
            idx = port.buffer.find(b'\x0D')
            # if x0D found
            if idx != -1:
                self.processTmuData(port.id, port.buffer[:idx].decode('ASCII'))
                port.buffer = port.buffer[idx+1:]

    def processTmuData(self, id: str, data: str):
        self.log.debug("processing TMU data id=%s data=%s", id, data)
        if data[0] != "*" and len(data) < 11:
            self.log.warning("Invalid data received: %s", data)
            return
        temp = data[1:10]
        self.log.info("Temperature id=%s temp=%s", id, temp)
        self.publish(id, temp)

    def _on_publish(self, client, userdata, mid):
        return
        # self.receivedMessages.append(mid)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self.mqtt_connected = rc
        self.mqtt_reconnect = 0
        if rc != 0:
            self.log.error("MQTT connection returned result=%s", rc)
            self.mqtt_reconnect += 1
            if self.mqtt_reconnect > 12:
                self.mqtt_reconnect = 12
            self.mqtt_reconnect_delay = 2**self.mqtt_reconnect
        else:
            self.log.info("Connected to MQTT broker.")

    def on_mqtt_disconnect(self, client, userdata, rc):
        self.mqtt_reconnect = 1
        if rc != 0:
            self.log.error("MQTT unexpected disconnection.")
            self.mqtt_reconnect = True
            self.mqtt_reconnect_delay = 10

    # publish a message
    def publish(self, topic: str, message, qos=1, retain=False):
        self.log.debug("Publishing topic=%s/%s msg=%s",
                       self.mqtt._client_id, topic, message)
        mid = self.mqtt.publish(self.mqtt._client_id+"/"+topic,
                                message, qos, retain)[1]


def stop_script_handler(msg: str, logger: logging.Logger):
    logger.info(msg)
    global runScript
    runScript = False

# -------------------------------------------------------


# parse commandline aruments and read config file if specified
cfg = Config(sys.argv[1:])

# configure logging
logging.basicConfig(filename=cfg.logfile, level=cfg.logLevel,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# create logger
log = logging.getLogger('main')

# add console to logger output
log.addHandler(logging.StreamHandler())

if len(cfg.tmus) == 0:
    log.fatal("No configuration for TMU devices found.")
    sys.exit("No configuration for TMU devices found.")

# handle gracefull end in case of service stop
signal.signal(signal.SIGTERM, lambda signo,
              frame: stop_script_handler("Signal SIGTERM received", log))

# handles gracefull end in case of closing a terminal window
signal.signal(signal.SIGHUP, lambda signo,
              frame: stop_script_handler("Signal SIGHUP received", log))

# connect to MQTT broker
log.info("Creating MQTT client for host=%s id=%s",
         cfg.mqtt.host, cfg.mqtt.clientId)
mqtt = mqtt.Client(cfg.mqtt.clientId)
mqtt.username_pw_set(cfg.mqtt.username, cfg.mqtt.password)
mqtt.connect_async(cfg.mqtt.host, cfg.mqtt.port, cfg.mqtt.keepalive)

log.info("Creating tmu2mqtt bridge")
bridge = TMU2MQTT(mqtt)

log.info("Opening serial ports for TMU sensors")
for tmu in cfg.tmus:
    try:
        # open serial port in non-blocking mode
        ser = serial.Serial(tmu.port, timeout=0)
        if ser.closed:
            log.fatal("Unable to open serial port %s", cfg.serialPort)
            sys.exit("Unable to open serial port")
        bridge.addPort(tmu.id, ser)
    except:
        log.error("Error opening serial port of TMU id=%s port=%s ",
                  tmu.id, tmu.port)
        sys.exit("Error opening serial port %s", tmu.port)


# start bridge
bridge.start()

try:
    while runScript:
        time.sleep(1)

except KeyboardInterrupt:
    log.info("Signal SIGINT received.")

# perform some cleanup
log.info("Stopping tmu2mqtt bridge")
bridge.stop()
ser.close()
log.info('tmu2mqtt stopped.')
