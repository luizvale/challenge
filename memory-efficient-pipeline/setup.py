"""
Setup script for the memory-efficient data pipeline package.
"""
from setuptools import setup, find_packages

setup(
    name="memory-efficient-pipeline",
    version="0.1.0",
    description="Memory-efficient data processing pipeline",
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
    ],
    keywords="data processing, pipeline, memory efficient, generators",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "psutil>=5.9.0",  # For memory monitoring
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.3.0",
            "isort>=5.10.1",
            "mypy>=0.950",
            "flake8>=4.0.1",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "run-pipeline=examples.example_pipeline:main",
        ],
    },
)