#!/bin/bash

today=`date +"%Y-%m-%d"`

## Gather alternate project tag or path from command line
while getopts "a:b:t:p": flag
do
    case "${flag}" in
        a) tag=${OPTARG};;
        b) bib=${OPTARG};;
        t) table=${OPTARG};;
        p) alt_processed_path=${OPTARG};;
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

## Check for bib number
if [[ -z $bib ]]; then
  echo "Alt bibliography not supplied, using default BETA"
  bib="BETA"
fi

## Check for table name
if [[ -z $table ]]; then
  echo "Table not supplied, default to all tables"
  table="None"
else
  echo "Alternate table name supplied: ${table}"
fi

## Identify location of philobiblon-private on local machine
echo "Looking for processed file path on local machine"

if [[ -n $alt_processed_path ]]; then
  full_path=$alt_processed_path
  echo "Using alternate processed file path: ${full_path}"
fi
if [[ -z $alt_processed_path ]]; then
  if processed_path=`find ~ -type d -name "philobiblon-private" 2>&1 | grep -v "Operation not permitted"`; then
    full_path=${processed_path}/data/processed/pre/$bib/*
  echo "Using processed file base path: ${full_path}"
  else
    echo "Unable to find base file path, please verify philobiblon-private-master directory exists"
    exit 1
  fi
fi
echo "Proceeding using the tag: ${tag}"

## Loop through processed files and create openrefine projects with updated version number
for f in `ls $full_path`;
  do
    if [[ $table != "None" ]]; then
      if [[ $f != *$table* ]]; then
        echo "Skipping table: ${f}"
        continue
      else
        echo "Creating project for table: ${table}"
      fi
    fi
  echo $f && openrefine-client -H philobiblon.cog.berkeley.edu -P 3333 --projectName=`basename $f | sed 's/.csv/.'${tag}'/'` --create $f
done

echo "OpenRefine projects created successfully"

