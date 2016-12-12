#!/bin/bash

source environment.sh

export PYTHONPATH=.:/Users/andy/work/gds/csd/ags_client_python:$PYTHONPATH

gunicorn -w 4 -b 0.0.0.0:6012 wsgi:application
