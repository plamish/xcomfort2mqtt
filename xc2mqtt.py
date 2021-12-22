"""
xComfort SHC  to MQTT broker.
https://github.com/plamish/xcomfort2mqtt


Example configuration:

    xcMQTT:
      class: xcMQTT
      module: xc2mqtt
      cameras:
        - url: "http://10.0.0.20"
          username: username
          password: password
          debug: True
          retian: True
          polling: 5
    
    url, username, password are mandatory       
    debug: optional, enables debug message in MQTT and appdaemon log
    retain: optional, sets retian flag for all MQTT messages
    polling: optional, timeout for long pull. 5 seconds works well 

      
App sends states from xComfort SHC under following topics:
    /xcomfort/parent_UID/device_UID if device has parrent
    /xomfort/device_UID if device is parent

Parent device  stores RSSI and battery status

"""
import appdaemon.plugins.hass.hassapi as hass
#import socket
import time
import threading
from threading import Thread
import requests
import json


class xcMQTT(hass.Hass):
    session_ID = ''
    proc = None
    kill_thread = False
    debug = False
    retain = False
    polling = 5

    
    
    def initialize(self):
        self.log("initialize()")        
        
        self.username = self.args["username"]
        self.password = self.args["password"]
        self.url = self.args["url"]
            
        try:
            self.debug = self.args["debug"]
            self.polling = int(self.args["polling"])
            self.retain = self.args["retain"]
        except:
            pass

       
        if self.debug:
             self.log("debug on")
        
        self.connect()
        self.poll_id = self.query("RE/subscribe",["*", ""])
        
        if self.debug:
            self.log("poll_id=%s", self.poll_id)
            
        self.proc = Thread(target=self.thread_process)
        self.proc.daemon = False
        self.proc.start()
        
        
    def connect(self):
        headers = {'User-Agent': 'Mozilla/5.0'}
        session = requests.Session()
        try:
            session.get(self.url)
        except Exception as err:
            self.log("ERROR1")
            exit(1)
        response = session.post(self.url, headers=headers, auth=(self.username, self.password))
        
        if response.status_code != 200:
            if response.status_code == 401:
                self.log('Invalid username/password\nAborting...')
                exit(1)
            else:
                self.log('Server responded with status code %s', str(response.status_code))
                exit(1)
        else:
            self.session_ID = requests.utils.dict_from_cookiejar(session.cookies)['JSESSIONID']


    def query(self,method, params=['', '']):
        json_url = self.url + '/remote/json-rpc'
        data = {
            "jsonrpc": "2.0",
            'method': method,
            'params': params,
            'id': 1
        }
        headers = {
            'Cookie': 'JSESSIONID=' + self.session_ID,
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
        }
    
        response = requests.post(json_url, data=json.dumps(data), headers=headers).json()

        if 'result' not in response:
            response['result'] = [{}] 
        return response['result']	    

    def terminate(self):
        self.kill_thread = True
        


    def thread_process(self):
        while not self.kill_thread:
            fun1 = self.query("RE/longPoll", [self.poll_id, self.polling])

            if fun1 != []:
               
                if self.debug:
                    _debug = json.dumps(fun1[0])
                    self.call_service("mqtt/publish", topic="xcomfort/debug", payload=_debug)
                try:
                    _parent = fun1[0]['properties']['parent.UID'].replace("hdm:xComfort Adapter:","")
                except:
                    _parent = ''
                
                try:
                    _debug = json.dumps(fun1[0]['properties'])
                    _uid = fun1[0]['properties']['UID'].replace("hdm:xComfort Adapter:","")
                    _name = fun1[0]['properties']['name']
                    _device_classes =fun1[0]['properties']['device.classes'][0].replace("com.eaton.xcomfort.hdm.dc.","") #SHC often reports multiple values. This broker takes the first one
                    _event = fun1[0]['properties']['event.device.class'][0].replace("com.eaton.xcomfort.hdm.dc.","") #SHC often reports multiple values. This broker takes the first on
                    _property_name= fun1[0]['properties']['event.device.class.object.property.name']
                    _value = fun1[0]['properties']['event.device.class.object.property.value']
                    
                    if (_parent != ''):
                        _topic = 'xcomfort/'+_parent+'/'+_uid+'/'
                    else:
                        _topic = 'xcomfort/'+_uid+'/'
                    
                    if (_property_name != 'isValueChanged'):
                        self.call_service("mqtt/publish", topic=_topic+_property_name, payload=_value,retain=self.retain)
                        
                        self.call_service("mqtt/publish", topic=_topic+'device_classes', payload=_device_classes,retain=self.retain)
                        
                        self.call_service("mqtt/publish", topic=_topic+'name', payload=_name, retain=self.retain)
                        
                        self.call_service("mqtt/publish", topic=_topic+'events/'+_event+'/value', payload=_value,retain=self.retain)
                    
                    
                    
                    if self.debug:
                        for e1 in fun1[0]['properties']['event.device.class']:
                            _event1 = e1.replace("com.eaton.xcomfort.hdm.dc.","")
                            
                            self.call_service("mqtt/publish", topic=_topic+'events/'+_event1+'/debug', payload=_debug,retain=self.retain)
                        
                            _topic_debug = 'xcomfort/events/'+_event1+'/'+_property_name
                            self.call_service("mqtt/publish", topic=_topic_debug, payload=_value,retain=self.retain)
                        
                    
                except:
                    if self.debug:
                        self.log('Issue parsing event =%s',fun1)

  
                
        result = self.query("RE/unsubscribe",[self.poll_id])    
        self.log("Thread exited")


"""
'event.device.class = 
com.eaton.xcomfort.hdm.dc.ActuatorMainsPowered,
com.eaton.xcomfort.hdm.dc.DimActuator,
com.eaton.xcomfort.hdm.dc.HeatingTemperatureActuator,
com.eaton.xcomfort.hdm.dc.TemperatureSensor

"""
