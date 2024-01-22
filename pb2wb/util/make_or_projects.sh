#!/bin/bash

# Set default values
BIB="BETA"
or_host="localhost"
or_port="3333"
tag="new"
dryrun=false

# Parse command line arguments
while [ "$#" -gt 0 ]; do
  case "$1" in
    --BIB=*)
      BIB="${1#*=}"
      ;;
    --or_host=*)
      or_host="${1#*=}"
      ;;
    --or_port=*)
      or_port="${1#*=}"
      ;;
    --tag=*)
      tag="${1#*=}"
      ;;
    --dryrun)
      dryrun=true
      ;;
    *)
      echo "Invalid option: $1"
      exit 1
  esac
  shift
done

# Note: openrefine-client requires python2!

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/pb2wb

datadir=$pbbase/data/processed/pre/$BIB

for f in $datadir/*
do
    pname=`basename $f | sed "s/.csv/.$tag/"`
    echo $pname
    echo openrefine-client -H $or_host -P $or_port --projectName=$pname --create $f
    openrefine-client -H $or_host -P $or_port --projectName=$pname --create $f
    if [ "$dryrun" = false ]; then
        openrefine-client -H "$or_host" -P "$or_port" --projectName="$pname" --create "$f"
    else
        echo "Dry run: openrefine-client command skipped"
    fi
done
