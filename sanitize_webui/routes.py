#!venv/bin/python3

import os
from flask import request, render_template, jsonify
import scrubadub
import scrubadub_spacy
import spacy
from scrubadub.filth import Filth

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

def setup_scrubber(locale):
    """Helper function to set up a scrubber with appropriate detectors and post-processors."""
    detector_list = []
    
    # Add universal detectors with unique names
    detector_list.extend([
        scrubadub.detectors.EmailDetector(name=f'email_{locale}'),
        scrubadub.detectors.PhoneDetector(name=f'phone_{locale}'),
        scrubadub.detectors.UrlDetector(name=f'url_{locale}'),
        scrubadub.detectors.TwitterDetector(name=f'twitter_{locale}'),
        scrubadub.detectors.SkypeDetector(name=f'skype_{locale}')
    ])
    
    if locale == 'en_US':
        detector_list.extend([
            scrubadub_spacy.detectors.SpacyEntityDetector(
                model='en_core_web_sm',
                name='spacy_en'
            ),
            scrubadub.detectors.DateOfBirthDetector(name='dob_en')
        ])
    elif locale == 'nl_NL':
        known_pii = load_entity_lists()
        detector_list.extend([
            scrubadub_spacy.detectors.SpacyEntityDetector(
                model='nl_core_news_sm',
                name='spacy_nl'
            ),
            KnownFilthDetector(
                known_filth_items=known_pii,
                name=f'known_pii_{locale}'
            )
        ])
    
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
                    
                    # Setup and run scrubber
                    scrubber = setup_scrubber(current_locale)
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