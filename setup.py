#!/usr/bin/env python3
"""Instalación con pip:  pip install .   (crea el comando 'sysmonitor')"""
from setuptools import setup

setup(
    name="sysmonitorpro",
    version="2.0.0",
    description="Monitor de sistema avanzado para Windows/Linux",
    license="GPL-3.0",
    py_modules=["sysmonitorpro"],
    python_requires=">=3.7",
    install_requires=[
        "psutil>=5.8.0",
        'wmi>=1.5.0; platform_system == "Windows"',
        'pywin32>=300; platform_system == "Windows"',
    ],
    entry_points={"console_scripts": ["sysmonitor=sysmonitorpro:main"]},
)
