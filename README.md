# svnreview

## Introduction

A simple python script to search an SVN repository's history and create a formatted review template.

The script takes any number of search parameters on the command line. All search parameters provided will be logically
ORed, which is to say that any revision containing any of the search parameters will be included.

The script can also be provided with details of previous reviews. The revisions that were included in the previous
reviews will be omitted from the changes in this review but overall changes for each file are also provided.

![Automation](http://imgs.xkcd.com/comics/automation.png)

## Usage

Before the script can be used an environment variable must be defined named `SVNROOT` which is to contain a valid
SVN URL path to the SVN repository that is being used.

In linux that can be done by either running the following commands before executing the script or adding them to your
`.bashrc` file:

    SVNROOT=<your SVN URL here>
    export SVNROOT

The script is executed using the python interpreter. Previous revisions are defined using the option '-r' followed by
a parameter in the format `<review number>:<first revision>-<last revision>`.

### Example 1: First review

    python review.py '#1234'

### Example 2: Second review

Assuming that the first review discovered revisions ranging from 34 to 42:

    python review.py -r '1:34-42' '#1234'
