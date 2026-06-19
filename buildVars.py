# =============================================================================
# buildVars.py
# NotepadPlusPlus NVDA AppModule — Variables de configuration pour le build
#
# Ce fichier est la SOURCE DE VÉRITÉ du projet. Il est lu par build_addon.py
# pour générer automatiquement le manifest.ini et construire le .nvda-addon.
#
# Pour créer l'addon : exécuter makeAddon.bat (ou python build_addon.py)
# Prérequis : Python 3.x installé et accessible dans le PATH.
# =============================================================================

__version__ = "4.2"
__date__ = "2026-06-18"

# ---------------------------------------------------------------------------
# Métadonnées de l'addon
# Ces valeurs sont injectées dans le manifest.ini généré automatiquement.
# ---------------------------------------------------------------------------

# Nom interne de l'addon (sans espaces, identifiant unique, lowerCamelCase
# ou underscores — utilisé comme nom de dossier dans NVDA)
addon_name = "nvda_addon_npp_python_cpp"

# Résumé court affiché dans la liste des addons NVDA
addon_summary = "Notepad++ accessibility for Python and C/C++ development (32 and 64 bits)"

# Description longue — OBLIGATOIRE pour la publication sur le Store NVDA.
# Affichée dans le Store quand l'utilisateur consulte l'addon.
addon_description = (
    "NVDA add-on for Notepad++ that improves accessibility for Python and C/C++ developers. "
    "Provides enhanced navigation, code structure browsing, bookmark management, "
    "compiler output reading, and keyboard shortcuts tailored for 32-bit and 64-bit "
    "development workflows."
)

# Numéro de version — format : MAJEUR.MINEUR
addon_version = "4.2"

# Versions NVDA compatibles (format : AAAA.MINEUR)
addon_minimumNVDAVersion = "2026.1"
addon_lastTestedNVDAVersion = "2026.1"

# Auteurs du projet
addon_author = (
    "Youenn Daviaud, Mael Fer, Baptiste Picquart (ECAM Rennes / My Human Kit)"
    " <contact@myhumankit.org>, FrancoisLB (MHK)"
)

# URL du dépôt GitHub (affiché dans le Store et dans la boîte "À propos" NVDA)
addon_url = "https://github.com/FrancoisLB/nvda_addon_npp_python_cpp"

# Nom du fichier de documentation principal (dans doc/en/)
addon_docFileName = "readme.html"

# ---------------------------------------------------------------------------
# Fichiers à inclure dans l'addon
# Ces listes sont utilisées par build_addon.py pour construire le ZIP.
# ---------------------------------------------------------------------------

# Fichiers Python à la racine de l'addon
py_files = [
    "installTasks.py",
]

# Répertoires à inclure entièrement dans le package
# IMPORTANT : lib/ doit figurer ici — il contient les modules internes
#             (scintilla.py, lang_detector.py, parsers/...)
include_dirs = [
    "appModules",
    "lib",        # modules internes : scintilla, lang_detector, parsers
    "doc",
    "locale",
]

# Fichiers et dossiers à exclure du package (patterns glob)
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
