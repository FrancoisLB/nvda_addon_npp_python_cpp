# =============================================================================
# build_addon.py
# NotepadPlusPlus NVDA AppModule — Script de packaging
#
# Génère le manifest.ini à partir de buildVars.py, puis construit
# le fichier .nvda-addon (archive ZIP renommée).
#
# Usage : python build_addon.py
#         (ou via makeAddon.bat)
#
# Prérequis : buildVars.py présent dans le même répertoire.
# =============================================================================

__version__ = "4.2"
__date__ = "2026-06-18"

import zipfile
import os
import fnmatch
import sys

# ---------------------------------------------------------------------------
# Import des métadonnées centralisées depuis buildVars.py
# ---------------------------------------------------------------------------
try:
    import buildVars
except ImportError:
    print("[ERREUR] Impossible d'importer buildVars.py.")
    print("         Ce script doit être lancé depuis le répertoire racine de l'addon.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constantes dérivées de buildVars
# ---------------------------------------------------------------------------

# Nom du fichier .nvda-addon généré
ADDON_FILENAME = "{name}-{version}.nvda-addon".format(
    name=buildVars.addon_name,
    version=buildVars.addon_version,
)

# Patterns d'exclusion (depuis buildVars + ajouts propres au script)
EXCLUDE = buildVars.exclude_patterns + [
    "makeAddon.bat",
    "makeAddon.cmd",
    "build_addon.py",
    "manifest.ini",   # généré automatiquement — on n'embarque pas l'ancien
]

# Répertoires à inclure (depuis buildVars — inclut lib/)
DIRS = buildVars.include_dirs

# Fichiers racine à inclure (hors manifest.ini généré automatiquement)
ROOT_FILES = [
    "installTasks.py",
    "readme.txt",
    "CHANGELOG.txt",
    "DEVELOPPEURS.txt",
]

# Fichiers critiques qui doivent être présents dans l'addon final
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

# ---------------------------------------------------------------------------
# Template du manifest.ini — généré depuis buildVars
# ---------------------------------------------------------------------------

MANIFEST_TEMPLATE = """\
name = {name}
summary = {summary}
description = {description}
version = {version}
author = {author}
docFileName = {docFileName}
minimumNVDAVersion = {minimumNVDAVersion}
lastTestedNVDAVersion = {lastTestedNVDAVersion}
url = {url}
"""


def generate_manifest():
    """
    Génère le contenu du fichier manifest.ini depuis buildVars.py.

    Parameters
    ----------
    Aucun — lit directement le module buildVars importé en tête.

    Returns
    -------
    str
        Contenu complet du manifest.ini, encodé en UTF-8, prêt à être
        injecté dans le ZIP via zipfile.ZipFile.writestr().

    Notes
    -----
    Les valeurs ne sont pas entourées de guillemets — le parseur NVDA
    les lirait littéralement sinon.
    """
    return MANIFEST_TEMPLATE.format(
        name=buildVars.addon_name,
        summary=buildVars.addon_summary,
        description=buildVars.addon_description,
        version=buildVars.addon_version,
        author=buildVars.addon_author,
        docFileName=buildVars.addon_docFileName,
        minimumNVDAVersion=buildVars.addon_minimumNVDAVersion,
        lastTestedNVDAVersion=buildVars.addon_lastTestedNVDAVersion,
        url=buildVars.addon_url,
    )


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def is_excluded(name):
    """
    Vérifie si un fichier ou dossier doit être exclu du package.

    Parameters
    ----------
    name : str
        Nom du fichier ou répertoire (sans chemin parent).

    Returns
    -------
    bool
        True si le fichier doit être exclu, False sinon.
    """
    for pattern in EXCLUDE:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Fonction principale de build
# ---------------------------------------------------------------------------

def build():
    """
    Construit le fichier .nvda-addon.

    Le manifest.ini est généré automatiquement depuis buildVars.py,
    écrit sur le disque (pour le dépôt GitHub et les contributeurs),
    puis injecté dans le ZIP.

    Returns
    -------
    int
        0 si le build est réussi, 1 en cas d'erreur détectée.
    """
    print("============================================")
    print(" Build {name} NVDA Addon v{version}".format(
        name=buildVars.addon_name,
        version=buildVars.addon_version,
    ))
    print("============================================")
    print()

    # Supprimer l'ancienne version si elle existe
    if os.path.exists(ADDON_FILENAME):
        os.remove(ADDON_FILENAME)
        print("Ancienne version supprimée : " + ADDON_FILENAME)

    errors = []

    # --- Génération et écriture du manifest.ini sur le disque ---
    # Écrit dans le répertoire courant pour que le dépôt GitHub reflète
    # toujours la version exacte embarquée dans le .nvda-addon.
    # Convention majoritaire dans la communauté NVDA : manifest.ini versionné.
    manifest_content = generate_manifest()
    with open("manifest.ini", "w", encoding="utf-8") as mf:
        mf.write(manifest_content)
    print("  + manifest.ini  [généré et écrit sur le disque depuis buildVars.py]")

    with zipfile.ZipFile(ADDON_FILENAME, "w", zipfile.ZIP_DEFLATED) as zf:

        # --- Injection du manifest.ini dans le ZIP ---
        zf.writestr("manifest.ini", manifest_content.encode("utf-8"))
        print("  + manifest.ini  [injecté dans le .nvda-addon]")

        # --- Fichiers à la racine ---
        for f in ROOT_FILES:
            if os.path.exists(f):
                zf.write(f, f)
                print("  + " + f)
            else:
                # Ces fichiers sont optionnels
                print("  - absent (ignoré) : " + f)

        # --- Répertoires (appModules, lib, doc, locale) ---
        for d in DIRS:
            if not os.path.isdir(d):
                msg = "  ! RÉPERTOIRE ABSENT : " + d
                print(msg)
                # appModules et lib sont critiques
                if d in ("appModules", "lib"):
                    errors.append(msg)
                continue

            for root, subdirs, files in os.walk(d):
                # Filtrer les sous-dossiers exclus (modification en place)
                subdirs[:] = [s for s in subdirs if not is_excluded(s)]

                for filename in files:
                    if is_excluded(filename):
                        continue
                    filepath = os.path.join(root, filename)
                    # Normaliser les séparateurs pour compatibilité ZIP multi-OS
                    arcname = filepath.replace(os.sep, "/")
                    zf.write(filepath, arcname)
                    print("  + " + arcname)

    print()

    # --- Vérification du contenu du ZIP produit ---
    print("Vérification du contenu :")
    with zipfile.ZipFile(ADDON_FILENAME) as z:
        names = z.namelist()
        for required in REQUIRED:
            if required in names:
                print("  OK       " + required)
            else:
                msg = "MANQUANT : " + required
                print("  MANQUANT " + required)
                errors.append(msg)

        print()
        print("Total fichiers inclus : " + str(len(names)))

    print()

    # --- Résultat final ---
    if errors:
        print("[ERREUR] Problèmes détectés :")
        for e in errors:
            print("  " + e)
        return 1
    else:
        print("[OK] Addon créé avec succès : " + ADDON_FILENAME)
        print()
        print("Pour installer :")
        print("  1. Double-cliquer sur " + ADDON_FILENAME)
        print("  2. NVDA demandera confirmation")
        print("  3. Redémarrer NVDA")
        return 0


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(build())
