from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='jaws',
    version='0.1',
    description='metadata extraction toolkit',
    author='Andrey Popp',
    author_email='8mayday@gmail.com',
    license='BSD',
    packages=['jaws', 'justext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    package_data={'justext': ['stoplists/*.txt']},
    test_suite='tests',
    entry_points="""
    [console_scripts]
    """)
