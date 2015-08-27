#!/bin/bash

# # Exit on errors from here.
set -e

composefile="${INSTALLDIR}/mama-ng-deploy/docker-compose.yml"

docker-compose -f "$composefile" build mamangcontrol
docker-compose -f "$composefile" up -d
