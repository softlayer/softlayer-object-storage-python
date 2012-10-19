#!/usr/bin/python
from setuptools import setup, find_packages
import sys
from object_storage.consts import __version__

name = 'softlayer-object-storage'
version = __version__
_ver = sys.version_info

requirements = ['httplib2']
if _ver[0] == 2 and _ver[1] < 6:
    requirements.append('simplejson')


# Python 3 conversion
extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

setup(
    name=name,
    version=version,
    description='Softlayer Object Storage client bindings for python.',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Distributed Computing',
        'Topic :: Utilities',
        ],
    author='SoftLayer Technologies, Inc.',
    author_email='sldn@softlayer.com',
    url='https://github.com/softlayer/softlayer-object-storage-python',
    license='MIT',
    test_suite='tests',
    packages=find_packages(exclude=['tests']),
    install_requires=requirements,
    **extra
)
