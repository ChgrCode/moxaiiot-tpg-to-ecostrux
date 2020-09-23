#! /usr/bin/python3
'''
Subscribe for Tags on ThingsPro Gateway and publish to Mqtt Client

'''

'''
Change log
0.3.0 - 2020-09-07 - cg
    Add TPG Web UI config options
    Default Python 3 (TPG default now)
    
Change log
0.2.0 - 2020-08-07 - cg
    Initial version
'''

__author__ = "Christian G."
__license__ = "MIT"
__version__ = '0.3.1'
__status__ = "beta"

import sys, time
import requests
import json
import ssl
import sh
import paho.mqtt.client as mqtt_client

from collections import deque

from lib.chgrcodebase import *
from lib.chgrcode_mqtt import AppMqttClient

from libmxidaf_py import TagV2, Tag, Time, Value


class TpgAppContext(AppContext):
    
    def __init__(self, args, **kwargs):
        AppContext.__init__(self, args, **kwargs)
        if isinstance(self._console_args.resource_name, str):
            self._tpg_resource_name = self._console_args.resource_name.strip()
        else:
            self._tpg_resource_name = None
            
        if self._console_args.vtag_buffer is not None:
            self._vtag_data_buffer = self._console_args.vtag_buffer
        else:
            self._vtag_data_buffer = 100
            
        if self._config_file is None:
             self._config_file = 'config.json'
             
        self._ext_conf = {} 
        self._tagV2_obj = None 
        self._vtag_tags = 0   
        self._vtag_template_name = None
        self._vtag_subscribe = {}
        self._publish_interval = 5.0
        self._publish_format = 'charlie'
        self._publish_last_only = True
        self._publish_system_status = False
        self.asset_name = None
        
        self._mqtt_client = None
        
        self._vtag_data = deque(maxlen=kwargs.get('max_data_size', self._vtag_data_buffer))
        self._vtag_data_lastmatch = None        
        
        return
       
    def convert_tpg_ui_config(self):
        self.log_debug('conver_tpg_ui_config')
        if not self._ext_conf:
            self.log_error('External configuration missing!')
            return False
        
        if 'mqtt' not in self._ext_conf:
            self._ext_conf['mqtt'] = {}
        
        if 'clientid' in self._ext_conf: 
            self._ext_conf['mqtt']['client_id'] = self._ext_conf['clientid']
            
        if 'username' in self._ext_conf: 
            self._ext_conf['mqtt']['user_name'] = self._ext_conf['username']
            
        if 'password' in self._ext_conf: 
            self._ext_conf['mqtt']['password'] = self._ext_conf['password']
            
        if 'enabletls' in self._ext_conf: 
            self._ext_conf['mqtt']['enable_tls'] = self._ext_conf['enabletls']
            
        if 'keepalive' in self._ext_conf: 
            self._ext_conf['mqtt']['keepalive'] = self._ext_conf['keepalive']
            
        if 'cleansession' in self._ext_conf: 
            self._ext_conf['mqtt']['clean_session'] = self._ext_conf['cleansession']
           
        if 'broker' in self._ext_conf: 
            self._ext_conf['mqtt']['broker_url'] = self._ext_conf['broker'] 
            
        if 'sendsystemstatus' in self._ext_conf: 
            self._publish_system_status = self._ext_conf['sendsystemstatus'] 
            
        self._ext_conf['mqtt']['default_topic'] = "devices/{}/messages/events/".format(self._ext_conf['mqtt']['client_id'])
        
        return True
       
    def init_context(self):
        self.log_info('Init Context! ...')
        
        self._ext_conf = AppContext.import_file(self._config_file, 'json', def_path='/data')
        
        if not self.convert_tpg_ui_config():
            return False        
        
        if not self._ext_conf or 'mqtt' not in self._ext_conf:
            self.log_error('Missing MQTT configuration!')
            return False
        
        if 'tpg_vtag_template' in self._ext_conf:
            self._vtag_template_name = self._ext_conf['tpg_vtag_template']
        
        if 'vtag_tags' in self._ext_conf:
            if isinstance(self._ext_conf['vtag_tags'], dict):
                self._vtag_subscribe = self._ext_conf['vtag_tags']
            else:
                self.log_error('Wrong vtag_tags format in config file!')
            
        if 'devicetags' in self._ext_conf:
            devicetags = self._ext_conf['devicetags']
            if isinstance(devicetags, list):
                for tags in devicetags:
                    if not isinstance(tags, dict):
                        continue
                    if 'equipmentName' in tags:
                        if 'name' in tags:
                            if tags['equipmentName'] not in self._vtag_subscribe:
                                self._vtag_subscribe[tags['equipmentName']] = list()
                            self._vtag_subscribe[tags['equipmentName']].append(tags['name'])
                    else:
                        self.log_error('Wrong devicetags Tag definition in config file. Missing equipmentName')
                        return False
            else:
                self.log_error('Wrong devicetags format in config file!')
                return False
                        
        
        if 'publish_interval' in self._ext_conf:
            self._publish_interval = float(self._ext_conf['publish_interval'])            
        if self._console_args.publish_interval is not None:
            self._publish_interval =  self._console_args.publish_interval  
            self.log_info('Publish interval set to %s, from console arg!', self._publish_interval) 
            
        if 'assetname' in self._ext_conf:
            self.asset_name = self._ext_conf['assetname']    
            
        if 'publish_format' in self._ext_conf:
            self._publish_format = self._ext_conf['publish_format']
            
        if 'publish_last_only' in self._ext_conf:
            self._publish_last_only = self._ext_conf['publish_last_only']
                            
        if 'publish_system_tags' in self._ext_conf: 
            self._publish_system_status = self._ext_conf['publish_system_tags'] 
            
        if self._publish_system_status is True:
            if 'SYSTEM' not in self._vtag_subscribe:
                self._vtag_subscribe['SYSTEM'] = list()
            self._vtag_subscribe['SYSTEM'].append('cpu_usage')
            self._vtag_subscribe['SYSTEM'].append('memory_usage')
            self._vtag_subscribe['SYSTEM'].append('disk_usage')   
                               
        if len(self._vtag_subscribe) == 0: 
            if self._vtag_template_name is None or self._vtag_template_name == "":
                self.log_error('Missing VTag template name!')
                return False
            
            mx_api_token = self.tpg_get_mx_api_token()
            tpgVtags = self.tpg_get_vtag_info(mx_api_token)
            subVtags = None
            for equipment in tpgVtags:
                if equipment['equipmentName'] == self._vtag_template_name:
                    subVtags = equipment
                    break
            
            if subVtags is None or not isinstance(subVtags, dict) \
                or 'equipmentTags' not in subVtags \
                or len(subVtags['equipmentTags']) <= 0:
                self.log_error('No Virutal Tags configured for [%s]', self._vtag_template_name)
                return False
            
            for tag in subVtags['equipmentTags']:
                if self._vtag_template_name not in self._vtag_subscribe:
                    self._vtag_subscribe[self._vtag_template_name] = list()
                self._vtag_subscribe[self._vtag_template_name].append(tag['name'])
                 
        
        self._tagV2_obj = TagV2.instance()
        self._tagV2_obj.subscribe_callback(self.tpg_callback)
               
               
        self._mqtt_client = AppMqttClient('mqttClient', conf=self._ext_conf['mqtt'], logger=self.get_logger())
        if not self._mqtt_client.parse_configuration():
            return False
        
        if not self._mqtt_client.init():
            return False
        
        if not self._mqtt_client.open():
            self.log_warning('MQTT connection not esteblished, will try later!')
                           
        return True

    def run_context(self):
        self.log_info('Run Context! ...')         
        
        if isinstance(self._vtag_subscribe, dict):
            for equ, tags in self._vtag_subscribe.items():    
                for tag in tags:
                    self.log_info('TPG Subscribe for %s - %s', equ, tag)        
                    self._tagV2_obj.subscribe(equ, tag)
        else:
            self.log_error('Wrong vtag subscribe format!')        
        
        self.log_info('Publish TPG tags every %s seconds', self._publish_interval)
        self._run = True

        t = AppTimer()
        sleep_time = self._publish_interval
        loop_counter = 0
        
        while self._run == True:
            loop_counter = loop_counter + 1
            t.start()
            if not self._mqtt_client.is_open():
                self.tpg_set_controller_status(False) 
                self._mqtt_client.open()
                
            if not self._mqtt_client.is_open():
                self.tpg_set_controller_status(False) 
                t.stop()
                self.log_warning('Loop %d, Not connected with broker! retry in %d seconds', loop_counter, self._publish_interval)
                time.sleep(self._publish_interval)
                continue
            else:
                self.tpg_set_controller_status(True)  
                
            self.log_info('Loop %d, %d Tags in Queue, total recived %d', loop_counter, len(self._vtag_data), self._vtag_tags)
            
            if self._publish_format != 'charlie':
                self.log_warning('Wrong publish format!')
            
            while len(self._vtag_data)>0:
                msg = self.build_mqtt_msg_charlie()
                self.log_debug('Publish [%s]', msg )
                self._mqtt_client.publish_json(msg, None) 
                
            t.stop()
            sleep_time = self._publish_interval - t.get_elapsed()/1000                        
            if sleep_time < 0: 
                sleep_time = 0.0  
            self.log_debug('Waiting %s seconds till next interval!', sleep_time)              
            time.sleep(sleep_time)                      
    
        return True

    def build_mqtt_msg_charlie(self):      
        payload = {
            "metrics": {
                "assetName": self.asset_name
                }
            }      
        if isinstance(self._vtag_data_lastmatch, dict):
            tag = self._vtag_data_lastmatch
            self._vtag_data_lastmatch = None
            payload['metrics'][tag['name']] = tag['value']
            payload['metrics'][tag['name'] + "_timestamp"] = tag['timestamp']                        
            
        while len(self._vtag_data)>0:
            tag = self._vtag_data.popleft() 
            if self._publish_last_only is False and tag['name'] in payload['metrics']:
                self.log_debug('Key %s alredy in payload, skipp remaining %s', tag['name'], len(self._vtag_data))
                self._vtag_data_lastmatch = tag
                return payload 
            payload['metrics'][tag['name']] = tag['value']
            payload['metrics'][tag['name'] + "_timestamp"] = tag['timestamp']
        
        return payload 

    def convert_value(self, tag):
        # ToDo
        if tag.value().is_uint():
            return tag.value().as_uint()
        elif tag.value().is_int():
            return tag.value().as_int()
        elif tag.value().is_float():
            return tag.value().as_float()
        elif tag.value().is_string():
            return tag.value().as_string()
        elif tag.value().is_bytearray():
            return tag.value().as_bytearray()
        else:
            pass           
        return str(tag.value())

    def tpg_callback(self, source_name, tag_name, Tag):
        self.log_debug('%s (%s) - Tag: %s! Value: %s, Unit: %s', source_name, str(Tag.at()), tag_name, Tag.value(), Tag.unit())
        self._vtag_tags += 1
        timestamp=int(time.time()*1000)
        value = self.convert_value(Tag)
        self._vtag_data.append({'name': tag_name, 'value': value, 'timestamp': timestamp})
        return

    def do_exit(self, reason):
        self._run = False
        if self._mqtt_client and self._mqtt_client.is_open():
            self._mqtt_client.close()
            
        self.tpg_set_controller_status(False)
        return True
 
    def tpg_get_vtag_info(self, mx_api_token):
        rest_header = {
            "mx-api-token": mx_api_token,
            "Content-Type": "application/json"
        }         
        self.log_info('Querry current configured equipment!') 
        r = requests.get(
                'https://localhost/api/v1/mxc/custom/equipments',
                headers=rest_header,
                verify=False)
        if r.status_code == 200:
            data = r.json()
            self.log_info('Query Equipments successfull')
        else:
            self.log_error('Host URL with error! http status code %s', r.status_code)
            return None  
        return data   
    
    def tpg_get_mx_api_token(self):
        return AppContext.import_file('/etc/mx-api-token', 'text')     

    def tpg_set_controller_status(self, status):
        if self._tpg_resource_name is None:
            return
        try:
            data = {
                "code": 200,
                "method": "put",
                "resource": self._tpg_resource_name,
                "data": {
                    "status": str(status)
                }
            }       
            sh.mosquitto_pub("-t", "/controller", "-m", json.dumps(data,indent=2)) 
        except Exception as e:
            self.log_error("Exception while updating controller status! %s", e)
            return False
        return True


