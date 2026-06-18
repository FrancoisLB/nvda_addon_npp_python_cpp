# =============================================================================
# lib/lang_detector.py
# NotepadPlusPlus NVDA AppModule v4.0
#
# Detection automatique du langage du fichier ouvert dans Notepad++.
#
# Deux strategies de detection sont utilisees, dans cet ordre :
#   1. SCI_GETLEXER : interroge Scintilla pour connaitre le lexer actif.
#      C'est la methode fiable et precise — Notepad++ a deja identifie
#      le langage selon sa configuration interne.
#   2. Fallback sur l'extension du fichier : si SCI_GETLEXER retourne
#      un lexer inconnu ou NULL, on regarde l'extension du fichier courant
#      via l'API NVDA (appModule.productName ou nom du fichier).
#
# Auteurs : ECAM Rennes / My Human Kit
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

import os
import logging
from enum import Enum, auto

from lib.scintilla import (
    ScintillaWrapper,
    SCLEX_PYTHON, SCLEX_CPP, SCLEX_VHDL, SCLEX_NULL
)

log = logging.getLogger(__name__)


# =============================================================================
# Enumeration des langages supportes
# =============================================================================

class Language(Enum):
    """
    Enumeration des langages de code supportes par l'addon.

    Attributes
    ----------
    PYTHON : auto
        Langage Python (.py) — support complet.
    CPP : auto
        Langage C ou C++ (.c, .cpp, .h, .hpp) — support complet.
    VHDL : auto
        Langage VHDL (.vhd, .vhdl) — prevu pour v5.0.
    UNKNOWN : auto
        Langage non reconnu ou fichier texte brut.
    """
    PYTHON  = auto()
    CPP     = auto()
    VHDL    = auto()
    UNKNOWN = auto()

    def getDisplayName(self):
        """
        Retourne le nom affichable du langage pour les annonces NVDA.

        Returns
        -------
        str
            Nom lisible du langage (ex: "Python", "C/C++").
        """
        names = {
            Language.PYTHON  : "Python",
            Language.CPP     : "C/C++",
            Language.VHDL    : "VHDL",
            Language.UNKNOWN : "non supporte",
        }
        return names.get(self, "inconnu")


# =============================================================================
# Classe LangDetector
# =============================================================================

class LangDetector:
    """
    Detecte automatiquement le langage du fichier ouvert dans Notepad++.

    Utilise SCI_GETLEXER comme source principale, avec fallback sur
    l'extension du fichier courant.

    Parameters
    ----------
    sci : ScintillaWrapper
        Instance du wrappeur Scintilla, deja initialise et rafraichi.

    Attributes
    ----------
    _sci : ScintillaWrapper
        Reference au wrappeur Scintilla.
    _current_language : Language
        Dernier langage detecte (mis en cache).

    Examples
    --------
    >>> sci = ScintillaWrapper(npp_hwnd)
    >>> sci.refresh()
    >>> detector = LangDetector(sci)
    >>> lang = detector.detect(current_file_path)
    >>> print(lang.getDisplayName())
    Python
    """

    # Extensions de fichiers connues par langage
    # (utilise en fallback si SCI_GETLEXER ne donne pas de resultat)
    _EXTENSIONS = {
        Language.PYTHON : {".py", ".pyw", ".pyi"},
        Language.CPP    : {".c", ".cpp", ".cxx", ".cc",
                           ".h", ".hpp", ".hxx", ".hh",
                           ".ino"},   # Arduino
        Language.VHDL   : {".vhd", ".vhdl"},
    }

    # Correspondance ID lexer Scintilla -> Language
    _LEXER_MAP = {
        SCLEX_PYTHON : Language.PYTHON,
        SCLEX_CPP    : Language.CPP,
        SCLEX_VHDL   : Language.VHDL,
    }

    def __init__(self, sci):
        """
        Initialise le detecteur de langage.

        Parameters
        ----------
        sci : ScintillaWrapper
            Wrappeur Scintilla deja initialise.
        """
        self._sci = sci
        self._current_language = Language.UNKNOWN
        log.debug("LangDetector initialise")

    def detect(self, file_path=None):
        """
        Detecte le langage du fichier courant.

        Strategie :
          1. SCI_GETLEXER -> correspondance avec LEXER_MAP
          2. Si echec, fallback sur l'extension de file_path

        Parameters
        ----------
        file_path : str, optional
            Chemin complet du fichier courant. Utilise en fallback
            si SCI_GETLEXER ne permet pas d'identifier le langage.

        Returns
        -------
        Language
            Le langage detecte. Toujours Language.UNKNOWN si rien ne
            correspond.
        """
        # --- Strategie 1 : SCI_GETLEXER ---
        lang = self._detectFromLexer()
        if lang != Language.UNKNOWN:
            self._current_language = lang
            log.debug(
                "Langage detecte via lexer : %s", lang.getDisplayName()
            )
            return lang

        # --- Strategie 2 : fallback extension de fichier ---
        if file_path:
            lang = self._detectFromExtension(file_path)
            if lang != Language.UNKNOWN:
                self._current_language = lang
                log.debug(
                    "Langage detecte via extension '%s' : %s",
                    os.path.splitext(file_path)[1],
                    lang.getDisplayName()
                )
                return lang

        # --- Aucun langage reconnu ---
        self._current_language = Language.UNKNOWN
        log.debug("Langage non reconnu (UNKNOWN)")
        return Language.UNKNOWN

    def getCurrent(self):
        """
        Retourne le dernier langage detecte (mis en cache).

        Returns
        -------
        Language
            Dernier resultat de detect().
        """
        return self._current_language

    def isSupported(self):
        """
        Indique si le langage courant est supporte pour la navigation.

        Returns
        -------
        bool
            True si Python ou C/C++ (navigation complete disponible).
            False si VHDL (prevu v5.0) ou UNKNOWN.
        """
        return self._current_language in (Language.PYTHON, Language.CPP)

    # -------------------------------------------------------------------------
    # Methodes privees
    # -------------------------------------------------------------------------

    def _detectFromLexer(self):
        """
        Detecte le langage via SCI_GETLEXER.

        Returns
        -------
        Language
            Language detecte, ou Language.UNKNOWN si non reconnu.
        """
        try:
            if not self._sci.isAvailable():
                return Language.UNKNOWN

            lexer_id = self._sci.getLexer()
            log.debug("SCI_GETLEXER retourne : %d", lexer_id)

            return self._LEXER_MAP.get(lexer_id, Language.UNKNOWN)

        except Exception as e:
            log.error(
                "Erreur _detectFromLexer : %s", e, exc_info=True
            )
            return Language.UNKNOWN

    def _detectFromExtension(self, file_path):
        """
        Detecte le langage depuis l'extension du fichier.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.

        Returns
        -------
        Language
            Language detecte, ou Language.UNKNOWN.
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if not ext:
                return Language.UNKNOWN

            for lang, extensions in self._EXTENSIONS.items():
                if ext in extensions:
                    return lang

            return Language.UNKNOWN

        except Exception as e:
            log.error(
                "Erreur _detectFromExtension('%s') : %s",
                file_path, e, exc_info=True
            )
            return Language.UNKNOWN
