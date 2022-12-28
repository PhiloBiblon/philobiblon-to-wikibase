#!/bin/bash

# Note: the schema for the dataclips may change when we get the next drop from John

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/data

# Clean BETA table csvs

# The BETA_raw_links directory is used as a staging area and a place in which to rename the individual files
mkdir -p ./clean/BETA_raw_links

ln -f './raw/BETA/csvs/BETA - ANALYTIC'* ./clean/BETA_raw_links/beta_analytic.csv
ln -f './raw/BETA/csvs/BETA - BIBLIOGRAPHY'* ./clean/BETA_raw_links/beta_bibliography.csv
ln -f './raw/BETA/csvs/BETA - BIOGRAPHY'* ./clean/BETA_raw_links/beta_biography.csv
ln -f './raw/BETA/csvs/BETA - COPIES'* ./clean/BETA_raw_links/beta_copies.csv
ln -f './raw/BETA/csvs/BETA - GEOGRAPHY'* ./clean/BETA_raw_links/beta_geography.csv
ln -f './raw/BETA/csvs/BETA - INSTITUTIONS'* ./clean/BETA_raw_links/beta_institutions.csv
ln -f './raw/BETA/csvs/BETA - LIBRARY'* ./clean/BETA_raw_links/beta_library.csv
ln -f './raw/BETA/csvs/BETA - MS_ED'* ./clean/BETA_raw_links/beta_ms_ed.csv
ln -f './raw/BETA/csvs/BETA - SUBJECT'* ./clean/BETA_raw_links/beta_subject.csv
ln -f './raw/BETA/csvs/BETA - UNIFORM_TITLE'* ./clean/BETA_raw_links/beta_uniform_title.csv

mkdir -p ./clean/BETA/csvs

for f in `ls ./clean/BETA_raw_links`
do
    echo 'checking for illegal utf8 in: ' $f
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/BETA/csvs/$f
done

# Now we can throw away the BETA_raw_links directory

rm -rf ./clean/BETA_raw_links

# For compatibility (BETA only) we will also link clean csvs into $pbbase/data/clean/BETA

ln -f $pbbase/data/clean/BETA/csvs/*.csv $pbbase/data/clean/BETA

# Clean the BETA dataclips

mkdir -p ./clean/BETA/dataclips

for f in `ls ./raw/BETA/dataclips | grep csv$`
do
    echo 'checking for illegal utf8 in BETA: ' $f
    cat $pbbase/data/raw/BETA/dataclips/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/raw/BETA/dataclips/$f | bash $pbbase/pbcsv/utf8clean.sh | \
        csvformat -M '@' | tr '\n@' ' \n' | \
        (echo "code,Status,Records,Bounds,Muster,es,en,Factgrid P#,Factgrid Q#,Wikidata P#,Wikidata Q#"; cat -) > $pbbase/data/clean/BETA/dataclips/$f
done

# Clean the datadict

mkdir -p ./clean/datadict

for f in `ls ./raw/datadict | grep csv$`
do
    echo 'checking for illegal utf8 in the datadict: ' $f
    cat $pbbase/data/raw/datadict/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/raw/datadict/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/datadict/$f
done

