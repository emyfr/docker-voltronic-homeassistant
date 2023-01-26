#!/bin/bash

UNBUFFER='stdbuf -i0 -oL -eL'

# stty -F /dev/ttyUSB0 2400 raw

# Init the mqtt server.  This creates the config topics in the MQTT server
# that the MQTT integration uses to create entities in HA.

# broker using persistence (default HA config)
$UNBUFFER /opt/inverter-mqtt/mqtt-init.sh

python3 /opt/inverter-py/main.py