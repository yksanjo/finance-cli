"""Setup configuration for Finance CLI."""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="finance-cli",
    version="1.0.0",
    author="Finance CLI Team",
    description="A privacy-focused CLI tool for personal finance management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/finance-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "finance=finance_cli.cli:main",
        ],
    },
    keywords="finance cli personal-finance budget expenses tracking privacy",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/finance-cli/issues",
        "Source": "https://github.com/yourusername/finance-cli",
    },
)
