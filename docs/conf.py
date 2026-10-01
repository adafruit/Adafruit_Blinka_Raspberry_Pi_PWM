"""Sphinx configuration for the Raspberry Pi PWM companion package."""

from importlib import metadata

project = "Adafruit Blinka Raspberry Pi PWM"
author = "Melissa LeBlanc-Williams"
copyright = "2026 Melissa LeBlanc-Williams"
release = metadata.version("Adafruit-Blinka-Raspberry-Pi-PWM")
version = release
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "myst_parser"]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build"]
html_theme = "sphinx_rtd_theme"
autodoc_member_order = "bysource"
