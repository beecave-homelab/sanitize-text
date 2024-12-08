#!venv/bin/python3
"""Web routes and API endpoints for the text sanitization web interface.

This module provides the Flask routes and supporting functions for the web interface,
including text processing endpoints and scrubber configuration.
"""

import os
from flask import request, render_template, jsonify
import scrubadub
import scrubadub_spacy
import spacy
from scrubadub.filth import Filth
from sanitize_text.utils.detectors import (
    BareDomainDetector,
    MarkdownUrlDetector,
    PrivateIPDetector,
    PublicIPDetector,
    DutchLocationDetector,
    DutchOrganizationDetector,
    DutchNameDetector
)

def load_spacy_model(model_name: str) -> spacy.language.Language:
    """Load a spaCy language model, downloading it if necessary.
    
    Args:
        model_name: Name of the spaCy model to load (e.g., 'en_core_web_sm')
        
    Returns:
        The loaded spaCy model or None if loading fails
    """
    try:
        return spacy.load(model_name)
    except OSError:
        try:
            spacy.cli.download(model_name)
            return spacy.load(model_name)
        except Exception as e:
            print(f"Warning: Could not load or download model {model_name}: {str(e)}")
            return None

def load_entity_lists():
    """Load entity lists from nl_entities directory."""
    known_pii = []
    try:
        entity_dir = 'nl_entities'
        if not os.path.exists(entity_dir):
            print(f"Warning: Directory {entity_dir} does not exist")
            return known_pii
            
        for filename in os.listdir(entity_dir):
            if not filename.endswith('.txt'):
                continue
                
            filename_without_ext = os.path.splitext(filename)[0].lower()
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
            except Exception as e:
                print(f"Warning: Could not load entity list {filename}: {str(e)}")
    except Exception as e:
        print(f"Warning: Error loading entity lists: {str(e)}")
    
    return known_pii

class KnownFilthDetector(scrubadub.detectors.Detector):
    """Detector for known PII items loaded from entity lists.
    
    This detector uses predefined lists of entities (names, locations, etc.)
    to identify PII in text. It supports case-insensitive matching and
    different types of filth based on the entity lists.
    """
    name = 'known_filth_detector'

    def __init__(self, known_filth_items, **kwargs):
        """Initialize the detector with a list of known PII items.
        
        Args:
            known_filth_items: List of dictionaries containing PII items and their types
            **kwargs: Additional arguments passed to the parent Detector class
        """
        self.known_filth_items = known_filth_items
        super().__init__(**kwargs)

    def iter_filth(self, text, document_name=None):
        """Iterate through text to find matches from the known filth items.
        
        Args:
            text: The text to search for PII
            document_name: Optional name of the document being processed
            
        Yields:
            Filth objects for each PII match found
        """
        for item in self.known_filth_items:
            match = item['match']
            pos = 0
            while True:
                start = text.find(match, pos)
                if start == -1:
                    break
                yield Filth(
                    beg=start,
                    end=start + len(match),
                    text=match,
                    detector_name=self.name,
                    filth_type=item['filth_type']
                )
                pos = start + 1

class HashedPIIReplacer(scrubadub.post_processors.PostProcessor):
    """Post-processor that replaces PII with hashed identifiers.
    
    This processor takes detected PII and replaces it with a combination
    of the PII type and a hash of the original text, making it traceable
    while maintaining privacy.
    """
    name = 'hashed_pii_replacer'
    
    def process_filth(self, filth_list):
        """Process a list of filth objects, replacing text with hashed identifiers.
        
        Args:
            filth_list: List of Filth objects to process
            
        Returns:
            The processed list of Filth objects with replacement strings
        """
        for filth in filth_list:
            filth_type = filth.type.upper()
            filth.replacement_string = f"{filth_type}-{hash(filth.text) % 10000:04d}"
        return filth_list

