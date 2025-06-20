#!/bin/bash
# Purpose: Check BOR pre-requisites 
# Script: Mario Divan
# ------------------------------------------

source ../pid/scripts/utilities.sh
source ./docker/.env

mess_inf "Verifying Docker Availability"
# Check if docker is installed
if docker version >& /dev/null; then
    mess_oki "Docker is installed."
    docker version
else
    mess_err "Docker is not installed or could not be reached. Please install Docker (https://docs.docker.com/engine/install/ubuntu/)."
    exit 1
fi

mess_inf "Verifying Docker Installation"

if docker run hello-world >& /dev/null; then
    mess_oki "Docker is running correctly."
else
    mess_err "Docker is not running correctly. Please check your Docker installation."
    exit 1
fi

if test -e ./docker/docker-compose.yml; then
    mess_ok2 "\tDocker compose file: " "Found"
else
    mess_er2 "\tDocker compose file: " "Not Found"
    exit 1
fi

if checkDockerNetwork; then
    mess_oki "Docker network is available."
else
    mess_err "Docker network is not available. Please check your Docker installation."
    exit 1
fi

# Pull and create the docker image
mess_inf "Pulling the BOR Docker image ..."
readarray -t theimages <<< $(fgrep image: ./docker/docker-compose.yml | sed 's/^.*: //')
for animage in "${theimages[@]}"; do
    if [[ $animage == *"bor"* ]]; then
        mess_wa2 "\t$animage: " "To be created"
        continue
    else
        running_status=$(docker pull $animage 2> /dev/null)
        
        if docker inspect --type=image "$animage" > /dev/null 2>&1; then
            mess_op2 "\t$animage: " "Available"
        else
            mess_er2 "\t$animage:  " "Unavailable"
        fi            
    fi  
done 

mess_inf "Creating BOR Server ..."
if docker compose -f ./docker/docker-compose.yml build 2>&1 > /dev/null ; then 
    mess_ok2 "\tBOR Server (RestX): " "Created"
else
    mess_er2 "\tBOR Server (RestX): " "Failed"
    exit 1
fi

DIR=./docker/sharedata
if [ ! -d "$DIR" ]; then
    mkdir -p "$DIR"
fi

if [ "$(stat -c '%u' "$DIR")" = "$UID" ]; then
    mess_ok2 "\t$BOR_SERVER_USER (UID $UID) is the owner of $DIR. Continuing..."
else
    mess_op2 "\t$BOR_SERVER_USER (UID $UID) is not the owner of $DIR. Changing ownership..."
    if sudo chown -R "$UID":"$UID" "$DIR"; then
        mess_ok2 "\tShared Data Directory: " "Ownership changed to $BOR_SERVER_USER (UID $UID)"
    else
        mess_er2 "\tShared Data Directory: " "Failed to change ownership"
        exit 1
    fi
fi

if sudo chmod -R u+w $DIR; then
    mess_ok2 "\tShared Data Directory: " "Established Permissions"
else
    mess_er2 "\tShared Data Directory: " "Failed to set permissions"
    exit 1
fi

mess_oki "All Containers are available and ready for execution!"