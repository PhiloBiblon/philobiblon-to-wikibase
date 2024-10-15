#!/bin/bash

# Note: the schema for the dataclips may change when we get the next drop from John

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/data

BIB=$1

case $BIB in
    BETA)
        lang=es
        ;;
    BITECA)
        lang=ca
        ;;
    BITAGAP)
        lang=pt
        ;;
esac

BIB=`echo $BIB | tr '[a-z]' '[A-Z]'`

BIB_LOWER=`echo $BIB | tr '[A-Z]' '[a-z]'`

echo Cleaning $BIB

# The raw_links directory is used as a staging area and a place in which to rename the individual files
mkdir -p ./clean/$BIB/raw_links

ln -f "./raw/$BIB/csvs/$BIB - ANALYTIC"* ./clean/$BIB/raw_links/${BIB_LOWER}_analytic.csv
ln -f "./raw/$BIB/csvs/$BIB - BIBLIOGRAPHY"* ./clean/$BIB/raw_links/${BIB_LOWER}_bibliography.csv
ln -f "./raw/$BIB/csvs/$BIB - BIOGRAPHY"* ./clean/$BIB/raw_links/${BIB_LOWER}_biography.csv
ln -f "./raw/$BIB/csvs/$BIB - COPIES"* ./clean/$BIB/raw_links/${BIB_LOWER}_copies.csv
ln -f "./raw/$BIB/csvs/$BIB - GEOGRAPHY"* ./clean/$BIB/raw_links/${BIB_LOWER}_geography.csv
ln -f "./raw/$BIB/csvs/$BIB - INSTITUTIONS"* ./clean/$BIB/raw_links/${BIB_LOWER}_institutions.csv
ln -f "./raw/$BIB/csvs/$BIB - LIBRARY"* ./clean/$BIB/raw_links/${BIB_LOWER}_library.csv
ln -f "./raw/$BIB/csvs/$BIB - MS_ED"* ./clean/$BIB/raw_links/${BIB_LOWER}_ms_ed.csv
ln -f "./raw/$BIB/csvs/$BIB - SUBJECT"* ./clean/$BIB/raw_links/${BIB_LOWER}_subject.csv
ln -f "./raw/$BIB/csvs/$BIB - UNIFORM_TITLE"* ./clean/$BIB/raw_links/${BIB_LOWER}_uniform_title.csv

mkdir -p ./clean/$BIB/csvs

for f in `ls ./clean/$BIB/raw_links`
do
    echo 'checking for illegal utf8 in: ' $f
    cat $pbbase/data/clean/$BIB/raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/$BIB/raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/$BIB/csvs/$f
done

# Now we can throw away the raw_links directory

rm -rf ./clean/$BIB/raw_links

# Clean the $BIB dataclips

# Bring back the raw_links directory
mkdir -p ./clean/$BIB/raw_links

ln -f "./raw/$BIB/dataclips/$BIB - DATACLIPS"* ./clean/$BIB/raw_links/${BIB_LOWER}_dataclips.csv

mkdir -p ./clean/$BIB/dataclips

for f in `ls ./clean/$BIB/raw_links`
do
    echo "checking for illegal utf8 in $BIB dataclips: " $f
    cat $pbbase/data/clean/$BIB/raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/$BIB/raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh | \
        csvformat -M '@' | tr '\n@' ' \n' | sed 1d | \
        (echo "code,class,status,census,${lang},en,unk1,unk2"; cat -) > $pbbase/data/clean/$BIB/dataclips/$f
done

# Now we can throw away the raw_links directory

rm -rf ./clean/$BIB/raw_links

