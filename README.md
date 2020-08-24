# moxaiiot-tpg-to-ecostrux
Publish ThingsPro Gateway Equipment Tags to EcoStruxure Machine Advaisor

[ThingsPro Gateway information](https://www.moxa.com/en/products/industrial-computing/system-software/thingspro-2)

[1. Getting started](#getting-started)

[2. Requirements](#requirements)

[3. Configuration](#configuration)

[4. Test](#test)

[5. ToDo's](#todos)

*******************************************************************************
<a name="getting-started"></a>
### 1. Getting started 

* Download and Install ThingsPro Gateway software v2.5.x
* Configure Modbus Data Acquisition Virtual Tags using ThingsPro Gateway Web UI
* Modify config.json file with your configuration
* Package the user program in tar.gz format
* Upload the Compressed folder to the ThingsPro Gateway

<a name="requirements"></a>
### 2. Requirements
* UC-XXXX with ThingsPro Gateway v2.6.x installed
* EcoStruxure Machine Advaisor connection information


<a name="configuration"></a>
### 3. Configuration

The application uses one json formatted configuration file which can be selected with command line argument "-c <config.json>", if not provided it will use the default "config.json" file included in the main application directory. 

The configuration file has two main sections:
* MQTT related connection information
* ThingsPro Virtual Tags to be published

	"asset_name": "<asset_name>"
	
asset_name: Device name as configured in EcoStruxure Machine Advaisor 
	
	"mqtt": {
		"broker_host": "broker.com",
		"broker_port": 8883,
		"client_id": "<client_id>",
	   "clean_session": false,
	   "keepalive": 30,
		"enable_tls": true,  
		"tls_insecure_set": false,
	   "user_name": "<user name>",
	   "password":  "<password>",    
		"default_topic": "devices/<client_id>/messages/events/"
	}
	
MQTT section
	
	"publish_interval": 5
	
publish_interval: Publish interval 

	"tpg_vtag_template": "CissSensor"
	
tpg_vtag_template: Virtual Tag Template name, this information will be used to publish all Tags
defined on this Virtual Tag Device in case "vtag_tags" is empty.

	"vtag_tags": {
		"CissSensor": [
			"CissACM0-ACCL-current",
			"CissACM0-ACCL-mean",
			"CissACM0-ACCL_x-mean",
			"CissACM0-ACCL_y-mean",
			"CissACM0-ACCL_z-mean",
			"CissACM0-GYRO-current",
			"CissACM0-MAGN-current",		
			"CissACM0-TEMP-current",
			"CissACM0-HUMI-current",
			"CissACM0-PRES-current"	
		]
	}

vtag_tags: Customised selection of Virtual Tags, based on Virtual Tag Device name and a list of Virtual Tags.

<a name="test"></a>
### 4. Testing the configuration

Copy the project folder to UC e.g.: /home/moxa

ajust the config.json configuration file if needed and execute the main script

	$ sudo python2 tpg_to_mqtt.py -v

or to specify a dedicated configuration file

	$ sudo python2 tpg_to_mqtt.py -c /home/moxa/my_config.json -v

If everything is ok, repack the whole folder content in a *.tgz file and upload it to ThingsPro Gateway user applications. (See ThingsPro user manual for full procedure)

Best practice: ...

<a name="todos"></a>
### 5. ToDo's 

There is still a lot to do, let me know your experience or if you have some feedback.
* ...

<a name="restrictions"></a>
### 6. Restrictions
* ...

