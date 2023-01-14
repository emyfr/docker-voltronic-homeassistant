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


port = 1883
sub_topic = "homeassistant/sensor/Voltronic_92932105101927/COMMANDS"
pub_topic = "python"
client_id = "python-client.py"


InvPoller = shlex.split("/opt/inverter-cli/bin/inverter_poller -1")
InvRawCmd = shlex.split("/opt/inverter-cli/bin/inverter_poller -r")



## Read and Write to Voltronic via Serial Port or USB, check if resorce is busy with Lock() system
class Voltronic:
    def __init__(self) -> None:       
      self.AllowedCmd = ['POP00']
      self.lock = threading.Lock()
      
    
    def read(self):
      self.lock.acquire()
      try:
          process = subprocess.run(InvPoller, 
                            check=True, 
                            shell=False, 
                            stdout=subprocess.PIPE, 
                            universal_newlines=True, 
                            timeout=10)
          return process.stdout
  
      except TimeoutExpired:
          print('Poller bin Timeout')
          return "{}"
      finally:
          self.lock.release()

    
    def write(self, param):
        self.lock.acquire()
        try:
            process = subprocess.run(InvRawCmd)
        finally:
            self.lock.release()
  

# The callback for when the client receives a CONNACK response from the server.
def mqtt_connect(client, userdata, flags, rc):
    print("MQTT connection result code: "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed. 

# The callback for when a PUBLISH message is received from the server.
def mqtt_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


def mqtt_pubblish(client,userdata,mid):
    print('ho appena pubblicato: ',mid)


if __name__ == '__main__':
    c = mqtt.Client(client_id)
    c.on_connect = mqtt_connect
    c.on_message = mqtt_message
    c.on_publish = mqtt_pubblish
    c.username_pw_set(conf['username'], conf['password'])
    c.connect(conf['server'], port)
    time.sleep(1)
    c.loop_start()
    
    inverter = Voltronic()

    while True:        
        res_json = inverter.read()
        mqtt_data = json.loads(res_json)
        for key,value in mqtt_data.items():
            topic = pub_topic+'/'+key
            c.publish(topic, value)
        time.sleep(5)
