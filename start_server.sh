#!/bin/bash

sudo apt-get update && sudo apt-get install python3-pip python3-dev python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install -U flask gunicorn requests flask-bootstrap flask-wtf pillow tensorflow keras
