#!/usr/bin/python
from setuptools import setup, find_packages
import sys
from object_storage.consts import __version__

requirements = ['httplib2']
if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    requirements.append('simplejson')

# Python 3 conversion
extra_args = {}
if sys.version_info >= (3,):
    extra_args['use_2to3'] = True

setup(
    name='softlayer-object-storage',
    version=__version__,
    description='SoftLayer Object Storage client bindings for Python.',
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
    **extra_args
)
