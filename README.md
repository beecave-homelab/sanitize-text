# Text PII Sanitizer

A powerful tool for detecting and sanitizing personally identifiable information (PII) in text, with support for both English and Dutch languages.

## Badges

![Python](https://img.shields.io/badge/Python-3.11-green)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Versions

**Current version**: 0.1.0

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
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
  - Approximately 1GB of free storage required for language models and dependencies

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

## Usage

### Command Line Interface

```bash
# Process text directly
python sanitize-cli.py -t "Your text here" -l nl_NL

# Process from a file
python sanitize-cli.py -i input.txt -o output.txt

# List available detectors
python sanitize-cli.py --list-detectors

# Use specific detectors
python sanitize-cli.py -i input.txt -d "email url name"

# Append to existing output
python sanitize-cli.py -i input.txt -o output.txt -a
```

Available options:

- `-t, --text`: Input text to scrub for PII
- `-i, --input`: Path to input file containing text to scrub
- `-o, --output`: Path to output file (defaults to $PWD/output/scrubbed.txt)
- `-l, --locale`: Language/locale code (nl_NL or en_US)
- `-d, --detectors`: Space-separated list of specific detectors to use
- `-a, --append`: Append to existing output file
- `--list-detectors`: List all available detectors

Supported Detectors:

- Generic (all locales):
  - email: Detect email addresses
  - phone: Detect phone numbers
  - url: Detect URLs (domains, paths, etc.)
  - markdown_url: Detect URLs in Markdown links
  - private_ip: Detect private IP addresses
  - public_ip: Detect public IP addresses

- Dutch (nl_NL):
  - location: Dutch locations/cities
  - organization: Dutch organization names
  - name: Dutch person names

- English (en_US):
  - name: English person names
  - organization: English organization names
  - location: English locations
  - date_of_birth: Dates of birth

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE) for more information.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
