#!/bin/sh

# Exit on error
set -e

VERSION=`python setup.py --version`


echo "### Releasing canaryd v$VERSION..."


echo "--> Running tests..."
nosetests


echo "--> Git tag & push..."
git tag -a "v$VERSION" -m "v$VERSION"
git push --tags


echo "--> Building packages..."
# Clear dist & build
scripts/clean.sh

# Build source and wheel packages
python setup.py sdist bdist_wheel

# Build .deb and .rpm packages
scripts/package.sh


echo "--> Upload to pypi..."
# Upload w/Twine
twine upload dist/*


echo "<-- All done!"
