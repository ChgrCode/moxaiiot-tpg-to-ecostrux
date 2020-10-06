# moxaiiot-tpg-to-ecostrux
Publish ThingsPro Gateway Equipment Tags to EcoStruxure Machine Advisor

## [ThingsPro Gateway information](https://www.moxa.com/en/products/industrial-computing/system-software/thingspro-2)


*******************************************************************************


[1 Getting started](#getting-started)

[2 Requirements](#requirements)

[3.1 Installation](#installation)

[3.2 Configuration](#configuration)

[4 Test](#test)

[5 ToDo's](#todos)

[6 Restrictions](#restrictions)

*******************************************************************************
<a name="getting-started"></a>

### 1 Getting started 

* Download and Install ThingsPro Gateway software v2.6.x
* Create the user program in tar.gz format or use pre-build bundle from "bin" folder above (see ThingsPro Gateway documentation)
* Upload the compressed folder to the ThingsPro Gateway User Programs
* If used with ThingsPro Gateway Web UI select the configuration UI (Menu -> Applications -> EcoStruxure Machine Advisor) after installation of the User Program (or if used without Web UI modify config.json file with your configuration)


#### How does this User Program integrate into ThingsPro Gateway?
This User Program is the Northbound Interface to Schneiders EcoStruxure Machine Advisor.

![ThingsPro Gateway Basic Architecture](media/TPG_arch1.png?raw=true "ThingsPro Gateway")


*******************************************************************************
<a name="requirements"></a>

### 2 Requirements
* UC-XXXX with ThingsPro Gateway v2.6.x installed
* EcoStruxure Machine Advisor connection information

*******************************************************************************
<a name="installation"></a>

### 3.1 Installation

Before creating the *.tgz package for uploading it to ThingsPro Gateway make sure that following files have execution rights.

* exec (main entry point)
* tpg_to_mqtt.py (main processing script)


	root@Moxa:~# cd /home/moxa/moxaiiot-tpg-to-ecostrux/
	root@Moxa:/home/moxa/moxaiiot-tpg-to-ecostrux# ls
	bundle.json  exec      lib      media      tpg_to_mqtt.py
	data         index.py  LICENSE  README.md  ui_folder
	root@Moxa:/home/moxa/moxaiiot-tpg-to-ecostrux# chmod +x exec
	root@Moxa:/home/moxa/moxaiiot-tpg-to-ecostrux# chmod +x tpg_to_mqtt.py
	root@Moxa:/home/moxa/moxaiiot-tpg-to-ecostrux# tar -czf my-ecostrux_v1.tgz *
	root@Moxa:/home/moxa/moxaiiot-tpg-to-ecostrux#


Copy my-ecostrux_v1.tgz to your PC and upload it to ThingsPro Gateway on Main Menu -> User Programs.

See also ThingsPro Gateway user documentation for further information.

![ThingsPro Gateway, User Program](media/TPG_user_program.png?raw=true "ThingsPro Gateway")

*******************************************************************************
<a name="configuration"></a>

### 3.2 Configuration

If used with ThingsPro Gateway Web UI enabled (default) go to ThingsPro Gateway Web UI and select Menu entry Applications -> EcoStruxure Machine Advisor. 

After uploading the compressed folder to ThingsPro Gateway User Program and enabled for running it will show up as below illustrated.

The configuration menu can be selected from the left Main Menu Application section:

![ThingsPro Gateway, Configuration](media/TPG_user_program_ui_menu.png?raw=true "ThingsPro Gatway")

![ThingsPro Gateway, Configuration](media/TPG_user_program_ui.png?raw=true "ThingsPro Gatway")

That's all, you can skip below configuration information.

If started without Web UI (User Program cmd line argument "noui"), the main script use one json formatted configuration file which can be selected with command line argument "-c <config.json>", if not provided it will use the default "config.json" file included in the data directory. 

The configuration file has two main sections:
* MQTT related connection information
* ThingsPro Virtual Tags to be published

	"assetname": "<asset_name>"
	
asset_name: Device name as configured in EcoStruxure Machine Advisor 
	
	"mqtt": {
		"broker_host": "<mqtt broker host>",
		"broker_port": 8883,
		"client_id": "<client_id>",
	   "clean_session": false,
	   "keepalive": 30,
		"enable_tls": true,  
		"tls_insecure_set": false,
	   "username": "<user name>",
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
			"CissACM0-GYRO-current",
			"CissACM0-MAGN-current",		
			"CissACM0-TEMP-current",
			"CissACM0-HUMI-current",
			"CissACM0-PRES-current"	
		]
	}

vtag_tags: Customized selection of Virtual Tags, based on Virtual Tag Device name and a list of Virtual Tags.

*******************************************************************************
<a name="test"></a>

### 4 Testing the configuration

This section only describes how to test the configuration modification, without Web UI. 
Copy the project folder to UC e.g.: /home/moxa

adjust the config.json configuration file if needed and execute the main script

	$ sudo python3 tpg_to_mqtt.py -v

or to specify a dedicated configuration file

	$ sudo python3 tpg_to_mqtt.py -c /home/moxa/my_config.json -v

If everything is ok, repack the whole folder content in a *.tgz file and upload it to ThingsPro Gateway user applications. (See ThingsPro Gateway user manual for full procedure)

*******************************************************************************
<a name="todos"></a>

### 5 ToDo's 

There is still a lot to do, let me know your experience or if you have some feedback.
* ...

*******************************************************************************
<a name="restrictions"></a>

### 6 Restrictions
* Only Tag Name including Timestamp and Tag values are published, other ThingsPro Gateway Tag information are ignored.
* ... 

