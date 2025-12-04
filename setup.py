#!/usr/bin/env python
"""Setup script for DarkReconX distribution."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="darkreconx",
    version="0.1.0",
    author="DarkReconX Contributors",
    description="Modular OSINT reconnaissance framework with Tor support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GeoAziz/DarkReconX",
    license="MIT",
    packages=find_packages(exclude=["tests", "docs", "examples"]),
    python_requires=">=3.11",
    install_requires=[
        "requests==2.31.0",
        "PySocks==1.7.1",
        "stem==1.8.2",
        "httpx==0.27.0",
        "typer==0.12.3",
        "rich==13.7.0",
        "pyfiglet==1.0.2",
        "pyyaml==6.0.1",
        "python-whois==0.9.4",
        "dnspython==2.6.1",
        "python-dotenv==1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest==8.0.0",
            "pytest-asyncio==0.23.2",
            "pytest-cov==4.1.0",
            "black==24.1.1",
            "isort==5.13.2",
            "flake8==6.1.0",
            "mypy==1.8.0",
            "pre-commit==3.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "darkreconx=cli.main:app",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet",
        "Topic :: System :: Monitoring",
        "Topic :: Security",
    ],
    keywords="osint reconnaissance darkweb tor security",
    project_urls={
        "Bug Reports": "https://github.com/GeoAziz/DarkReconX/issues",
        "Documentation": "https://github.com/GeoAziz/DarkReconX/README.md",
        "Source": "https://github.com/GeoAziz/DarkReconX",
    },
)