def setup_scrubber(locale, selected_detectors=None):
    """Helper function to set up a scrubber with appropriate detectors and post-processors."""
    detector_list = []
    
    # Map of detector names to their classes/constructors
    detector_map = {
        'email': lambda: scrubadub.detectors.EmailDetector(name=f'email_{locale}'),
        'phone': lambda: scrubadub.detectors.PhoneDetector(name=f'phone_{locale}'),
        'url': lambda: scrubadub.detectors.UrlDetector(name=f'url_{locale}'),
        'twitter': lambda: scrubadub.detectors.TwitterDetector(name=f'twitter_{locale}'),
        'skype': lambda: scrubadub.detectors.SkypeDetector(name=f'skype_{locale}'),
        'bare_domain': lambda: BareDomainDetector(name=f'bare_domain_{locale}'),
        'markdown_url': lambda: MarkdownUrlDetector(name=f'markdown_url_{locale}'),
        'private_ip': lambda: PrivateIPDetector(name=f'private_ip_{locale}'),
        'public_ip': lambda: PublicIPDetector(name=f'public_ip_{locale}'),
        'spacy_en': lambda: scrubadub_spacy.detectors.SpacyEntityDetector(model='en_core_web_sm', name='spacy_en'),
        'dob_en': lambda: scrubadub.detectors.DateOfBirthDetector(name='dob_en'),
        'spacy_nl': lambda: scrubadub_spacy.detectors.SpacyEntityDetector(model='nl_core_news_sm', name='spacy_nl'),
        'known_pii': lambda: KnownFilthDetector(known_filth_items=load_entity_lists(), name=f'known_pii_{locale}'),
        'dutch_location': lambda: DutchLocationDetector(name=f'dutch_location_{locale}'),
        'dutch_organization': lambda: DutchOrganizationDetector(name=f'dutch_organization_{locale}'),
        'dutch_name': lambda: DutchNameDetector(name=f'dutch_name_{locale}')
    }

    # If no detectors specified, use all available for the locale
    if not selected_detectors:
        selected_detectors = list(detector_map.keys())

    # Add selected detectors based on locale
    for detector_name in selected_detectors:
        if detector_name in detector_map:
            # Skip English detectors for Dutch locale and vice versa
            if locale == 'nl_NL' and detector_name in ['spacy_en', 'dob_en']:
                continue
            if locale == 'en_US' and detector_name in ['spacy_nl', 'known_pii', 'dutch_location', 'dutch_organization', 'dutch_name']:
                continue
            detector_list.append(detector_map[detector_name]())
    
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

def init_routes(app):
    """Initialize Flask routes for the web interface.
    
    Args:
        app: Flask application instance
    """
    @app.route('/')
    def index():
        """Render the main page of the web interface."""
        return render_template('index.html')
    
    @app.route('/process', methods=['POST'])
    def process():
        """Process text and remove PII based on specified locale and detectors.
        
        Expects a JSON payload with:
            - text: The text to process
            - locale: Optional locale code ('nl_NL' or 'en_US')
            - detectors: Optional list of detector names to use
            
        Returns:
            JSON response with scrubbed text or error message
        """
        data = request.json
        input_text = data.get('text', '')
        locale = data.get('locale')  # Can be 'nl_NL', 'en_US', or None for both
        selected_detectors = data.get('detectors', [])
        
        if not input_text:
            return jsonify({'error': 'No text provided'}), 400
            
        try:
            scrubbed_texts = []
            locales_to_process = ['en_US', 'nl_NL'] if locale is None else [locale]
            
            for current_locale in locales_to_process:
                try:
                    # Load appropriate language model
                    lang_code = current_locale.split('_')[0]
                    model_name = "en_core_web_sm" if lang_code == "en" else "nl_core_news_sm"
                    
                    nlp = load_spacy_model(model_name)
                    if nlp is None:
                        continue
                    
                    # Process the input text
                    doc = nlp(input_text)
                    
                    # Setup and run scrubber with selected detectors
                    scrubber = setup_scrubber(current_locale, selected_detectors)
                    scrubbed_text = scrubber.clean(input_text)
                    scrubbed_texts.append({
                        'locale': current_locale,
                        'text': scrubbed_text
                    })
                    
                except Exception as e:
                    print(f"Warning: Processing failed for locale {current_locale}: {str(e)}")
                    continue
            
            if not scrubbed_texts:
                return jsonify({'error': 'All processing attempts failed'}), 500
                
            return jsonify({'results': scrubbed_texts})
            
        except Exception as e:
            return jsonify({'error': f'Scrubbing failed: {str(e)}'}), 500