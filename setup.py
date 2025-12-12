"""Setup script for PRTG CLI Tool."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="prtg-tool",
    version="0.2.0",
    description="Command-line tool for PRTG Network Monitor API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PRTG Tool Contributors",
    python_requires=">=3.14",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "click",
        "requests",
        "pydantic>=2.12.0,<3.0",
        "python-dotenv",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "prtg=prtg.cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.14",
    ],
)
