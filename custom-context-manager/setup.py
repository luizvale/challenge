from setuptools import setup, find_packages

setup(
    name="custom-context-manager",
    version="0.1.0",
    description="Robust context manager for managing external resources with detailed logging.",
    author="ArionKoder",
    author_email="info@arionkoder.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="context manager, resource management, logging",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies required

    ],
    extras_require={
        "dev": ["pytest", "pytest-cov", "black", "isort", "mypy", "flake8"],
        "test": ["pytest", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "resource-manager-demo=examples.resource_manager_example:main",
        ],
    },
)
