#!/bin/bash
# Purpose: Stop PID (if running) abd remove the installed libraries (Including drivers)
# Script: Mario Divan
# ------------------------------------------

source ../pid/scripts/utilities.sh

removeImages() {    
    mess_inf "Removing Containers' Images from Docker"
    #It verifies the container to remove from the docker-compose file. 
    readarray -t containers <<< $(fgrep image: ./docker/docker-compose.yml | sed 's/^.*: //')
    for idcontainer in "${containers[@]}"; do
        #It verifies if the container is running
        if sudo docker rmi -f "$idcontainer" &> /dev/null; then #> /dev/null 2>&1
            # Check whether the image was removed           
            if  sudo docker images | grep -q "$idcontainer" &> /dev/null; then
                mess_er2 "\t$idcontainer: " "It could not be removed"
                exit 99
            else
                mess_ok2 "\t$idcontainer: " "Removed"
            fi            
        else
            #If not present, the image was removed
            mess_ok2 "$idcontainer: " "Removed"
        fi
    done    
}

mess_war "This action will remove PCA Docker images from your system. "
read -p "Are you sure to continue? (y/n) " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
  # commands if yes
  mess_ok2 "Delete Procedure: " "Confirmed"
else
  # commands if no
  mess_wa2 "Delete Procedure: " "Cancelled"
  exit 1
fi

mess_inf "Verifying Docker Installation"

if docker run hello-world >& /dev/null; then
    mess_oki "Docker is running correctly."
else
    mess_err "Docker is not running correctly. Please check your Docker installation."
    exit 1
fi

# Stop containers (if required)
mess_inf "Stopping PID containers"
if ./runPCA.sh stop; then
    mess_ok2 "\tPCA Containers: " "Stopped"
else
    mess_err "\tPCA Containers: " "No Stopped"
    exit 1
fi

mess_inf "Removing PCA Docker images from your system"
if removeImages; then
    mess_ok2 "\tPID containers: " "Removed"
else
    mess_er2 "\tPID Containers: " "Not Removed"
    exit 1
fi

mess_oki "PCA Removal Completed"