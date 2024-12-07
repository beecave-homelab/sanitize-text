#!venv/bin/python3

import os
import sys
import click
import scrubadub
import scrubadub_spacy
from scrubadub.detectors.email import EmailDetector
from scrubadub.detectors.phone import PhoneDetector
import spacy
from halo import Halo
import warnings
import nltk
from typing import ClassVar
from scrubadub.detectors import register_detector
from custom_detectors.private_ip_detector import PrivateIPDetector
from custom_detectors.public_ip_detector import PublicIPDetector
from custom_detectors.url_detector import BareDomainDetector
from custom_detectors.dutch_location_detector import DutchLocationDetector
from custom_detectors.dutch_organization_detector import DutchOrganizationDetector
from custom_detectors.dutch_name_detector import DutchNameDetector
from custom_detectors.markdown_url_detector import MarkdownUrlDetector

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    click.echo(f"Warning: Could not download NLTK data: {str(e)}", err=True)

def load_entity_lists():
    """Load entity lists from nl_entities directory."""
    known_pii = []
    
    try:
        entity_dir = 'nl_entities'
        if not os.path.exists(entity_dir):
            click.echo(f"Warning: Directory {entity_dir} does not exist", err=True)
            return known_pii
            
        json_files = {
            'cities.json': 'location',
            'organizations.json': 'organization',
            'names.json': 'name'
        }
        
        import json
        for filename, filth_type in json_files.items():
            try:
                filepath = os.path.join(entity_dir, filename)
                if not os.path.exists(filepath):
                    continue
                    
                with open(filepath, 'r') as f:
                    entities = json.load(f)
                    for entity in entities:
                        known_pii.append({
                            'match': entity['match'],
                            'filth_type': filth_type,
                            'ignore_case': True
                        })
                click.echo(f"Loaded {len(entities)} entities from {filename}")
            except Exception as e:
                click.echo(f"Warning: Could not load entity list {filename}: {str(e)}", err=True)
    except Exception as e:
        click.echo(f"Warning: Error loading entity lists: {str(e)}", err=True)
    
    return known_pii

def add_detector_safely(scrubber, detector_class, locale=None):
    """Helper function to safely add a detector to the scrubber."""
    try:
        scrubber.add_detector(detector_class)
    except Exception as e:
        click.echo(f"Warning: Could not add detector {detector_class.__name__}: {str(e)}", err=True)

def get_available_detectors(locale=None):
    """Returns a list of available detector names for the given locale."""
    # Generic detectors available for all locales
    generic_detectors = {
        'email': 'Detect email addresses (e.g., user@example.com)',
        'phone': 'Detect phone numbers',
        'url': 'Detect URLs (bare domains, www prefixes, http(s), complex paths, query parameters)',
        'markdown_url': 'Detect URLs within Markdown links [text](url)',
        'private_ip': 'Detect private IP addresses (192.168.x.x, 10.0.x.x, 172.16-31.x.x)',
        'public_ip': 'Detect public IP addresses (any non-private IP)'
    }
    
    # Locale-specific detectors
    locale_detectors = {
        'nl_NL': {
            'location': 'Detect Dutch locations (cities)',
            'organization': 'Detect Dutch organization names',
            'name': 'Detect Dutch person names'
        },
        'en_US': {
            'name': 'Detect person names (English)',
            'organization': 'Detect organization names (English)',
            'location': 'Detect locations (English)',
            'date_of_birth': 'Detect dates of birth'
        }
    }
    
    if locale:
        # Combine generic detectors with locale-specific ones
        return {**generic_detectors, **locale_detectors.get(locale, {})}
    return locale_detectors

class HashedPIIReplacer(scrubadub.post_processors.PostProcessor):
    name = 'hashed_pii_replacer'
    def process_filth(self, filth_list):
        for filth in filth_list:
            filth.replacement_string = f"{{{{{filth.type}-{hash(filth.text) % 10000:04d}}}}}"
        return filth_list

def setup_scrubber(locale, selected_detectors=None):
    """Helper function to set up a scrubber with appropriate detectors and post-processors."""
    detector_list = []
    available_detectors = get_available_detectors(locale).keys()
    
    if selected_detectors:
        selected_detectors = [d.lower() for d in selected_detectors]
        invalid_detectors = [d for d in selected_detectors if d not in available_detectors]
        if invalid_detectors:
            click.echo(f"Warning: Invalid detector(s) for locale {locale}: {', '.join(invalid_detectors)}", err=True)
    
    # Add generic detectors that work for all locales if selected or if no specific detectors are specified
    generic_detectors = {
        'email': EmailDetector,
        'phone': PhoneDetector,
        'url': BareDomainDetector,
        'markdown_url': MarkdownUrlDetector,
        'private_ip': PrivateIPDetector,
        'public_ip': PublicIPDetector
    }
    
    # Configure detectors with proper locale settings
    for detector_name, detector_class in generic_detectors.items():
        if not selected_detectors or detector_name in selected_detectors:
            try:
                if detector_name == 'email':
                    detector = detector_class(locale=locale)
                else:
                    detector = detector_class()
                detector_list.append(detector)
            except Exception as e:
                click.echo(f"Warning: Could not add detector {detector_name}: {str(e)}", err=True)
    
    # Configure locale-specific detectors
    if locale == 'nl_NL':
        dutch_detectors = {
            'location': DutchLocationDetector,
            'organization': DutchOrganizationDetector,
            'name': DutchNameDetector
        }
        
        if not selected_detectors:
            # Add all Dutch detectors if none specified
            for detector_class in dutch_detectors.values():
                detector_list.append(detector_class())
        else:
            # Only add requested Dutch detectors
            for detector_name, detector_class in dutch_detectors.items():
                if detector_name in selected_detectors:
                    detector_list.append(detector_class())
    
    # Initialize scrubber with selected detectors and custom post-processors
    scrubber = scrubadub.Scrubber(
        locale=locale,
        detector_list=detector_list,
        post_processor_list=[
            HashedPIIReplacer(),
        ]
    )
    
    # Explicitly disable all other detectors
    scrubber.detectors = {d.name: d for d in detector_list}
    
    return scrubber

