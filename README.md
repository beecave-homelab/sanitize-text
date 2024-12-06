# Text PII Sanitizer

A powerful tool for detecting and sanitizing personally identifiable information (PII) in text, with support for both English and Dutch languages. Available as both a command-line interface and a web application.

## Versions

**Current version**: 0.1.0

## Table of Contents

- [Versions](#versions)
- [Badges](#badges)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Contributing](#contributing)

## Badges

![Python](https://img.shields.io/badge/Python-3.11-green)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd sanitize-text
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

Alternatively, use Docker:
```bash
# Using Docker
docker build -t pii-sanitizer .
docker run -p 5000:5000 pii-sanitizer

# Or using Docker Compose
docker-compose up
```

## Usage

### Command Line Interface

```bash
# Process text directly
python sanitize-cli.py --text "Your text here" --locale nl_NL

# Process from a file
python sanitize-cli.py --input input.txt --output output.txt

# List available detectors
python sanitize-cli.py --list-detectors
```

### Web Interface

1. Start the web server:
   ```bash
   python run.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Enter text in the web interface and choose your preferred language settings

Key Features:
- Multi-language Support (English and Dutch)
- Comprehensive PII Detection (emails, phone numbers, names, etc.)
- Customizable Output Options
- Support for Custom Entity Lists

## License

This project is licensed under the MIT license. See [LICENSE](LICENSE) for more information.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. 
