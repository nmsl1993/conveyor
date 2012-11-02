#!/bin/bash

PYVERSION=$1
BASEDIR=`echo $0|sed 's|/.*||'`

if [ -z $PYVERSION ]
then
    PYVERSION=`python -c 'import sys; print ".".join(sys.version.split()[0].split(".")[0:2])'`
    echo "python version is $PYVERSION"
else
    PYBINVERSION=$PYVERSION
fi

UNAME=`uname`
MAC_DISTUTILS=/System/Library/Frameworks/Python.framework/Versions/$PYVERSION/lib/python$PYVERSION/distutils/__init__.py
if [ "$UNAME" == "Darwin" ]
then
    MACVER=`system_profiler SPSoftwareDataType |grep '^ *System Version:' |sed 's/.*OS X //' | sed 's/\(10\.[0-9]\)*.*$/\1/'`

    export PATH=$PATH:$BASEDIR/submodule/conveyor_bins/mac/$MACVER

    if [ ! -f $MAC_DISTUTILS ]
    then
	sudo cp mac/$PYVERSION/distutils/__init__.py $MAC_DISTUTILS
    fi
fi

if [ ! -d virtualenv/ ]
then
	python$PYBINVERSION virtualenv.py virtualenv
fi

. virtualenv/bin/activate
echo "Upgrading setuptools"
pip install -q --upgrade setuptools
echo "Installing modules"
pip install -q --use-mirrors coverage doxypy mock lockfile python-daemon unittest-xml-reporting argparse unittest2
echo "Installing pyserial egg"
easy_install -q submodule/conveyor_bins/pyserial-2.7_mb2.1-py$PYVERSION.egg
echo "Installing paramiko"
pip install paramiko
echo "installing makerbot driver"
#installing makerbot_driver
easy_install submodule/conveyor_bins/pyserial-2.7_mb2.1-py2.7.egg

