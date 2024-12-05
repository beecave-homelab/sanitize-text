# PyScrub WebUI

A modern web interface and command-line tool for anonymizing PII (Personally Identifiable Information) in text using the `scrubadub` package. Supports both English and Dutch text processing with advanced entity detection.

## Features

- Clean, modern web interface
- Command-line interface for batch processing
- Multilingual support (English and Dutch)
- Advanced PII detection using spaCy models
- Custom entity list support for Dutch language
- Hashed PII replacements for consistent anonymization
- Real-time text processing
- Copy to clipboard functionality
- Responsive design for all devices
- Simple and intuitive user experience
- Automatic downloading of required language models

## Installation

### System Requirements

- Tested on MacOS 15.1.1 with Apple Silicon chip (arm64)
- Tested with Python version 3.11

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pyscrub-webui.git
cd pyscrub-webui
```

2. Create a virtual environment:
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

### Web Interface

1. Start the application:
```bash
chmod +x run.py
./run.py
```
The script will automatically download all required NLTK and spaCy models on first run.

2. Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

3. Enter text containing PII in the input field
4. Select your preferred language mode:
   - Both (NL + EN): Process text with both Dutch and English models
   - Dutch (NL): Process text with Dutch model only
   - English (EN): Process text with English model only
5. Click "Process Text" to anonymize the content
6. Use the "Copy to Clipboard" button to copy the processed text

### Command Line Interface

The project includes a CLI tool (`pyscrub-cli.py`) for processing text files or direct input:

```bash
chmod +x pyscrub-cli.py
./pyscrub-cli.py [OPTIONS]
```

Options:
- `-t, --text TEXT`: Input text to scrub for PII
- `-i, --input PATH`: Path to input file containing text to scrub
- `-o, --output PATH`: Path to output file (defaults to $PWD/output/scrubbed.txt)
- `-l, --locale [nl_NL|en_US]`: Locale for text processing

Examples:

1. Process text directly:
```bash
./pyscrub-cli.py --text "John Doe lives in Amsterdam"
```

2. Process a file:
```bash
./pyscrub-cli.py --input input.txt --output scrubbed.txt
```

3. Process piped input:
```bash
echo "John Doe lives in Amsterdam" | ./pyscrub-cli.py
pbpaste | ./pyscrub-cli.py
```

4. Process with specific locale:
```bash
./pyscrub-cli.py --text "Jan Jansen woont in Amsterdam" --locale nl_NL
```

## Custom Entity Lists (Dutch)

The application supports custom entity lists for Dutch language processing. Place your entity lists in the `nl_entities` directory with `.txt` files:

```
nl_entities/
├── names.txt          # Personal names
├── cities.txt         # City names
├── organizations.txt  # Organization names
└── ...               # Other entity types
```

Each file should contain one entity per line. The filename (without extension) determines the entity type in the output.

## Development

The application is built with:
- Flask (Backend framework)
- scrubadub (Text anonymization)
- scrubadub-spacy (Advanced entity detection)
- spaCy (NLP processing)
- Modern HTML/CSS/JavaScript (Frontend)

### Project Structure

```
pyscrub-webui/
├── scrub_webui/
│   ├── __init__.py      # Flask app initialization
│   ├── routes.py        # Application routes and PII processing logic
│   ├── templates/       # HTML templates
│   └── static/          # CSS and other static files
├── nl_entities/         # Custom Dutch entity lists
├── requirements.txt     # Project dependencies
├── run.py              # Application entry point with automatic model downloading
└── pyscrub-cli.py      # Command-line interface for text processing
```

### PII Detection Features

The application detects various types of PII:

#### Universal Detection
- Email addresses
- Phone numbers
- URLs
- Twitter handles
- Skype usernames

#### English-Specific Detection
- Names (using spaCy NER)
- Dates of birth
- Organizations
- Locations

#### Dutch-Specific Detection
- Names (using spaCy NER and custom lists)
- Organizations (using spaCy NER and custom lists)
- Locations (using spaCy NER and custom lists)
- Custom entities from entity lists

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 