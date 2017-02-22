#!/bin/bash

source environment.sh

waitress-serve --listen=0.0.0.0:6012 wsgi:application
