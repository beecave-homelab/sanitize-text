"""Setup configuration for the sanitize-text package."""

from setuptools import setup, find_packages

setup(
    name="sanitize-text",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'sanitize_text': [
            'data/nl_entities/*.json',
            'data/en_entities/*.json',
        ],
    },
    install_requires=[
        "click>=8.0.0",
        "scrubadub>=2.0.0",
        "halo>=0.0.31",
    ],
    extras_require={
        "spacy": [
            "spacy>=3.0.0",
            "scrubadub-spacy>=0.4.0",
        ],
        "nltk": [
            "nltk>=3.6.0",
        ],
        "all": [
            "spacy>=3.0.0",
            "scrubadub-spacy>=0.4.0",
            "nltk>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sanitize-text=sanitize_text.cli.main:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for removing personally identifiable information (PII) from text",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/sanitize-text",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
) 