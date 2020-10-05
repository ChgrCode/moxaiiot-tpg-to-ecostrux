#! /bin/bash

BUNDLE_VERSION=$1
BUNDLE_NAME="moxaiiot-tpg-to-ecostrux_v$BUNDLE_VERSION.tgz"

chmod +x "exec"
chmod +x "tpg_to_mqtt.py"

BUNDLE_CONTENT=(

exec 
tpg_to_mqtt.py
index.py
bundle.json
LICENSE
README.md
lib/*
data/*
ui_folder/*

)

tar -czf $BUNDLE_NAME ${BUNDLE_CONTENT[*]}
if [ $? -ne 0 ] ; then
    echo "Failed to build $BUNDLE_NAME"
    exit -1
fi
echo "Successful build $BUNDLE_NAME"
exit 0
