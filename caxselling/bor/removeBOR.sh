#!/bin/bash
# Purpose: Stop BOR (if running) and remove the installed images
# Script: Mario Divan
# ------------------------------------------

source ../pid/scripts/utilities.sh

removeImages() {    
    mess_inf "Removing Containers' Images from Docker"
    #It verifies the container to remove from the docker-compose file. 
    readarray -t containers <<< $(fgrep image: ./docker/docker-compose.yml | sed 's/^.*: //')
    for idcontainer in "${containers[@]}"; do
        image_ids=$(sudo docker images "$idcontainer" --format "{{.ID}}")

        if [ -n "$image_ids" ]; then
            echo "$image_ids" | xargs -r sudo docker rmi -f > /dev/null 2>&1
            mess_ok2 "$idcontainer: " "Removed (all tags)"
        else
            mess_ok2 "$idcontainer: " "No images found"
        fi        
    done    
}

mess_war "This action will remove BOR Docker images from your system. "
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
mess_inf "Stopping BOR containers"
if ./runBOR.sh stop; then
    mess_ok2 "\tBOR Containers: " "Stopped"
else
    mess_err "\tBOR Containers: " "No Stopped"
    exit 1
fi

mess_inf "Removing BOR Docker images from your system"
if removeImages; then
    mess_ok2 "\tBOR containers: " "Removed"
else
    mess_er2 "\tBOR Containers: " "Not Removed"
    exit 1
fi

mess_oki "BOR Removal Completed"