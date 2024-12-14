# Sanitize Text | A Sanitizer for PII

A powerful tool for detecting and sanitizing personally identifiable information (PII) in text, with support for both English and Dutch languages.

## Badges

![Python](https://img.shields.io/badge/Python-3.11-green)
![Version](https://img.shields.io/badge/version-0.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Versions

**Current version**: 0.2.0

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Tool](#cli-tool)
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

### Web Interface

Launch the web interface using:

```bash
python -m sanitize_text.webui
```

The web interface provides a user-friendly way to sanitize text and manage entities. Access it through your web browser at `http://localhost:5000` after starting the server.

### Entity Management

The project includes a utility script for managing entities in the Dutch (nl_NL) locale. You can add new names, organizations, or cities using the `add_entity.py` script:

```bash
# Add a new city
python -m sanitize_text.utils.add_entity -c "Amsterdam"

# Add a new name
python -m sanitize_text.utils.add_entity -n "John Smith"

# Add a new organization
python -m sanitize_text.utils.add_entity -o "Example B.V."

# Add multiple entities at once
python -m sanitize_text.utils.add_entity -c "Amsterdam" -n "John Smith" -o "Example B.V."
```

Available options:

- `-c, --city`: Add a new city
- `-n, --name`: Add a new person name
- `-o, --organization`: Add a new organization
- `-h, --help`: Show help message

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
