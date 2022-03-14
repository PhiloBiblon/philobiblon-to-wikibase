#!/bin/bash

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/data

mkdir -p ./clean/BETA_raw_links
mkdir -p ./clean/BETA

ln -f './raw/BETA/BETA - ANALYTIC.CSV' ./clean/BETA_raw_links/beta_analytic.csv
ln -f './raw/BETA/BETA - BIBLIOGRAPHY.CSV' ./clean/BETA_raw_links/beta_bibliography.csv
ln -f './raw/BETA/BETA - BIOGRAPHY.CSV' ./clean/BETA_raw_links/beta_biography.csv
ln -f './raw/BETA/BETA - COPIES.CSV' ./clean/BETA_raw_links/beta_copies.csv
ln -f './raw/BETA/BETA - GEOGRAPHY.CSV' ./clean/BETA_raw_links/beta_geography.csv
ln -f './raw/BETA/BETA - INSTITUTIONS.CSV' ./clean/BETA_raw_links/beta_institutions.csv
ln -f './raw/BETA/BETA - LIBRARY.CSV' ./clean/BETA_raw_links/beta_library.csv
ln -f './raw/BETA/BETA - MS_ED.CSV' ./clean/BETA_raw_links/beta_ms_ed.csv
ln -f './raw/BETA/BETA - SUBJECT.CSV' ./clean/BETA_raw_links/beta_subject.csv
ln -f './raw/BETA/BETA - UNIFORM_TITLE.CSV' ./clean/BETA_raw_links/beta_uniform_title.csv

for f in `ls ./clean/BETA_raw_links`
do
    echo 'illegal utf8 in: ' $f
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/BETA_raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/BETA/$f
done
