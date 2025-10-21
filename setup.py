"""
Setup configuration for birdhaus_data_pipeline package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = []

setup(
    name="birdhaus_data_pipeline",
    version="0.1.0",
    description="Data pipeline for extracting and transforming Wix Events & Tickets data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Birdhaus Shibari Studio",
    author_email="",
    url="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.32.0",
        "pyrate-limiter>=3.9.0",
        "tenacity>=8.2.0",
        "pandas>=2.0.0",
        "numpy>=2.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "responses>=0.23.0",
            "mypy>=1.4.0",
            "types-requests>=2.31.0",
            "types-PyYAML>=6.0.0",
        ],
        "logging": [
            "structlog>=23.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "wix-pull-all=scripts.pull_all:main",
            "wix-pull-incremental=scripts.pull_incremental:main",
            "wix-backfill=scripts.backfill_historical:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="wix api data pipeline etl events tickets",
    project_urls={
        "Documentation": "",
        "Source": "",
        "Tracker": "",
    },
)
