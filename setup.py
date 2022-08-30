"""
Install with: python3 setup.py install
Develop with: python3 setup.py develop
Make it available on PIP with:
    python3 setup.py sdist
    pip3 install twine
    twine upload dist/*
"""
from setuptools import find_packages, setup

setup(
    name='netdoc',
    version='0.9.3',
    description='Network Documentation plugin for NetBox',
    url='https://github.com/dainok/netdoc',
    author='Andrea Dainese',
    author_email='andrea.dainese@pm.me',
    license='GNU v3.0',
    install_requires=['python-slugify', 'nornir==3.3.0', 'nornir_utils==0.2.0', 'nornir_netmiko==0.1.2', 'ipaddress', 'macaddress', 'ouilookup'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
    ],
    project_urls={
        'Source': 'https://github.com/dainok/netdoc',
    },
)
