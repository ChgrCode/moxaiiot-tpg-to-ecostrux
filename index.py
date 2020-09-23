#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import logging
import os
import subprocess
import json
import sh
import time
from sanji.core import Route
from sanji.core import Sanji

from sanji.model_initiator import ModelInitiator

_logger = logging.getLogger("sanji.secos")


class Secos(object):

    def __init__(self, *args, **kwargs):
        root_path = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("secos", root_path)

    def get(self):
        return self.model.db

    def put(self, data):
        self.model.db = data
        self.model.save_db()
        return data


def setCCS(status):
    data = {
        "code": 200,
        "method": "put",
        "resource": "/CCS/secos",
        "data": {
        }
    }
    data["data"]["status"] = status
    sh.mosquitto_pub("-t", "/controller", "-m", json.dumps(data,indent=2))


class Index(Sanji):

    def init(self, *args, **kwargs):
        self.path_root = os.path.abspath(os.path.dirname(__file__))
        self.executable = 'tpg_to_mqtt.py'
        self.executable_config = os.path.join(self.path_root, 'data/secos.json')
        self.executable_param = ['-c %s'% self.executable_config, '-r /CCS/secos', '-l 20', '-v']
        self.mySubP = None
        self.secos = Secos()
        config = self.secos.get()

        if config["enable"]:
            self.stop_executable()
            self.start_executable()
        else:
            _logger.info("Module Not enabled")
            setCCS('False')

    def start_executable(self):
        process = os.path.join(self.path_root, self.executable)
        _logger.info('Start executable: %s', process)
        popen_param = list()
        popen_param.append(process)
        popen_param.extend(self.executable_param)
        _logger.info("Starting executable %s", popen_param)
        self.mySubP = subprocess.Popen(popen_param)
        if self.mySubP.poll() != None:
            _logger.info("Starting Failed, process not running")
            return False
        return True
    
    def stop_executable(self):
        _logger.info("Stopping executable %s", self.executable)
        if self.mySubP != None:
            self.mySubP.kill()
            time.sleep(1)
            if self.mySubP.poll() == None:
                _logger.error("Process still running killing it")
                subprocess.call(['killall', self.executable])
        self.mySubP = None
        return True


    @Route(methods="get", resource="/resource/secos")
    def get(self, message, response):
        _logger.info("GET method: ")
        # check if program is running and eventually run
        if self.mySubP is None:
            _logger.error("No ProcessInfo found - Process may not run")
	    # no Process information available
        else:
            poll = self.mySubP.poll()
            if poll == None:
                _logger.info("Process is running")
            else:
                _logger.error("Process is not running")
                self.stop_executable()
                setCCS('False')
        return response(data=self.secos.get())

    @Route(methods="put", resource="/resource/secos")
    def put(self, message, response):
        _logger.info("PUT method:")
        #print (message.data)
        try:
            self.secos.put(message.data)
        except Exception as e:
            return response(code=400, data={"message": e.message})

        if message.data["enable"]:
            if self.mySubP is not None:
                if self.mySubP.poll() is None:
                    _logger.warning('Trying to start executable but already running! Restarting')
                    self.stop_executable()
                    if self.start_executable() is False:
                        # clean up
                        self.stop_executable()
                        setCCS('False')
            else:
                if self.start_executable() is False:
                    # clean up
                    self.stop_executable()
                    setCCS('False')                   
        else:
            self.stop_executable()
            setCCS('False')
        return response(data=message.data) 


    @Route(methods="put", resource="/CCS/secos")
    # get Cloud Connection Status
    def CCS_event(self, message):
        status = False
        data = self.secos.get()
        if message.data['status'] == 'False':
            data['cloud_conn_status'] = status
            self.secos.put(data)
        else:
            if data['enable']:
                status = True
                data['cloud_conn_status'] = status
                self.secos.put(data)

        _logger.debug("Remote connection status:: %s", message.data['status'])
        self.publish.event.put(
            "/socket/app/message",
            data={
                "data": {"cloud_conn_status": status},
                "event": "CCS/secos",
                "key": "connectionStatus"})


if __name__ == "__main__":
    from sanji.connection.mqtt import Mqtt

    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.secos")
    setCCS('False')
    index = Index(connection=Mqtt())
    index.start()
