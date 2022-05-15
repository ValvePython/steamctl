#!/usr/bin/env python

from setuptools import setup, find_packages
from codecs import open
from os import path
import sys

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
with open(path.join(here, 'steamctl/__init__.py'), encoding='utf-8') as f:
    __version__ = f.readline().split('"')[1]
    __author__ = f.readline().split('"')[1]

install_requires = [
    'steam[client]~=1.3',
    'appdirs',
    'argcomplete',
    'tqdm',
    'arrow',
    'pyqrcode',
    'vpk>=1.3.2',
    'beautifulsoup4',
]

setup(
    name='steamctl',
    version=__version__,
    description='Take control of Steam from your terminal',
    long_description=long_description,
    url='https://github.com/ValvePython/steamctl',
    author=__author__,
    author_email='rossen@rgp.io',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='steam steamctl steamid steamcommunity authenticator workshop',
    packages=['steamctl'] + ['steamctl.'+x for x in find_packages(where='steamctl')],
    entry_points={
        'console_scripts': ['steamctl = steamctl.__main__:main'],
    },
    python_requires='~=3.4',
    install_requires=install_requires,
    zip_safe=True,
)
