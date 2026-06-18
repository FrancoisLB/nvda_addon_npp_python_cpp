# =============================================================================
# buildVars.py
# NotepadPlusPlus NVDA AppModule — Variables de configuration pour SCons
#
# Ce fichier est lu par le script SCons (sconstruct) pour générer le
# fichier .nvda-addon. Il centralise toutes les métadonnées du projet.
#
# Pour créer l'addon : exécuter  scons  dans ce répertoire.
# Prérequis : Python, SCons, et les outils de build NVDA installés.
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

# ---------------------------------------------------------------------------
# Métadonnées de l'addon — doivent correspondre exactement au manifest.ini
# ---------------------------------------------------------------------------

# Nom interne de l'addon (sans espaces, identifiant unique)
addon_name = "NotepadPlusPlus"

# Numéro de version — format recommandé : MAJEUR.MINEUR
addon_version = "4.1"

# Versions NVDA compatibles
addon_minimumNVDAVersion = "2025.1"
addon_lastTestedNVDAVersion = "2026.1"

# Auteurs
addon_author = (
    "Youenn Daviaud, Mael Fer, Baptiste Picquart (ECAM Rennes / My Human Kit)"
    " <contact@myhumankit.org>, FrancoisLB (MHK)"
)

# URL du dépôt (None = non renseigné, sera omis du manifest)
addon_url = None

# Nom du fichier de documentation principal (dans doc/en/)
addon_docFileName = "readme.html"

# ---------------------------------------------------------------------------
# Fichiers à inclure dans l'addon
# SCons utilisera cette liste pour construire le ZIP
# ---------------------------------------------------------------------------

# Fichiers Python à la racine
py_files = [
    "installTasks.py",
]

# Répertoires à inclure entièrement
include_dirs = [
    "appModules",
    "doc",
    "locale",
]

# Fichiers à exclure du package (patterns glob)
exclude_patterns = [
    "*.pyc",
    "__pycache__",
    "*.bak",
    "*.orig",
    ".git",
    "buildTools",
    "sconstruct",
    "buildVars.py",
    "*.nvda-addon",
]
