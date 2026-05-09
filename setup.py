from setuptools import setup, find_packages

setup(
    name="sysmonitorpro",
    version="1.0.0",
    author="George0884",  # ← Cambia "Tu Nombre" por tu usuario de GitHub
    author_email="tuemail@ejemplo.com",  # ← Opcional pero recomendado
    description="Monitor de sistema avanzado para Linux con gráficos históricos, soporte multi-GPU y modo JSON",
    long_description=open("README.md", encoding="utf-8").read(),  # ← Agregado: usa README como descripción larga
    long_description_content_type="text/markdown",  # ← Agregado: formato markdown
    py_modules=["sysmonitorpro"],
    python_requires=">=3.8",  # ← Agregado: versión mínima de Python
    install_requires=[
        "psutil>=5.8.0",
    ],
    extras_require={
        "gpu": ["gputil>=1.4.0", "pyamdgpuinfo>=0.1.0"],
    },
    entry_points={
        "console_scripts": [
            "sysmonitorpro=sysmonitorpro:main",  # ← Nota: el comando será 'sysmonitorpro'
            "sysmonitor=sysmonitorpro:main",     # ← Agregado: también crear 'sysmonitor' más corto
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    keywords="system-monitor, linux, gpu-monitor, performance, terminal",  # ← Agregado: palabras clave
    url="https://github.com/george0884/sysmonitorpro",  # ← Agregado: URL del repo
    project_urls={  # ← Agregado: enlaces adicionales
        "Bug Reports": "https://github.com/george0884/sysmonitorpro/issues",
        "Source": "https://github.com/george0884/sysmonitorpro",
    },
)