def load_spacy_model(model_name):
    """Helper function to safely load spaCy model."""
    try:
        return spacy.load(model_name)
    except OSError:
        try:
            click.echo(f"Downloading language model {model_name}")
            spacy.cli.download(model_name)
            return spacy.load(model_name)
        except Exception as e:
            click.echo(f"Warning: Could not load or download model {model_name}: {str(e)}", err=True)
            return None

@click.command()
@click.option(
    "--text",
    "-t",
    type=str,
    help="Input text to scrub for PII.",
    default=None,
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Path to input file containing text to scrub.",
    default=None,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    help="Path to output file where scrubbed text will be saved. Defaults to $PWD/output/scrubbed.txt",
    default=None,
)
@click.option(
    "--append",
    "-a",
    is_flag=True,
    help="If set, use the output file as input when it exists, ignoring the input file.",
    default=False,
)
@click.option(
    "--locale",
    "-l",
    type=click.Choice(['nl_NL', 'en_US']),
    help="Locale for text processing (nl_NL or en_US)",
    default=None
)
@click.option(
    "--detectors",
    "-d",
    help="Space-separated list of specific detectors to use (e.g., 'url name organisation')",
    default=None
)
@click.option(
    "--list-detectors",
    "-ld",
    is_flag=True,
    help="List all available detectors",
)
def scrub_pii(text, input, output, locale, detectors, list_detectors, append):
    """
    Remove personally identifiable information (PII) from text.
    
    Available detectors include:
    - email: Detect email addresses
    - phone: Detect phone numbers
    - url: Detect URLs
    - twitter: Detect Twitter handles
    - skype: Detect Skype usernames
    - name: Detect person names
    - organisation: Detect organization names
    - location: Detect location names
    - date_of_birth: Detect dates of birth
    - known_pii: Detect known PII from custom lists (NL only)
    """
    # If --list-detectors is used, show available detectors and exit
    if list_detectors:
        detectors_by_locale = get_available_detectors()
        generic_detectors = {
            'email': 'Detect email addresses',
            'phone': 'Detect phone numbers',
            'url': 'Detect URLs',
            'private_ip': 'Detect private IP addresses',
            'public_ip': 'Detect public IP addresses'
        }
        
        click.echo("Available detectors:\n")
        click.echo("Generic detectors (available for all locales):")
        for detector, description in generic_detectors.items():
            click.echo(f"  - {detector:<15} {description}")
        click.echo()
        
        click.echo("Locale-specific detectors:")
        for loc, detector_dict in detectors_by_locale.items():
            click.echo(f"\n{loc}:")
            for detector, description in detector_dict.items():
                click.echo(f"  - {detector:<15} {description}")
        click.echo()
        return

    # Suppress specific warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
    warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

    # Parse selected detectors if provided
    selected_detectors = detectors.split() if detectors else None

    # Determine input text
    if append and output and os.path.exists(output):
        with open(output, "r") as output_file:
            input_text = output_file.read()
    elif input:
        with open(input, "r") as input_file:
            input_text = input_file.read()
    elif text:
        input_text = text
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        click.echo("Error: No input provided. Use --text, --input, or pipe input.", err=True)
        sys.exit(1)

    # Validate append mode requirements
    if append and not output:
        click.echo("Error: --append/-a requires --output/-o to be specified.", err=True)
        sys.exit(1)

    # Set up spinner
    spinner = Halo(text="Scrubbing PII", spinner="dots")
    spinner.start()

    try:
        scrubbed_texts = []
        
        # Process with both languages if no specific locale is provided
        locales_to_process = ['en_US', 'nl_NL'] if locale is None else [locale]
        
        for current_locale in locales_to_process:
            try:
                # Load appropriate language model
                lang_code = current_locale.split('_')[0]
                model_name = "en_core_web_sm" if lang_code == "en" else "nl_core_news_sm"
                
                nlp = load_spacy_model(model_name)
                if nlp is None:
                    click.echo(f"Skipping locale {current_locale} due to missing language model")
                    continue
                
                # Process the input text
                doc = nlp(input_text)
                
                # Setup and run scrubber with selected detectors
                scrubber = setup_scrubber(current_locale, selected_detectors)
                scrubbed_text = scrubber.clean(input_text)
                scrubbed_texts.append(f"Results for {current_locale}:\n{scrubbed_text}")
                
            except Exception as e:
                click.echo(f"Warning: Processing failed for locale {current_locale}: {str(e)}", err=True)
                continue
        
        if not scrubbed_texts:
            raise Exception("All processing attempts failed")
            
        # Combine results
        scrubbed_text = "\n\n".join(scrubbed_texts)

    except Exception as e:
        spinner.fail("Scrubbing failed")
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    else:
        spinner.succeed("Scrubbing completed")

    # Handle output
    if text:
        # Print scrubbed text to terminal when --text is used
        click.echo(scrubbed_text)
    else:
        if output is None:
            # Use default output directory and file
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            output = os.path.join(output_dir, "scrubbed.txt")
        
        with open(output, "w") as output_file:
            output_file.write(scrubbed_text)
        click.echo(f"Scrubbed text saved to {output}")


if __name__ == "__main__":
    scrub_pii()
