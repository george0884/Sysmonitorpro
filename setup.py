from setuptools import setup, find_packages

setup(
    name="sysmonitorpro",
    version="1.0.0",
    author="Tu Nombre",
    description="Monitor de sistema avanzado para Linux",
    py_modules=["sysmonitorpro"],
    install_requires=[
        "psutil>=5.8.0",
    ],
    extras_require={
        "gpu": ["gputil>=1.4.0", "pyamdgpuinfo>=0.1.0"],
    },
    entry_points={
        "console_scripts": [
            "sysmonitorpro=sysmonitorpro:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
)
