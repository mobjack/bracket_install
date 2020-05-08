#!/bin/sh

docker container prune

# Delete old image
OLD_ID=`docker image ls | grep install-api | awk '{print $3}'`
if [ $OLD_ID ] ; then
    docker image rm -f `docker image ls | grep install-api | awk '{print $3}'` 
else
    printf '\n'
    printf '#######\n'
    printf 'No old images found...\nMoving On...'
    printf '#######\n'
    printf '\n'
fi

# Build a new image
docker build -t install-api ./ 

# Run it
docker run -d --name install-api -p 80:80 install-api &

#docker logs -f 

echo "########### Started? ##########\n"
docker image ls

echo '\n'
