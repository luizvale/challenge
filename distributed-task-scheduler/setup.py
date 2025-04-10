from setuptools import setup, find_packages

setup(
    name="distributed-task-scheduler",
    version="0.1.0",
    description="Python-based distributed task scheduler supporting priority queues, dependencies, and monitoring.",
    author="ArionKoder",
    author_email="info@arionkoder.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="task scheduling, distributed systems, task queues",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
    ],
    extras_require={
        "dev": ["pytest", "pytest-cov", "black", "isort", "mypy", "flake8"],
        "test": ["pytest", "pytest-cov"],
    },
    entry_points={
        "console_scripts": [
            "task-scheduler-demo=examples.task_scheduler_example:main",
        ],
    },
)
