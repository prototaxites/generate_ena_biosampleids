"""
ENA Biosample ID Generation Package

This package provides tools for generating ENA biosample IDs for various sample types,
with both command-line interfaces and programmatic APIs.
"""

from .metagenome_biosample_generator import (
    MetagenomeBiosampleGenerator,
    create_generator,
    generate_metagenome_biosample_ids,
)

__all__ = [
    "MetagenomeBiosampleGenerator",
    "create_generator",
    "generate_metagenome_biosample_ids",
]

__version__ = "1.0.0"


def main() -> None:
    print("Hello from generate-ena-biosampleids!")
