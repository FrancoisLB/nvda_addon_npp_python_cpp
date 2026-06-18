# =============================================================================
# lib/parsers/base_parser.py
# NotepadPlusPlus NVDA AppModule v4.0
#
# Classe abstraite definissant l'interface commune a tous les parsers de code.
#
# Chaque parser concret (PythonParser, CppParser, VhdlParser...) herite de
# BaseParser et implemente ses methodes abstraites. L'AppModule utilise
# toujours l'interface BaseParser, ce qui permet de changer de parser
# sans modifier le code de navigation.
#
# Auteurs : ECAM Rennes / My Human Kit
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

import re
import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Interface abstraite commune a tous les parsers de structures de code.

    Un parser est responsable de reconnaitre les structures syntaxiques
    d'un langage (fonctions, classes, methodes...) dans le texte d'une ligne.

    Les methodes de navigation (findNext, findPrev) sont implementees ici
    de facon generique en s'appuyant sur les methodes abstraites isFunction()
    et isClass() que chaque parser concret doit implementer.

    La navigation utilise le ScintillaWrapper pour lire les lignes et
    deplacer le curseur — elle n'utilise plus l'API NVDA standard.

    Parameters
    ----------
    sci : ScintillaWrapper
        Instance du wrappeur Scintilla pour lire/ecrire dans l'editeur.

    Attributes
    ----------
    _sci : ScintillaWrapper
        Reference au wrappeur Scintilla.

    Examples
    --------
    Un parser concret doit implementer isFunction() et isClass() :

    class PythonParser(BaseParser):
        def isFunction(self, line_text):
            return bool(re.match(r'^\\s*(async\\s+)?def\\s+', line_text))
        def isClass(self, line_text):
            return bool(re.match(r'^\\s*class\\s+', line_text))
    """

    def __init__(self, sci):
        """
        Initialise le parser avec le wrappeur Scintilla.

        Parameters
        ----------
        sci : ScintillaWrapper
            Wrappeur Scintilla deja initialise et rafraichi.
        """
        self._sci = sci

    # -------------------------------------------------------------------------
    # Methodes abstraites — a implementer dans chaque parser concret
    # -------------------------------------------------------------------------

    @abstractmethod
    def isFunction(self, line_text):
        """
        Determine si une ligne contient une declaration de fonction/methode.

        Parameters
        ----------
        line_text : str
            Texte brut de la ligne (avec indentation, sans \\n final).

        Returns
        -------
        bool
            True si la ligne est une declaration de fonction ou methode.
        """
        ...

    @abstractmethod
    def isClass(self, line_text):
        """
        Determine si une ligne contient une declaration de classe.

        Parameters
        ----------
        line_text : str
            Texte brut de la ligne (avec indentation, sans \\n final).

        Returns
        -------
        bool
            True si la ligne est une declaration de classe.
        """
        ...

    @abstractmethod
    def getLanguageName(self):
        """
        Retourne le nom du langage gere par ce parser.

        Returns
        -------
        str
            Nom lisible du langage (ex: "Python", "C/C++").
        """
        ...

    # -------------------------------------------------------------------------
    # Methodes de navigation generiques (implementees dans BaseParser)
    # -------------------------------------------------------------------------

    def findNextFunction(self, current_line):
        """
        Trouve la prochaine declaration de fonction/methode apres la ligne courante.

        Parcourt les lignes vers le bas depuis current_line + 1 jusqu'a la
        fin du document. Retourne la premiere ligne correspondant a isFunction().

        Parameters
        ----------
        current_line : int
            Numero de ligne de depart (base 0). La recherche commence
            a la ligne suivante (current_line + 1).

        Returns
        -------
        int or None
            Numero de ligne (base 0) de la prochaine declaration,
            ou None si aucune trouvee jusqu'a la fin du document.
        """
        return self._findNext(current_line, self.isFunction)

    def findPrevFunction(self, current_line):
        """
        Trouve la declaration de fonction/methode precedente.

        Parameters
        ----------
        current_line : int
            Numero de ligne de depart (base 0). La recherche commence
            a la ligne precedente (current_line - 1).

        Returns
        -------
        int or None
            Numero de ligne (base 0) ou None si aucune trouvee.
        """
        return self._findPrev(current_line, self.isFunction)

    def findNextClass(self, current_line):
        """
        Trouve la prochaine declaration de classe apres la ligne courante.

        Parameters
        ----------
        current_line : int
            Numero de ligne de depart (base 0).

        Returns
        -------
        int or None
            Numero de ligne (base 0) ou None si aucune trouvee.
        """
        return self._findNext(current_line, self.isClass)

    def findPrevClass(self, current_line):
        """
        Trouve la declaration de classe precedente.

        Parameters
        ----------
        current_line : int
            Numero de ligne de depart (base 0).

        Returns
        -------
        int or None
            Numero de ligne (base 0) ou None si aucune trouvee.
        """
        return self._findPrev(current_line, self.isClass)

    # -------------------------------------------------------------------------
    # Utilitaires partages entre les parsers
    # -------------------------------------------------------------------------

    def getIndentLevel(self, line_text, tab_size=4):
        """
        Calcule le niveau d'indentation d'une ligne en nombre d'espaces.

        Les tabulations sont converties en espaces (tab_size espaces par tab).

        Parameters
        ----------
        line_text : str
            Texte brut de la ligne.
        tab_size : int, optional
            Nombre d'espaces equivalents a une tabulation (par defaut 4).

        Returns
        -------
        int
            Nombre d'espaces d'indentation en debut de ligne.
        """
        count = 0
        for char in line_text:
            if char == '\t':
                count += tab_size
            elif char == ' ':
                count += 1
            else:
                break
        return count

    def stripLineComment(self, line_text, comment_markers):
        """
        Supprime le commentaire de fin de ligne (hors chaines de caracteres).

        Note : implementation simplifiee — ne gere pas les commentaires
        a l'interieur de chaines multilignes.

        Parameters
        ----------
        line_text : str
            Texte brut de la ligne.
        comment_markers : list of str
            Marqueurs de debut de commentaire (ex: ["//", "#"]).

        Returns
        -------
        str
            Ligne sans le commentaire de fin.
        """
        for marker in comment_markers:
            idx = line_text.find(marker)
            if idx >= 0:
                line_text = line_text[:idx]
        return line_text

    # -------------------------------------------------------------------------
    # Implementation generique de findNext / findPrev
    # -------------------------------------------------------------------------

    def _findNext(self, current_line, predicate):
        """
        Parcourt les lignes vers le bas et retourne la premiere
        qui satisfait le predicat.

        Parameters
        ----------
        current_line : int
            Ligne de depart (exclue de la recherche).
        predicate : callable
            Fonction (line_text: str) -> bool.

        Returns
        -------
        int or None
            Numero de ligne trouvee (base 0), ou None.
        """
        try:
            total = self._sci.getLineCount()
            for line in range(current_line + 1, total):
                text = self._sci.getLine(line).rstrip("\r\n")
                if predicate(text):
                    log.debug(
                        "_findNext : trouve ligne %d : %s",
                        line, text.strip()[:60]
                    )
                    return line
            return None
        except Exception as e:
            log.error("Erreur _findNext : %s", e, exc_info=True)
            return None

    def _findPrev(self, current_line, predicate):
        """
        Parcourt les lignes vers le haut et retourne la premiere
        qui satisfait le predicat.

        Parameters
        ----------
        current_line : int
            Ligne de depart (exclue de la recherche).
        predicate : callable
            Fonction (line_text: str) -> bool.

        Returns
        -------
        int or None
            Numero de ligne trouvee (base 0), ou None.
        """
        try:
            for line in range(current_line - 1, -1, -1):
                text = self._sci.getLine(line).rstrip("\r\n")
                if predicate(text):
                    log.debug(
                        "_findPrev : trouve ligne %d : %s",
                        line, text.strip()[:60]
                    )
                    return line
            return None
        except Exception as e:
            log.error("Erreur _findPrev : %s", e, exc_info=True)
            return None
