#!/bin/bash
#
# NOTE: This script expects to be run from the project root with
# ./scripts/get_chromedriver.sh

destination="tests/selenium/drivers"
mkdir -p $destination && cd $destination
curl -O https://chromedriver.storage.googleapis.com/2.27/chromedriver_mac64.zip
tar -zxf chromedriver_mac64.zip
rm chromedriver_mac64.zip
