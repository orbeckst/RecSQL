#!/bin/bash

PACKAGE=RecSQL

SERVERDIR=/sansom/public_html/sbcb/oliver
PACKAGES=$SERVERDIR/download/Python
DOCS=$SERVERDIR/software/$PACKAGE

usage="usage: $0 [-h] [cmd1 cmd2 ...]

Distribute $PACKAGE. 

default: 'distribution docs'

cmd           description
-----         -----------------
distribution  make sdist and egg, copy to $PACKAGES
docs          'make_epydoc make_sphinx'
make_epydoc   source code docs, copy to $DOCS/epydoc
make_sphinx   documentation, copy to $DOCS/html
"

function die () {
    echo 1>&2 "ERROR: $1"
    exit ${2:-1}
}


distribution () {
  python setup.py sdist \
      && python setup.py bdist_egg \
      && rsync -v --checksum dist/* $PACKAGES \
      || die "Failed distribution"
}

make_epydocs() {
  epydoc -v -o doc/epydoc --html --name=$PACKAGE \
         --url=http://sbcb.bioch.ox.ac.uk/oliver/software/$PACKAGE/ \
         recsql  \
      || die "Failed making epydoc"
  rsync -vrP --delete doc/epydoc $DOCS
}

make_sphinx () {
  (cd doc/sphinx && make html) || die "Failed making sphinx docs"
  rsync -vrP --delete doc/sphinx/build/html $DOCS
}

docs () {
  make_epydocs 
  make_sphinx
}


case "$1" in
    -h|--help) echo "$usage"; exit 0;;
esac

commands="$@"
[ -n "$commands" ] || commands="distribution docs"

for cmd in $commands; do
    eval "$cmd"
done


  
