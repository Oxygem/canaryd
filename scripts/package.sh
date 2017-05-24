#!/bin/sh

# Exit on error
set -e

VERSION=`python setup.py --version`
DEB_VERSION=`echo $VERSION | sed 's/\.dev/~dev/'`


function build() {
    TYPE=$1

    # Build the package into a Docker image
    docker build -t canaryd-$TYPE-build -f docker/Dockerfile-$TYPE . > /dev/null

    # Create a container of that image
    docker create --name canaryd-$TYPE-build canaryd-$TYPE-build > /dev/null
}


# Build
#

echo "--> Building RPM..."
build rpm

echo "--> Building Deb..."
build deb

echo


# Copy
#

echo "--> Copying files..."

docker cp \
    canaryd-rpm-build:/opt/canaryd/dist/canaryd-$VERSION-1.noarch.rpm \
    dist/canaryd-$VERSION.rpm

echo "    dist/canaryd-$VERSION.rpm"

docker cp \
    canaryd-deb-build:/opt/canaryd/deb_dist/python-canaryd_$DEB_VERSION-1_all.deb \
    dist/canaryd-$VERSION.deb

echo "    dist/canaryd-$VERSION.deb"


# Cleanup
#

echo
echo "--> Removing containers..."

docker rm canaryd-rpm-build canaryd-deb-build > /dev/null


echo
echo "<-- Packages build!"
