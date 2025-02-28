import json
import random
import time
import subprocess
import shlex
import paho.mqtt.client as mqtt
import threading


## Read config from "/etc/inverter/mqtt.json"
config = open('/etc/inverter/mqtt.json','r')
conf = json.load(config)

pub_topic = conf['topic'] + "/sensor/" + conf['devicename'] + "_" + conf['serial']
sub_topic = pub_topic + "/COMMANDS"
client_id = "python-client.py"
POLLER_CMD = "/opt/inverter-cli/bin/inverter_poller -1"
WRITE_CMD = "/opt/inverter-cli/bin/inverter_poller -r"


## Read and Write to Voltronic via Serial Port or USB, check if resorce is busy with Lock() system
class Voltronic:
    AllowedCmd = ['POP00','POP01','POP02','PCP00','PCP01','PCP02','PCP03','MUCHGC010','MUCHGC020','MUCHGC030','MUCHGC040','MUCHGC050']    
    InvPoller = shlex.split(POLLER_CMD)
    
    def __init__(self) -> None:
      self.lock = threading.Lock()
    
    def read(self):
      self.lock.acquire()
      try:
          rdProcess = subprocess.run(Voltronic.InvPoller, 
                            check=True, 
                            shell=False, 
                            stdout=subprocess.PIPE, 
                            universal_newlines=True,
                            timeout=10)
          return rdProcess.stdout  
      except:
          print('Poller bin error')
          return "{}"
      finally:
          self.lock.release()

    
    def write(self, param):
        if param in Voltronic.AllowedCmd:
            wrCOMMAND = shlex.split(WRITE_CMD)
            wrCOMMAND.append(param)
            
            print("wrcommand -> " + str(wrCOMMAND))
            
            self.lock.acquire() 
            try:
                attemp = 0
                invResponse = '---'
                while invResponse != 'ACK' and attemp < 5:
                  attemp +=1 
                  print("Try WRITE to INVERTER n. ", attemp)
                   
                  wrProcess = subprocess.run(wrCOMMAND,
                                        stdout=subprocess.PIPE,
                                        check=True,
                                        shell=False,
                                        universal_newlines=True,
                                        timeout=10)
                  res = wrProcess.stdout.split()
                  invResponse = res[1]
                  
                  if invResponse == "ACK":
                    print("Write success!!")
                    t = time.localtime()
                    
                    ## formatto l'orario in ISO8601 (https://it.wikipedia.org/wiki/ISO_8601)
                    wrTime = time.strftime("%Y-%m-%dT%H:%M:%S%z", t)
                    c.publish(pub_topic+'/Last_write_success', wrTime)
                    c.publish(pub_topic+'/Last_write_command', param)
                  else:
                    print("Write Failed, retry in 2 sec.")
                  time.sleep(2)
            finally:
                self.lock.release()
        else:
            print(param," not allowed")
  

# The callback for when the client receives a CONNACK response from the server.
def mqtt_connect(client, userdata, flags, rc):
    print("MQTT connection result code: "+str(rc))
    print("Subribing to topic: " + sub_topic)
    client.subscribe(sub_topic)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed. 

# The callback for when a PUBLISH message is received from the server.
def mqtt_message(client, userdata, msg):
    print("Received message '" + str(msg.payload) + "' on topic '" + msg.topic + "' with QoS " + str(msg.qos))
    
    inverter.write(str(msg.payload.decode("utf-8")))


def mqtt_pubblish(client,userdata,mid):
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S %Z", t)
    print("data sent to MQTT",current_time)


if __name__ == '__main__':
    c = mqtt.Client(client_id)
    c.on_connect = mqtt_connect
    c.on_message = mqtt_message
    c.on_publish = mqtt_pubblish
    print("Pubblish to topic: " + pub_topic)
        
    c.username_pw_set(conf['username'], conf['password'])
    c.connect(conf['server'], 1883)
    time.sleep(1)
    c.loop_start()
    
    inverter = Voltronic()

    while True:
        # Reset variabili per calcolare grid_watts
        chargeCurrent = 0
        batteryVoltage = 0
        loadWatt = 0
        inverterMode = 0
        
        res_json = inverter.read()
        mqtt_data = json.loads(res_json)
        for key,value in mqtt_data.items():
            topic = pub_topic+'/'+key
            c.publish(topic, value)
            if key == 'Battery_charge_current':
                chargeCurrent = value
            if key == 'Battery_voltage':
                batteryVoltage = value
            if key == 'Load_watt':
                loadWatt = value
            if key == 'Inverter_mode':
                inverterMode = value
        
        if inverterMode == 3:
            topic = pub_topic + '/AC_grid_watt'
            value = (loadWatt + ( chargeCurrent * batteryVoltage )) / 0.93
            c.publish(topic, value)
        else:
            topic = pub_topic + '/AC_grid_watt'
            value = 0
            c.publish(topic, value)
            
        t = time.localtime()
        ## formatto l'orario in ISO8601 (https://it.wikipedia.org/wiki/ISO_8601)
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S%z", t)
        c.publish(pub_topic+'/Last_inverter_update',current_time)
        time.sleep(5)