#!/bin/sh


DOC_ID=`docker container ls | grep install-api | awk '{print $1}'`

if [ $DOC_ID ] ; then
    docker container stop $DOC_ID
    docker container rm $DOC_ID
else
    printf 'No ID Found\n'
fi