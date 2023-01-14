#!/bin/bash

MQTT_SERVER=`cat /etc/inverter/mqtt.json | jq '.server' -r`
MQTT_PORT=`cat /etc/inverter/mqtt.json | jq '.port' -r`
MQTT_TOPIC=`cat /etc/inverter/mqtt.json | jq '.topic' -r`
MQTT_DEVICENAME=`cat /etc/inverter/mqtt.json | jq '.devicename' -r`
MQTT_SERIAL=`cat /etc/inverter/mqtt.json | jq '.serial' -r`
MQTT_USERNAME=`cat /etc/inverter/mqtt.json | jq '.username' -r`
MQTT_PASSWORD=`cat /etc/inverter/mqtt.json | jq '.password' -r`
LOCK_FILE=`cat /etc/inverter/mqtt.json | jq '.lockfile' -r`

function subscribe () {
    mosquitto_sub -h $MQTT_SERVER -p $MQTT_PORT -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -i ""$MQTT_DEVICENAME"_"$MQTT_SERIAL"" -t "$MQTT_TOPIC/sensor/""$MQTT_DEVICENAME"_"$MQTT_SERIAL""/COMMANDS" -q 1
}

function reply () {
    mosquitto_pub -h $MQTT_SERVER -p $MQTT_PORT -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" -i ""$MQTT_DEVICENAME"_"$MQTT_SERIAL"" -t "$MQTT_TOPIC/sensor/""$MQTT_DEVICENAME"_"$MQTT_SERIAL""/COMMANDS" -q 1 -m "$*"
}

subscribe | while read rawcmd; do

  echo "[$(date +%F+%T)] try send incoming request: [$rawcmd] to inverter."
  for attempt in $(seq 3); do
    while [ ! -f "$LOCK_FILE" ]
    do
      echo "--| try write to inverter [$(date +%F+%T)] $rawcmd"
      echo "$(date +%s) $0" > $LOCK_FILE
      REPLY=$(/opt/inverter-cli/bin/inverter_poller -r $rawcmd)
      rm $LOCK_FILE
      break
    done    
    echo "[$(date +%F+%T)] $REPLY"
    reply "[$rawcmd] [Attempt $attempt] [$REPLY]"
	  [ "$REPLY" = "Reply:  ACK" ] && break
	  [ "$attempt" != "3" ] && sleep 3
  done
done