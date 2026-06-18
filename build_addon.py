# =============================================================================
# build_addon.py
# NotepadPlusPlus NVDA AppModule v4.0 — Script de packaging
#
# Appele par makeAddon.bat. Ne pas executer directement.
# Usage : python build_addon.py
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

import zipfile
import os
import fnmatch
import sys

# --- Configuration ---
ADDON_NAME = "NotepadPlusPlus-4.2.nvda-addon"

EXCLUDE = [
    "*.pyc", "__pycache__", "*.bak", "*.orig", ".git",
    "buildTools", "sconstruct", "buildVars.py",
    "*.nvda-addon", "makeAddon.bat", "makeAddon.cmd",
    "build_addon.py"
]

# IMPORTANT : lib/ est inclus ici
DIRS = ["appModules", "lib", "doc", "locale"]

ROOT_FILES = [
    "manifest.ini",
    "installTasks.py",
    "readme.txt",
    "CHANGELOG.txt",
    "DEVELOPPEURS.txt",
]

# Fichiers critiques qui doivent etre presents dans l'addon
REQUIRED = [
    "manifest.ini",
    "installTasks.py",
    "appModules/notepadPlusPlus.py",
    "lib/__init__.py",
    "lib/scintilla.py",
    "lib/lang_detector.py",
    "lib/parsers/__init__.py",
    "lib/parsers/base_parser.py",
    "lib/parsers/python_parser.py",
    "lib/parsers/cpp_parser.py",
]


def is_excluded(name):
    """Verifie si un fichier ou dossier doit etre exclu."""
    for pattern in EXCLUDE:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def build():
    """Construit le fichier .nvda-addon."""

    print("============================================")
    print(" Build NotepadPlusPlus NVDA Addon v4.0")
    print("============================================")
    print()

    # Supprimer l'ancien fichier
    if os.path.exists(ADDON_NAME):
        os.remove(ADDON_NAME)
        print("Ancienne version supprimee.")

    errors = []

    with zipfile.ZipFile(ADDON_NAME, "w", zipfile.ZIP_DEFLATED) as zf:

        # Fichiers a la racine
        for f in ROOT_FILES:
            if os.path.exists(f):
                zf.write(f, f)
                print("  + " + f)
            else:
                print("  ! ABSENT (ignore) : " + f)

        # Repertoires
        for d in DIRS:
            if not os.path.isdir(d):
                msg = "  ! REPERTOIRE ABSENT : " + d
                print(msg)
                if d in ("appModules", "lib"):
                    errors.append(msg)
                continue

            for root, subdirs, files in os.walk(d):
                # Filtrer les sous-dossiers exclus
                subdirs[:] = [
                    s for s in subdirs if not is_excluded(s)
                ]
                for filename in files:
                    if is_excluded(filename):
                        continue
                    filepath = os.path.join(root, filename)
                    # Normaliser les separateurs pour le ZIP
                    arcname = filepath.replace(os.sep, "/")
                    zf.write(filepath, arcname)
                    print("  + " + arcname)

    print()

    # Verification du contenu
    print("Verification du contenu :")
    with zipfile.ZipFile(ADDON_NAME) as z:
        names = z.namelist()
        all_ok = True
        for required in REQUIRED:
            if required in names:
                print("  OK       " + required)
            else:
                print("  MANQUANT " + required)
                errors.append("MANQUANT : " + required)
                all_ok = False

        print()
        print("Total fichiers inclus : " + str(len(names)))

    print()
    if errors:
        print("[ERREUR] Problemes detectes :")
        for e in errors:
            print("  " + e)
        return 1
    else:
        print("[OK] Addon cree avec succes : " + ADDON_NAME)
        print()
        print("Pour installer :")
        print("  1. Double-cliquer sur " + ADDON_NAME)
        print("  2. NVDA demandera confirmation")
        print("  3. Redemarrer NVDA")
        return 0


if __name__ == "__main__":
    sys.exit(build())
