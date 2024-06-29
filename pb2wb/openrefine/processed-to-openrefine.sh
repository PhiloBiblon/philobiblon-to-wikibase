#!/bin/bash

today=`date +"%Y-%m-%d"`

## Gather alternate project tag from command line
while getopts "t": flag
do
    case "${flag}" in
        t) tag=${OPTARG};;
    esac
done

if [[ -z $tag ]]; then
  echo "Alternate project tag not supplied, using default date: ${today}"
  tag=${today}
fi  

## Identify location of philobiblon-private-master on local machine
echo "Looking for processed file path on local machine"
if processed_path=`find ~ -type d -name "philobiblon-private-master" 2>&1 | grep -v "Operation not permitted"`; then
  echo "Using processed file base path: ${processed_path}"
else
  echo "Unable to find base file path, please verify philobiblon-private-master directory exists"
  exit 1
fi

echo "Proceeding using the tag: ${tag}"

## Loop through processed files and create openrefine projects with updated version number
for f in ${processed_path}/data/processed/pre/BETA/*
do
  echo $f && echo openrefine-client -H philobiblon.cog.berkeley.edu -P 3333 --projectName=`basename $f | sed 's/.csv/.'${tag}'/'` --create $f
done

