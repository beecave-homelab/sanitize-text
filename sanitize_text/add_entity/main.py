#!/usr/bin/env python3

"""Utility script for adding new entities to sanitization lists.

This tool allows adding new entries to the sanitization entity lists used for
PII detection. It supports adding cities, names, and organizations to their
respective JSON files.

Examples:
    Add a new city:
        $ python -m sanitize_text.add_entity -c "Amsterdam"

    Add a new name:
        $ python -m sanitize_text.add_entity -n "John Smith"

    Add a new organization:
        $ python -m sanitize_text.add_entity -o "Example B.V."

    Add multiple entities:
        $ python -m sanitize_text.add_entity -c "Amsterdam" \
            -n "John Smith" -o "Example B.V."
"""

import json
from pathlib import Path

import click

# Define custom context settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class EntityManager:
    """Manages the addition of entities to sanitization JSON files."""

    def __init__(self) -> None:
        """Initialize the EntityManager with paths to JSON files."""
        self.base_path = Path(__file__).parent.parent / "data" / "nl_entities"
        self.files = {
            "city": self.base_path / "cities.json",
            "name": self.base_path / "names.json",
            "organization": self.base_path / "organizations.json",
        }

    def load_json(self, file_path: Path) -> list[dict[str, str]]:
        """Load and parse a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            List of dictionaries containing entity data
        """
        try:
            with open(file_path, encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            click.echo(f"Error: File {file_path} not found.", err=True)
            return []
        except PermissionError:
            click.echo(f"Error: Permission denied when accessing {file_path}", err=True)
            return []
        except json.JSONDecodeError:
            click.echo(f"Error: Invalid JSON format in {file_path}", err=True)
            return []

    def save_json(self, file_path: Path, data: list[dict[str, str]]) -> bool:
        """Save data to a JSON file.

        Args:
            file_path: Path to save the JSON file
            data: List of dictionaries to save

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
            return True
        except PermissionError:
            click.echo(f"Error: Permission denied when writing to {file_path}", err=True)
            return False
        except Exception as error:
            click.echo(f"Error saving file: {str(error)}", err=True)
            return False

    def add_entity(self, entity_type: str, value: str) -> bool:
        """Add a new entity to the specified entity type file.

        Args:
            entity_type: Type of entity ('city', 'name', or 'organization')
            value: The entity value to add

        Returns:
            bool: True if addition was successful, False otherwise
        """
        if entity_type not in self.files:
            click.echo(f"Error: Invalid entity type '{entity_type}'", err=True)
            return False

        file_path = self.files[entity_type]
        entities = self.load_json(file_path)

        new_entry = {
            "match": value,
            "filth_type": "location" if entity_type == "city" else entity_type,
        }

        # Check for existing entries (case-insensitive)
        if any(entity["match"].lower() == value.lower() for entity in entities):
            click.echo(
                f"Warning: {entity_type.capitalize()} '{value}' already exists",
                err=True,
            )
            return False

        # Add new entry and maintain alphabetical order
        entities.append(new_entry)
        entities.sort(key=lambda x: x["match"].lower())

        if self.save_json(file_path, entities):
            click.echo(f"Successfully added {entity_type} '{value}'")
            return True
        return False


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--city",
    "-c",
    type=str,
    help="Add a new city to the sanitization list.",
    metavar="<city>",
)
@click.option(
    "--name",
    "-n",
    type=str,
    help="Add a new person name to the sanitization list.",
    metavar="<name>",
)
@click.option(
    "--organization",
    "-o",
    type=str,
    help="Add a new organization to the sanitization list.",
    metavar="<organization>",
)
def main(city: str | None, name: str | None, organization: str | None) -> None:
    r"""Add new entities to sanitization lists.

    This tool manages the addition of new entities to the sanitization lists used
    for PII detection. Each entity type is stored in a separate JSON file and
    maintained in alphabetical order.

    \b
    Entity Types:
    - Cities: Geographic locations
    - Names: Person names
    - Organizations: Company and institution names

    \f
    Args:
        city: City name to add
        name: Person name to add
        organization: Organization name to add
    """
    entity_manager = EntityManager()

    if not any([city, name, organization]):
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        return

    if city:
        entity_manager.add_entity("city", city)
    if name:
        entity_manager.add_entity("name", name)
    if organization:
        entity_manager.add_entity("organization", organization)


if __name__ == "__main__":
    main()
