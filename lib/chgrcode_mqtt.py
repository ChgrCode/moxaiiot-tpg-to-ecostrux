#!/usr/bin/env python3
'''
App MQTT Template 

MQTT wrapper class implementations  
'''

'''
Change log
1.0.0 - 2020-03-01 - cg
    Initial version
'''
__author__ = "chgrCode"
__license__ = "MIT"
__version__ = '1.0.0'
__maintainer__ = "chgrCode"
__credits__ = ["..."]
__status__ = "beta"


import json
import time
import re
import ssl
import paho.mqtt.client as mqtt_client

from collections import deque

from chgrcodebase import *

class AppMqttClient(AppBase):
    
    def __init__(self, id, **kwargs):
        AppBase.__init__(self, id, **kwargs)  
        self._ext_conf = kwargs.get('conf', None)
        self._ds_handle = None

        self._broker_host = None
        self._broker_port = 1883
        self._broker_keepalive = 60
        self._broker_username = None
        self._broker_password = None
        self._broker_enable_tls = False
        self._broker_insecure_tls = True
        
        self._client_bindaddr = '' 
        self._client_id = self.get_base_id()
        self._clean_session = True
        self._userdata = None
        self._protocol = 'MQTTv311'
        self._transport = 'tcp'   
        self._connect_attempts = 0
        self.is_connected = False
        self._continue_on_conn_error = False
        
        self._mqtt_default_topic = '/default'        
        
        self._mqtt_msg_tracking = None
        return
 
    def parse_configuration(self):
        if not self._ext_conf:
            self.log_error('Empty configuration!')
            return False          
       
        if 'broker_host' in self._ext_conf:
            self._broker_host = self._ext_conf['broker_host'] 
        if 'broker_port' in self._ext_conf:
            self._broker_port = int(str(self._ext_conf['broker_port']))
        if 'keepalive' in self._ext_conf:
            self._broker_keepalive = int(self._ext_conf['keepalive'])            
        if 'client_id' in self._ext_conf:
            self._client_id = self._ext_conf['client_id']
        if 'clean_session' in self._ext_conf:
            self._clean_session = self._ext_conf['clean_session']
        if 'enable_tls' in self._ext_conf:
            self._broker_enable_tls = self._ext_conf['enable_tls']
        if 'insecure_tls' in self._ext_conf:
            self._broker_insecure_tls = self._ext_conf['insecure_tls']
        if 'user_name' in self._ext_conf:
            self._broker_username = self._ext_conf['user_name'] 
        if 'password' in self._ext_conf:
            self._broker_password = self._ext_conf['password']             
        if 'default_topic' in self._ext_conf:
            self._mqtt_default_topic = self._ext_conf['default_topic']      

        return True 
 
    def init(self):

        # Initialize Connection 
        self.log_info('Create MQTT Client %s, clean session = %s', self._client_id, self._clean_session)
        self._ds_handle = mqtt_client.Client(client_id=self._client_id, 
                                             clean_session=self._clean_session)
        self.is_connected = False

        self.log_debug('Register Callback functions')
        self._ds_handle.on_connect = self.on_connect_callback
        self._ds_handle.on_disconnect = self.on_disconnect_callback
        self._ds_handle.on_publish = self.on_publish
        self._ds_handle.on_log = self.on_log

        if self._broker_username:
            self.log_debug('Set User Name and Password')
            self._ds_handle.username_pw_set(username= self._broker_username,
                                            password= self._broker_password )

        if self._broker_enable_tls:
            self.log_info('Enable TLS, insecure_tls=%s', self._broker_insecure_tls)
            self._ds_handle.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=None,  tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
            self._ds_handle.tls_insecure_set(self._broker_insecure_tls)
        
        return True
    
    def open(self):
        self.log_debug('Open(%d) Connect to Mqtt broker %s port %d, keepalive=%d, on %s', self._connect_attempts, 
                       self._broker_host,  self._broker_port, self._broker_keepalive, self._client_bindaddr)
        try:            
            if self._connect_attempts <= 0:
                self._ds_handle.connect(self._broker_host, 
                                        port=self._broker_port, 
                                        keepalive=self._broker_keepalive, 
                                        bind_address=self._client_bindaddr)  
            else:
                self._ds_handle.reconnect()
                
            self._connect_attempts += 1 
            
            retry = 0
            wait_timeout = 5
            self.log_info('Waiting max %s seconds for connection!', wait_timeout)
            while self.is_connected == False:                
                if retry > wait_timeout:
                    break
                self._ds_handle.loop(timeout=1.0, max_packets=1) 
                retry += 1                    
        
        except Exception as e:
            if not self._continue_on_conn_error:
                self.log_exception('Connecting Broker!')
                self.set_error_str(AppErrorCode.EXCEPTION.value, str(e))
            else:
                self.log_error('%s', str(e)) 
            self.is_connected = False                   
        finally:
            pass        
        if self.get_error():
            return False
        else:
            return True
    
    def is_open(self):
        if self._ds_handle and self.is_connected == True:
            return True
        else:
            return False
    
    def close(self):
        self.log_debug('Close()! Disconnect from Mqtt host')
        if self._ds_handle == None:
            return True
        try:
            self._ds_handle.disconnect(reasoncode=None, properties=None)          
        except Exception as e:
            self.log_exception('Closing Connection to Broker!')
            self.set_error_str(AppErrorCode.EXCEPTION.value, str(e))
        finally:
            pass            
        if self.get_error():
            return False
        else:
            return True
    
    def publish(self, data, topic=None, net_loop=True):        
        if topic is None:
            topic = self._mqtt_default_topic       

        pInfo = self._ds_handle.publish(topic, data)  
        self.log_debug('Puplish topic %s: %s', topic, pInfo) 
        if pInfo.rc != mqtt_client.MQTT_ERR_SUCCESS:
            self.log_error('Msg not published, reason %s', pInfo) 
        if net_loop:                                           
            self._ds_handle.loop(timeout=1.0, max_packets=1)
        return pInfo  
    
    def publish_json(self, data, topic=None, net_loop=True):
        data = json.dumps(data)
        return self.publish(data, topic, net_loop)
    
    def on_connect_callback(self, client, userdata, flags, rc):   
        self.log_info('OnConnect! rc=%s flags=%s', rc, flags)     
        if rc == 0:           
            self.is_connected = True
            self.log_info("Connected successfully to broker: %s", self._broker_host)
            return
        elif rc == 1:
            self.log_warning("Connection refused - incorrect protocol version")
               
        elif rc == 2:
            self.log_warning("Connection refused - invalid client identifier")
                 
        elif rc == 3:
            self.log_warning("Connection refused - server unavailable")
                 
        elif rc == 4:
             self.log_warning("Connection refused - bad username or password")
             
        else:
             self.log_warning("Connection refused - not authorised") 
             
        self.is_connected = False
        return
                      
    def on_disconnect_callback(self, client, userdata, rc):
        self.log_info('OnDisonnect! rc = %s', rc)
        self.is_connected = False
        if rc:
            self.log_error('Disonnected with result code = %s', rc)  
        return

    def on_log(self, client, userdata, level, buf):
        self.log_debug("OnLog(%s): %s ", level, buf)
        return

    def on_publish(self, client, userdata, mid):
        self.log_info('OnPublish MsgID [%s]', mid)

        return    

            