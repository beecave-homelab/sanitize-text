"""Core functionality for text scrubbing.

This module provides the main text scrubbing functionality, including setup of
detectors, loading of entity lists, and text processing with multiple locales.
"""

import os
import spacy
import scrubadub
import warnings
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from ..utils.post_processors import HashedPIIReplacer
from ..utils.custom_detectors import (
    BareDomainDetector,
    MarkdownUrlDetector,
    PrivateIPDetector,
    PublicIPDetector,
    DutchLocationDetector,
    DutchOrganizationDetector,
    DutchNameDetector,
    CustomWordDetector
)
from scrubadub.detectors.email import EmailDetector
from scrubadub.detectors.phone import PhoneDetector

def load_entity_lists() -> List[Dict[str, Any]]:
    """Load entity lists from data directory.
    
    Loads predefined lists of entities (cities, organizations, names) from JSON files
    in the data directory. These lists are used by the Dutch entity detectors.
    
    Returns:
        List of dictionaries containing entity information with keys:
            - match: The entity text to match
            - filth_type: Type of the entity (location, organization, name)
            - ignore_case: Whether to perform case-insensitive matching
    """
    known_pii = []
    
    try:
        # Get the package's data directory
        data_dir = Path(__file__).parent.parent / 'data' / 'nl_entities'
        if not data_dir.exists():
            print(f"Warning: Directory {data_dir} does not exist")
            return known_pii
            
        json_files = {
            'cities.json': 'location',
            'organizations.json': 'organization',
            'names.json': 'name'
        }
        
        for filename, filth_type in json_files.items():
            try:
                filepath = data_dir / filename
                if not filepath.exists():
                    continue
                    
                with open(filepath, 'r') as f:
                    entities = json.load(f)
                    for entity in entities:
                        known_pii.append({
                            'match': entity['match'],
                            'filth_type': filth_type,
                            'ignore_case': True
                        })
                print(f"Loaded {len(entities)} entities from {filename}")
            except Exception as e:
                print(f"Warning: Could not load entity list {filename}: {str(e)}")
    except Exception as e:
        print(f"Warning: Error loading entity lists: {str(e)}")
    
    return known_pii

def load_spacy_model(model_name: str) -> Optional[spacy.language.Language]:
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

def get_available_detectors(locale: Optional[str] = None) -> Dict[str, str]:
    """Get available detector names and descriptions for the given locale.
    
    Args:
        locale: Optional locale code (e.g., 'nl_NL', 'en_US')
        
    Returns:
        Dictionary mapping detector names to their descriptions
    """
    generic_detectors = {
        'email': 'Detect email addresses (e.g., user@example.com)',
        'phone': 'Detect phone numbers',
        'url': 'Detect URLs (bare domains, www prefixes, http(s), complex paths, query parameters)',
        'markdown_url': 'Detect URLs within Markdown links [text](url)',
        'private_ip': 'Detect private IP addresses (192.168.x.x, 10.0.x.x, 172.16-31.x.x)',
        'public_ip': 'Detect public IP addresses (any non-private IP)'
    }
    
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
        return {**generic_detectors, **locale_detectors.get(locale, {})}
    return locale_detectors

def setup_scrubber(
    locale: str,
    selected_detectors: Optional[List[str]] = None,
    custom_text: Optional[str] = None
) -> scrubadub.Scrubber:
    """Set up a scrubber with appropriate detectors and post-processors.
    
    Args:
        locale: Locale code for text processing (e.g., 'nl_NL', 'en_US')
        selected_detectors: Optional list of detector names to use
        custom_text: Optional custom text to detect and replace
        
    Returns:
        Configured scrubber instance ready for text processing
    """
    detector_list = []
    available_detectors = get_available_detectors(locale).keys()
    
    if selected_detectors:
        selected_detectors = [d.lower() for d in selected_detectors]
        invalid_detectors = [d for d in selected_detectors if d not in available_detectors]
        if invalid_detectors:
            print(f"Warning: Invalid detector(s) for locale {locale}: {', '.join(invalid_detectors)}")
    
    # Add custom word detector if custom text is provided
    if custom_text:
        detector_list.append(CustomWordDetector(custom_text=custom_text))
    
    # Add generic detectors
    generic_detectors = {
        'email': EmailDetector,
        'phone': PhoneDetector,
        'url': BareDomainDetector,
        'markdown_url': MarkdownUrlDetector,
        'private_ip': PrivateIPDetector,
        'public_ip': PublicIPDetector
    }
    
    for detector_name, detector_class in generic_detectors.items():
        if not selected_detectors or detector_name in selected_detectors:
            try:
                if detector_name == 'email':
                    detector = detector_class(locale=locale)
                else:
                    detector = detector_class()
                detector_list.append(detector)
            except Exception as e:
                print(f"Warning: Could not add detector {detector_name}: {str(e)}")
    
    # Configure locale-specific detectors
    if locale == 'nl_NL':
        dutch_detectors = {
            'location': DutchLocationDetector,
            'organization': DutchOrganizationDetector,
            'name': DutchNameDetector
        }
        
        if not selected_detectors:
            for detector_class in dutch_detectors.values():
                detector_list.append(detector_class())
        else:
            for detector_name, detector_class in dutch_detectors.items():
                if detector_name in selected_detectors:
                    detector_list.append(detector_class())
    
    # Initialize scrubber
    scrubber = scrubadub.Scrubber(
        locale=locale,
        detector_list=detector_list,
        post_processor_list=[HashedPIIReplacer()]
    )
    
    # Explicitly disable all other detectors
    scrubber.detectors = {d.name: d for d in detector_list}
    
    return scrubber

def scrub_text(
    text: str,
    locale: Optional[str] = None,
    selected_detectors: Optional[List[str]] = None,
    custom_text: Optional[str] = None
) -> List[str]:
    """Scrub PII from the given text using specified locale and detectors.
    
    This is the main function for text sanitization. It processes the input text
    using the specified locale and detectors, removing personally identifiable
    information (PII) and replacing it with anonymized placeholders.
    
    Args:
        text: The text to scrub
        locale: Optional locale code (e.g., 'nl_NL', 'en_US')
        selected_detectors: Optional list of detector names to use
        custom_text: Optional custom text to detect and replace
        
    Returns:
        List of scrubbed texts, one for each processed locale
        
    Raises:
        Exception: If all processing attempts fail
    """
    # Suppress specific warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
    warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")
    
    scrubbed_texts = []
    locales_to_process = ['en_US', 'nl_NL'] if locale is None else [locale]
    
    for current_locale in locales_to_process:
        try:
            # Load appropriate language model
            lang_code = current_locale.split('_')[0]
            model_name = "en_core_web_sm" if lang_code == "en" else "nl_core_news_sm"
            
            nlp = load_spacy_model(model_name)
            if nlp is None:
                print(f"Skipping locale {current_locale} due to missing language model")
                continue
            
            # Process the input text
            doc = nlp(text)
            
            # Setup and run scrubber
            scrubber = setup_scrubber(current_locale, selected_detectors, custom_text)
            scrubbed_text = scrubber.clean(text)
            scrubbed_texts.append(f"Results for {current_locale}:\n{scrubbed_text}")
            
        except Exception as e:
            print(f"Warning: Processing failed for locale {current_locale}: {str(e)}")
            continue
    
    if not scrubbed_texts:
        raise Exception("All processing attempts failed")
    
    return scrubbed_texts 