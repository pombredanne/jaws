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
    install_requires=[
        'PIL>=1.1.7',
        'WebOb>=1.2.3',
        'chardet>=2.1.1',
        'docopt>=0.5.0',
        'lxml>=3.0',
        'python-dateutil>=2.1',
        'routr>=0.6',
        'routr-schema>=0.1',
        'schemify>=0.1',
        ],
    package_data={'justext': ['stoplists/*.txt']},
    test_suite='tests',
    entry_points="""
    [console_scripts]
    jaws = jaws:main
    """)
