#!venv/bin/python3

import os
import sys
import click
import scrubadub
import scrubadub_spacy
from scrubadub.filth import Filth
import spacy
from halo import Halo
import warnings
import nltk

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
        # Get all .txt files from nl_entities directory
        entity_dir = 'nl_entities'
        if not os.path.exists(entity_dir):
            click.echo(f"Warning: Directory {entity_dir} does not exist", err=True)
            return known_pii
            
        for filename in os.listdir(entity_dir):
            if not filename.endswith('.txt'):
                continue
                
            # Map filename to valid filth type
            filename_without_ext = os.path.splitext(filename)[0].lower()
            # Map common name-related files to 'name' filth type
            if any(name_type in filename_without_ext for name_type in ['names', 'male_names', 'female_names']):
                filth_type = 'name'
            else:
                filth_type = filename_without_ext
            
            try:
                filepath = os.path.join(entity_dir, filename)
                with open(filepath, 'r') as f:
                    entities = [line.strip() for line in f if line.strip()]
                    for entity in entities:
                        known_pii.append({
                            'match': entity,
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

def get_available_detectors():
    """Returns a list of available detector names."""
    base_detectors = ['email', 'phone', 'url', 'twitter', 'skype']
    spacy_detectors = ['name', 'organisation', 'location']
    other_detectors = ['date_of_birth', 'known_pii']
    return base_detectors + spacy_detectors + other_detectors

def setup_scrubber(locale, selected_detectors=None):
    """Helper function to set up a scrubber with appropriate detectors and post-processors."""
    detector_list = []
    available_detectors = get_available_detectors()
    
    if selected_detectors:
        selected_detectors = [d.lower() for d in selected_detectors]
        invalid_detectors = [d for d in selected_detectors if d not in available_detectors]
        if invalid_detectors:
            click.echo(f"Warning: Invalid detector(s): {', '.join(invalid_detectors)}", err=True)
    
    # Add universal detectors with unique names if they're selected or if no specific detectors were requested
    if not selected_detectors or any(d in selected_detectors for d in ['email', 'phone', 'url', 'twitter', 'skype']):
        base_detectors = {
            'email': scrubadub.detectors.EmailDetector,
            'phone': scrubadub.detectors.PhoneDetector,
            'url': scrubadub.detectors.UrlDetector,
            'twitter': scrubadub.detectors.TwitterDetector,
            'skype': scrubadub.detectors.SkypeDetector
        }
        
        for detector_name, detector_class in base_detectors.items():
            if not selected_detectors or detector_name in selected_detectors:
                detector_list.append(detector_class(name=f'{detector_name}_{locale}'))
    
    # Configure SpacyEntityDetector with the correct model for each locale
    if locale == 'en_US':
        if not selected_detectors or any(d in selected_detectors for d in ['name', 'organisation', 'location']):
            detector_list.append(
                scrubadub_spacy.detectors.SpacyEntityDetector(
                    model='en_core_web_sm',
                    name='spacy_en'
                )
            )
        if not selected_detectors or 'date_of_birth' in selected_detectors:
            detector_list.append(scrubadub.detectors.DateOfBirthDetector(name='dob_en'))
            
    elif locale == 'nl_NL':
        if not selected_detectors or any(d in selected_detectors for d in ['name', 'organisation', 'location']):
            detector_list.append(
                scrubadub_spacy.detectors.SpacyEntityDetector(
                    model='nl_core_news_sm',
                    name='spacy_nl'
                )
            )
        # Load and add known PII terms from entity lists only for Dutch
        if not selected_detectors or 'known_pii' in selected_detectors:
            known_pii = load_entity_lists()
            detector_list.append(
                KnownFilthDetector(
                    known_filth_items=known_pii,
                    name=f'known_pii_{locale}'
                )
            )
    
    # Custom post-processor to add hash to PII replacements
    class HashedPIIReplacer(scrubadub.post_processors.PostProcessor):
        name = 'hashed_pii_replacer'
        def process_filth(self, filth_list):
            for filth in filth_list:
                filth_type = filth.type.upper()
                filth.replacement_string = f"{filth_type}-{hash(filth.text) % 10000:04d}"
            return filth_list
    
    # Initialize scrubber with selected detectors and custom post-processors
    scrubber = scrubadub.Scrubber(
        locale=locale,
        detector_list=detector_list,
        post_processor_list=[
            HashedPIIReplacer(),
            scrubadub.post_processors.PrefixSuffixReplacer(
                prefix='{{',
                suffix='}}'
            )
        ]
    )
    
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

class KnownFilthDetector(scrubadub.detectors.Detector):
    name = 'known_filth_detector'

    def __init__(self, known_filth_items, **kwargs):
        self.known_filth_items = known_filth_items
        super().__init__(**kwargs)

    def iter_filth(self, text, document_name=None):
        for item in self.known_filth_items:
            match = item['match']
            pos = 0
            # Keep searching for matches until we reach the end of text
            while True:
                start = text.find(match, pos)
                if start == -1:  # No more matches
                    break
                yield Filth(
                    beg=start,
                    end=start + len(match),
                    text=match,
                    detector_name=self.name,
                    filth_type=item['filth_type']
                )
                pos = start + 1  # Move position forward to find next occurrence

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
def scrub_pii(text, input, output, locale, detectors, list_detectors):
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
        click.echo("Available detectors:")
        for detector in get_available_detectors():
            click.echo(f"- {detector}")
        return

    # Suppress specific warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
    warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

    # Parse selected detectors if provided
    selected_detectors = detectors.split() if detectors else None

    # Determine input text
    if input:
        with open(input, "r") as input_file:
            input_text = input_file.read()
    elif text:
        input_text = text
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        click.echo("Error: No input provided. Use --text, --input, or pipe input.", err=True)
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