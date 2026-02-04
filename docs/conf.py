"""Sphinx configuration for cad_to_dagmc documentation."""

import cad_to_dagmc
import pyvista

# PyVista configuration for building docs
pyvista.OFF_SCREEN = True
pyvista.BUILDING_GALLERY = True

project = "cad_to_dagmc"
copyright = "2024, Fusion Energy"
author = "Fusion Energy"

# Truncate version to just semver (remove git hash if present)
_full_version = cad_to_dagmc.__version__
version = _full_version.split("+")[0].split(".dev")[0] if "+" in _full_version or ".dev" in _full_version else _full_version
release = version

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_design",
    "sphinxcontrib.mermaid",
    "sphinxcadquery",
    "jupyter_sphinx",
    "pyvista.ext.plot_directive",
]

# MyST parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "html_admonition",
    "html_image",
    "substitution",
]
myst_heading_anchors = 3
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Theme configuration
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_logo = "_static/logo.png"
html_favicon = "_static/logo.png"

html_theme_options = {
    "repository_url": "https://github.com/fusion-energy/cad_to_dagmc",
    "use_repository_button": True,
    "show_toc_level": 2,
    "show_navbar_depth": 3,
    "navigation_depth": 3,
    "collapse_navigation": False,
    "navigation_with_keys": True,
}

# Hide "Created using Sphinx" in footer
html_show_sphinx = False

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "cadquery": ("https://cadquery.readthedocs.io/en/latest/", None),
    "openmc": ("https://docs.openmc.org/en/stable/", None),
}

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Mermaid settings
mermaid_version = "10.6.1"
mermaid_d3_zoom = False
mermaid_init_js = """
mermaid.initialize({
    startOnLoad: true,
    theme: 'base',
    themeVariables: {
        primaryColor: '#f8fafc',
        primaryTextColor: '#1e293b',
        primaryBorderColor: '#cbd5e1',
        lineColor: '#94a3b8',
        secondaryColor: '#f1f5f9',
        tertiaryColor: '#e2e8f0',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        fontSize: '14px'
    },
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis',
        padding: 20,
        nodeSpacing: 50,
        rankSpacing: 60
    }
});
"""

# PyVista plot directive settings
plot_setup = """
import pyvista as pv
pv.OFF_SCREEN = True
"""
plot_include_source = False

# Custom CSS
html_css_files = [
    "custom.css",
]
