# Sanitize Text | A Sanitizer for PII

A powerful tool for detecting and sanitizing personally identifiable information (PII) in text, with support for both English and Dutch languages.

## Badges

![Python](https://img.shields.io/badge/Python-3.11-green)
![Version](https://img.shields.io/badge/version-0.2.1-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Versions

**Current version**: 0.2.1

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Supported Locales](#supported-locales)
  - [Available Detectors](#available-detectors)
  - [CLI Tool](#cli-tool)
  - [Handling binary/rich formats](#handling-binaryrich-formats)
  - [Web Interface](#web-interface)
  - [Entity Management](#entity-management)
- [License](#license)
- [Contributing](#contributing)

## System Requirements

- **Operating System**:
  - Tested on MacOS 15.1 (Macbook Pro M2)
  - Should work on Linux systems
- **Python**:
  - Python 3.11 required
  - Can be installed via Homebrew on MacOS: `brew install python@3.11`
- **Storage**:
  - Base installation stays under 100 MB and runs entirely on CPU
  - Optional extras (spaCy models, NLTK corpora) require additional space

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/beecave-homelab/sanitize-text.git
   cd sanitize-text
   ```

2. Create and activate a virtual environment:

   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -U pip
   pip install -r requirements.txt
   ```

4. (Optional) Install language extras when you need them:

   ```bash
   # Enable spaCy-powered entity detection
   pip install .[spacy]

   # Enable NLTK-powered detectors
   pip install .[nltk]
   ```

## Usage

### Supported Locales

The package supports two locales for PII detection and sanitization:

- **Dutch (nl_NL)**:
  - Specialized detection for Dutch names, organizations, and locations
  - Support for Dutch address formats and postal codes
  - Recognition of Dutch-specific organizational suffixes (B.V., N.V., etc.)
  - Dutch phone number formats

- **English (en_US)**:
  - Detection of English names, organizations, and locations using curated lists
  - US-format date of birth detection
  - Optional spaCy models for statistical NER when installed

### Available Detectors

The package includes both locale-specific and general-purpose detectors:

#### General Detectors (All Locales)

- **Email**: Detects email addresses in standard formats
- **Phone**: Identifies phone numbers in various formats
- **URL**: Detects web URLs, including domains and full paths
- **Markdown URL**: Specifically identifies URLs within Markdown link syntax
- **Private IP**: Detects private IP addresses (e.g., 192.168.x.x, 10.x.x.x)
- **Public IP**: Identifies public-facing IP addresses

#### Dutch (nl_NL) Specific Detectors

- **Location**: Dutch cities, provinces, and addresses
- **Organization**: Dutch company names and legal entities
- **Name**: Dutch personal names (first names, surnames, and combinations)
- **spaCy Entities** *(optional)*: Statistical NER when `sanitize-text[spacy]` is installed

#### English (en_US) Specific Detectors

- **Name**: English personal names (dictionary based)
- **Organization**: Common English-language organizations
- **Location**: Major US cities and regions
- **Date of Birth**: Various US date formats
- **spaCy Entities** *(optional)*: Statistical NER when `sanitize-text[spacy]` is installed

Each detector can be used individually or in combination using the `-d` flag in the CLI tool.

### CLI Tool

Run the CLI tool using the Python module syntax:

```bash
# Process text directly
python -m sanitize_text -t "Your text here" -l nl_NL

# Process from a file
python -m sanitize_text -i input.txt -o output.txt

# List available detectors
python -m sanitize_text --list-detectors

# Use specific detectors
python -m sanitize_text -i input.txt -d "email url name"

# Append to existing output
python -m sanitize_text -i input.txt -o output.txt -a
```

Available options:

- `-t, --text`: Input text to scrub for PII
- `-i, --input`: Path to input file containing text to scrub
- `-o, --output`: Path to output file (defaults to $PWD/output/scrubbed.txt)
- `-l, --locale`: Language/locale code (nl_NL or en_US)
- `-d, --detectors`: Space-separated list of specific detectors to use
- `-a, --append`: Append to existing output file
- `--list-detectors`: List all available detectors

### Handling binary/rich formats

Binary or rich document formats (e.g., PDF, DOC/DOCX, RTF, images) are not parsed natively. Convert or extract text first, then pass the resulting text to the CLI or Python API. Examples:

```bash
# PDF → text (requires pdftotext from poppler)
pdftotext input.pdf - | python -m sanitize_text

# DOCX → text (docx2txt)
docx2txt input.docx - | python -m sanitize_text

# RTF → text (pandoc)
pandoc input.rtf -t plain | python -m sanitize_text

# Image → text via OCR (tesseract)
tesseract image.png stdout | python -m sanitize_text
```

Notes:

- These commands stream extracted UTF-8 text to stdin; all content is treated as plain text.
- For structured files (CSV/JSON), sanitize-text processes raw text without field-aware parsing.

### Web Interface

Launch the web interface using:

```bash
python -m sanitize_text.webui
```

The web interface provides a user-friendly way to sanitize text and manage entities. Access it through your web browser at `http://localhost:5000` after starting the server.

### Entity Management

The project includes a utility for managing entities in the Dutch (nl_NL) locale. You can add new names, organizations, or cities using the add_entity module:

```bash
# Add a new city
python -m sanitize_text.add_entity -c "Amsterdam"

# Add a new name
python -m sanitize_text.add_entity -n "John Smith"

# Add a new organization
python -m sanitize_text.add_entity -o "Example B.V."

# Add multiple entities at once
python -m sanitize_text.add_entity -c "Amsterdam" -n "John Smith" -o "Example B.V."
```

Available options:

- `-c, --city`: Add a new city
- `-n, --name`: Add a new person name
- `-o, --organization`: Add a new organization
- `-h, --help`: Show help message

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE) for more information.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
