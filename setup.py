#!/usr/bin/python
from setuptools import setup, find_packages
from object_storage import __version__

name = 'softlayer-object-storage'
version = __version__
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
    packages=find_packages(exclude=['test', 'ez_setup', 'examples']),
    test_suite='tests',
    install_requires=['httplib2'],
    setup_requires=['mock'],
    namespace_packages=[]
)
