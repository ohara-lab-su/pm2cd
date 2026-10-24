from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
project = "pm2cd"
author = "ohara-lab-su"
extensions = ["myst_parser", "sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
master_doc = "index"
html_theme = "sphinx_rtd_theme"
html_static_path = []
exclude_patterns = ["_build"]
language = os.environ.get("DOC_LANGUAGE", "en")

# The controller runtime is not needed to render API signatures.
# Mock only unavailable runtime infrastructure; retain actual pm2cd source.
autodoc_mock_imports = ["process_executor", "x_logger"]
