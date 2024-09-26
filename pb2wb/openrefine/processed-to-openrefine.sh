#!/bin/bash

today=`date +"%Y-%m-%d"`

## Gather alternate project tag from command line
while getopts "a:t": flag
do
    case "${flag}" in
        a) tag=${OPTARG};;
        t) table=${OPTARG};;
    esac
done

## Check if openrefine-client is installed
if ! command -v openrefine-client &> /dev/null
then
    echo "openrefine-client could not be found, please install before proceeding"
    exit 1
fi

## Check for alternate project tag
if [[ -z $tag ]]; then
  echo "Alternate project tag not supplied, using default date: ${today}"
  tag=${today}
fi

## Check for table name
if [[ -z $table ]]; then
  echo "Table not supplied, default to all tables"
  table="None"
fi

## Identify location of philobiblon-private on local machine
echo "Looking for processed file path on local machine"
if processed_path=`find ~ -type d -name "philobiblon-private" 2>&1 | grep -v "Operation not permitted"`; then
  echo "Using processed file base path: ${processed_path}"
else
  echo "Unable to find base file path, please verify philobiblon-private-master directory exists"
  exit 1
fi

echo "Proceeding using the tag: ${tag}"

## Loop through processed files and create openrefine projects with updated version number
for f in ${processed_path}/data/processed/pre/BETA/*
  do
    if [[ $table != "None" ]]; then
      if [[ $f != *$table* ]]; then
        continue
      else
        echo "Creating project for table: ${table}"
      fi
    fi
  echo $f
  #echo $f && openrefine-client -H philobiblon.cog.berkeley.edu -P 3333 --projectName=`basename $f | sed 's/.csv/.'${tag}'/'` --create $f
done

echo "OpenRefine projects created successfully"