'''
'''
def main_argparse(assigned_args = None):  
    # type: (List)  
    """
    Parse and execute the call from command-line.
    Args:
        assigned_args: List of strings to parse. The default is taken from sys.argv.
    Returns: 
        Namespace list of args
    """
    import argparse, logging
    parser = argparse.ArgumentParser(prog="appcmd", description=globals()['__doc__'], epilog="!!Note: .....")
    parser.add_argument("-c", dest="config_file", metavar="Config File", help="Configuration file to use!")
    parser.add_argument("-i", dest="publish_interval", metavar="Publish Interval", type=int, help="Overwrite publish interval!")
    parser.add_argument("-r", dest="resource_name", metavar="TPG Resource Name", type=str, help="TPG Resource Name used for Web UI update!")
    parser.add_argument("-b", dest="vtag_buffer", metavar="VTag buffer size", type=int, default=100, help="Virtual Tag buffer size (default 100)!")
    parser.add_argument("-l", dest="file_level", metavar="File log level", type=int, action="store", default=None, help="Turn on file logging with level (10 - 50).")
    parser.add_argument("-v", "--verbose", dest="verbose_level", action="count", default=None, help="Turn on console DEBUG mode. Max = -vvv")
    parser.add_argument("-V", "--version", action="version", version=__version__) 

    return parser.parse_args(assigned_args)
    
