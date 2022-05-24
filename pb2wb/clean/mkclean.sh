#!/bin/bash

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/data

mkdir -p ./clean/BETA_raw_links
mkdir -p ./clean/BETA

ln -f './raw/BETA/BETA - ANALYTIC'* ./clean/BETA_raw_links/beta_analytic.csv
ln -f './raw/BETA/BETA - BIBLIOGRAPHY'* ./clean/BETA_raw_links/beta_bibliography.csv
ln -f './raw/BETA/BETA - BIOGRAPHY'* ./clean/BETA_raw_links/beta_biography.csv
ln -f './raw/BETA/BETA - COPIES'* ./clean/BETA_raw_links/beta_copies.csv
ln -f './raw/BETA/BETA - GEOGRAPHY'* ./clean/BETA_raw_links/beta_geography.csv
ln -f './raw/BETA/BETA - INSTITUTIONS'* ./clean/BETA_raw_links/beta_institutions.csv
ln -f './raw/BETA/BETA - LIBRARY'* ./clean/BETA_raw_links/beta_library.csv
ln -f './raw/BETA/BETA - MS_ED'* ./clean/BETA_raw_links/beta_ms_ed.csv
ln -f './raw/BETA/BETA - SUBJECT'* ./clean/BETA_raw_links/beta_subject.csv
ln -f './raw/BETA/BETA - UNIFORM_TITLE'* ./clean/BETA_raw_links/beta_uniform_title.csv

for f in `ls ./clean/BETA_raw_links`
do
    echo 'checking for illegal utf8 in: ' $f
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/BETA/$f
done
