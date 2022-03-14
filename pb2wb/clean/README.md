# PhiloBiblon clean data

Cleans CSVs with raw data.

## Clean data

Run the `mkclean.sh` script to create a `clean` directory. It can be run from any directory in the 
repo. The following example assumes you are in the `data` directory:

```
bash mkclean.sh
```

This will create a `clean` directory with a `BETA` sub-directory. Note:

* The `clean` directory should not be checked in to the repo. There is a `.gitignore` file in this directory to ensure that doesn't happen.
* The filenames are now lower case without spaces, for convenience. 

After running mkclean, you should have the following files:

```
clean
├── BETA
│   ├── beta_analytic.csv
│   ├── beta_bibliography.csv
│   ├── beta_biography.csv
│   ├── beta_copies.csv
│   ├── beta_geography.csv
│   ├── beta_institutions.csv
│   ├── beta_library.csv
│   ├── beta_ms_ed.csv
│   ├── beta_subject.csv
│   └── beta_uniform_title.csv
└── BETA_raw_links
    ├── beta_analytic.csv
    ├── beta_bibliography.csv
    ├── beta_biography.csv
    ├── beta_copies.csv
    ├── beta_geography.csv
    ├── beta_institutions.csv
    ├── beta_library.csv
    ├── beta_ms_ed.csv
    ├── beta_subject.csv
    └── beta_uniform_title.csv
```