'''
'''
def main(assigned_args = None):  
    # type: (List)    
       
    try:    
        cargs = main_argparse(assigned_args)
        my_app = TpgAppContext(cargs, 
                                app_name='vtag_app', 
                                logger=AppContext.initLogger(cargs.verbose_level, cargs.file_level, '/var/log/tpg_to_mqtt.log', False))    
        if not my_app.init_context():
            # debug_print_classes() # debuging modules loaded
            return my_app.exit_context(1)
    except KeyboardInterrupt as e:   
        if 'my_app' in locals() and my_app != None: 
            my_app.log_exception('Keyboard Interrupt Exception')
            return my_app.exit_context(e)  
        else:
            traceback.print_exc(file=sys.stdout) 
            return -1     
    except Exception as e:
        # debug_print_classes() # debugging 
        if 'my_app' in locals() and my_app != None: 
            my_app.log_exception('Initialization Exception')
            return my_app.exit_context(e)
        else:
            traceback.print_exc(file=sys.stdout)
            return -1
    else:
        try:
            if not my_app.run_context():
                return my_app.exit_context(1)
            else:
                return my_app.exit_context(0)
        except KeyboardInterrupt as e:
            my_app.log_exception('Keyboard Interrupt Exception')
            return my_app.exit_context(e)                
        except Exception as e:
            # traceback.print_exc(file=sys.stdout)
            my_app.log_exception('Runtime Exception')
            return my_app.exit_context(e)  
                 
    return 0
    
if __name__ == "__main__":     
    sys.exit(main())