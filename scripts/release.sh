#!/bin/sh

set -e

VERSION=`python setup.py --version`

echo "# Releasing canaryd v$VERSION..."

echo "# Running tests..."
nosetests -s

echo "# Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags

echo "# Upload to pypi..."
# Clear dist
rm -rf dist/* build/*
# Build source and wheel packages
python setup.py sdist bdist_wheel
# Upload w/Twine
twine upload dist/*

echo "# All done!"
