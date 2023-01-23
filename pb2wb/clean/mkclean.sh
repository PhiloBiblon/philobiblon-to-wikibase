#!/bin/bash

# Note: the schema for the dataclips may change when we get the next drop from John

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/data

# At present, this script works only with BETA and the Data Dictionary (same for all bibliographies)
# TODO: add the other bibliographies; blocked by pbbase/data/fetch_from_gdrive and
# pbbase/data/google_ids.csv. Also: we need to change the directory hierarchy in data/clean

# Clean BETA table csvs

# The raw_links directory is used as a staging area and a place in which to rename the individual files
mkdir -p ./clean/raw_links

ln -f './raw/BETA/csvs/BETA - ANALYTIC'* ./clean/raw_links/beta_analytic.csv
ln -f './raw/BETA/csvs/BETA - BIBLIOGRAPHY'* ./clean/raw_links/beta_bibliography.csv
ln -f './raw/BETA/csvs/BETA - BIOGRAPHY'* ./clean/raw_links/beta_biography.csv
ln -f './raw/BETA/csvs/BETA - COPIES'* ./clean/raw_links/beta_copies.csv
ln -f './raw/BETA/csvs/BETA - GEOGRAPHY'* ./clean/raw_links/beta_geography.csv
ln -f './raw/BETA/csvs/BETA - INSTITUTIONS'* ./clean/raw_links/beta_institutions.csv
ln -f './raw/BETA/csvs/BETA - LIBRARY'* ./clean/raw_links/beta_library.csv
ln -f './raw/BETA/csvs/BETA - MS_ED'* ./clean/raw_links/beta_ms_ed.csv
ln -f './raw/BETA/csvs/BETA - SUBJECT'* ./clean/raw_links/beta_subject.csv
ln -f './raw/BETA/csvs/BETA - UNIFORM_TITLE'* ./clean/raw_links/beta_uniform_title.csv

mkdir -p ./clean/BETA/csvs

for f in `ls ./clean/raw_links`
do
    echo 'checking for illegal utf8 in: ' $f
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/BETA/csvs/$f
done

# Now we can throw away the raw_links directory

rm -rf ./clean/raw_links

# For compatibility (BETA only) we will also link clean csvs into $pbbase/data/clean/BETA

ln -f $pbbase/data/clean/BETA/csvs/*.csv $pbbase/data/clean/BETA

# Clean the BETA dataclips

# Bring back the raw_links directory
mkdir -p ./clean/raw_links

ln -f './raw/BETA/dataclips/BETA - DATACLIPS'* ./clean/raw_links/beta_dataclips.csv

mkdir -p ./clean/BETA/dataclips

for f in `ls ./clean/raw_links`
do
    echo 'checking for illegal utf8 in BETA dataclips: ' $f
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh | \
        csvformat -M '@' | tr '\n@' ' \n' | \
        (echo "code,Status,Records,Bounds,Muster,es,en,Factgrid P#,Factgrid Q#,Wikidata P#,Wikidata Q#,unnamed1,unnamed2,unnamed3"; cat -) > $pbbase/data/clean/BETA/dataclips/$f
done

# Now we can throw away the raw_links directory

rm -rf ./clean/raw_links

# Clean the datadict

# Bring back the raw_links directory
mkdir -p ./clean/raw_links

ln -f ./raw/datadict/*ANA* ./clean/raw_links/analytic_datadict.csv
ln -f ./raw/datadict/*BIB* ./clean/raw_links/bibliography_datadict.csv
ln -f ./raw/datadict/*BIO* ./clean/raw_links/biography_datadict.csv
ln -f ./raw/datadict/*COP* ./clean/raw_links/copies_datadict.csv
ln -f ./raw/datadict/*GEO* ./clean/raw_links/geography_datadict.csv
ln -f ./raw/datadict/*INS* ./clean/raw_links/institutions_datadict.csv
ln -f ./raw/datadict/*LIB* ./clean/raw_links/library_datadict.csv
ln -f ./raw/datadict/*MAN* ./clean/raw_links/ms_ed_datadict.csv
ln -f ./raw/datadict/*SUB* ./clean/raw_links/subject_datadict.csv
ln -f ./raw/datadict/*UNI* ./clean/raw_links/uniform_title_datadict.csv

mkdir -p ./clean/datadict

for f in `ls ./clean/raw_links`
do
    echo 'checking for illegal utf8 in the datadict: ' $f
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8check.sh
    cat $pbbase/data/clean/raw_links/$f | bash $pbbase/pbcsv/utf8clean.sh > $pbbase/data/clean/datadict/$f
done

# Now we can throw away the raw_links directory

rm -rf ./clean/raw_links

