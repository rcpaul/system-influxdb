#!/bin/bash

while :
do
    echo "Trying .50"
    python3 system-influxdb.py
    echo "Waiting"
    sleep 180
done
