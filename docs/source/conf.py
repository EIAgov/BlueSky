# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'BlueSky Prototype Model'
copyright = '2024, Energy Information Administration'
author = 'US Energy Information Administration'
release = 'v1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}

master_doc = 'index'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_markdown_tables',
    'sphinx_markdown_builder',
    'sphinx.ext.autosummary',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'numpydoc',
]

autosummary_generate = True
autosummary_imported_members = True
numpydoc_class_members_toctree = False
numpydoc_show_class_members = False

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'titles_only': True,
    'prev_next_buttons_location': False,
}
html_sidebars = {'**': ['globaltoc.html']}
