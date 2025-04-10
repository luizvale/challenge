"""
Setup script for the Lazy Evaluation package.
"""
from setuptools import setup, find_packages

setup(
    name="lazy-collection",
    version="0.1.0",
    description="Robust and efficient lazy collection library for processing large datasets",
    author="ArionKoder",
    author_email="info@arionkoder.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="lazy evaluation, data processing, generators, memory efficient",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "memory_profiler>=0.61.0",
        "matplotlib>=3.5.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=23.0.0",
            "isort>=5.10.1",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "run-bigdata-pipeline=examples.big_data_pipeline_example:main",
            "run-csv-processing=examples.large_csv_processing:main",
            "run-caching-demo=examples.caching_and_memoization:main",
        ],
    },
)
