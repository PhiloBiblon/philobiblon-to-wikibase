#!/bin/bash

# Note: the schema for the dataclips may change when we get the next drop from John

pbbase=`git rev-parse --show-toplevel`
cd $pbbase/pb2wb

for BIB in BETA BITECA BITAGAP
do
    bash clean/mkclean_bib.sh $BIB
    echo
done

cd $pbbase/data

echo
echo Cleaning the datadict

# Clean the datadict

# Create a raw_links directory
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

