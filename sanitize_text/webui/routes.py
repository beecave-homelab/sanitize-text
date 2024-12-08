#!venv/bin/python3

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

def load_spacy_model(model_name):
    """Helper function to safely load spaCy model."""
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
    name = 'known_filth_detector'

    def __init__(self, known_filth_items, **kwargs):
        self.known_filth_items = known_filth_items
        super().__init__(**kwargs)

    def iter_filth(self, text, document_name=None):
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
    name = 'hashed_pii_replacer'
    def process_filth(self, filth_list):
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
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/process', methods=['POST'])
    def process():
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