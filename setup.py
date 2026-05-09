from setuptools import setup, find_packages
import platform

# Detectar sistema operativo para dependencias extras
is_windows = platform.system() == "Windows"

# Dependencias base
install_requires = [
    "psutil>=5.8.0",
]

# Dependencias extras por SO
extras_require = {
    "gpu": ["gputil>=1.4.0", "pyamdgpuinfo>=0.1.0"],
}

# Agregar dependencias específicas de Windows
if is_windows:
    extras_require["windows"] = ["wmi>=1.5.0", "pywin32>=300"]
    extras_require["full"] = ["gputil>=1.4.0", "wmi>=1.5.0", "pywin32>=300"]
else:
    extras_require["full"] = ["gputil>=1.4.0", "pyamdgpuinfo>=0.1.0"]
    extras_require["sensors"] = ["lm-sensors"]

setup(
    name="sysmonitorpro",
    version="1.0.0",
    author="George0884",
    author_email="george0884@github.com",  # Corregido
    description="Monitor de sistema avanzado para Windows/Linux con gráficos históricos, soporte multi-GPU y modo JSON",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    py_modules=["sysmonitorpro"],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "sysmonitorpro=sysmonitorpro:main",
            "sysmonitor=sysmonitorpro:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    keywords="system-monitor, windows, linux, gpu-monitor, performance, terminal, temperatures",
    url="https://github.com/george0884/sysmonitorpro",
    project_urls={
        "Bug Reports": "https://github.com/george0884/sysmonitorpro/issues",
        "Source": "https://github.com/george0884/sysmonitorpro",
        "Documentation": "https://github.com/george0884/sysmonitorpro#readme",
    },
)
