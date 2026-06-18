# =============================================================================
# lib/parsers/python_parser.py
# NotepadPlusPlus NVDA AppModule v4.0
#
# Parser de structures Python pour la navigation de code.
#
# Reconnait :
#   - Fonctions et methodes : def nom(...) et async def nom(...)
#   - Classes               : class Nom(...):
#   - Bloc principal        : if __name__ == '__main__':
#
# Auteurs : ECAM Rennes / My Human Kit
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

import re
import logging

from lib.parsers.base_parser import BaseParser

log = logging.getLogger(__name__)

# =============================================================================
# Expressions regulieres Python
# =============================================================================

# Fonction ou methode Python (avec support async def)
# Exemples : def foo():  async def bar(x, y):  def __init__(self):
_RE_FUNCTION = re.compile(r'^\s*(async\s+)?def\s+\w+')

# Classe Python
# Exemples : class Foo:  class Bar(Base):  class MyClass(A, B):
_RE_CLASS = re.compile(r'^\s*class\s+\w+')

# Bloc principal Python
# Exemples : if __name__ == '__main__':  if __name__ == "__main__":
_RE_MAIN = re.compile(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:')


class PythonParser(BaseParser):
    """
    Parser de code Python pour la navigation de structures.

    Herite de BaseParser et implemente la reconnaissance des structures
    syntaxiques Python : fonctions, methodes (def / async def) et classes.

    Parameters
    ----------
    sci : ScintillaWrapper
        Instance du wrappeur Scintilla deja initialise.

    Examples
    --------
    >>> parser = PythonParser(sci)
    >>> current_line = sci.getCurrentLineNumber()
    >>> next_func = parser.findNextFunction(current_line)
    >>> if next_func is not None:
    ...     sci.gotoLine(next_func)
    """

    def getLanguageName(self):
        """
        Retourne le nom du langage.

        Returns
        -------
        str
            "Python"
        """
        return "Python"

    def isFunction(self, line_text):
        """
        Detecte une declaration de fonction ou methode Python.

        Reconnait def et async def, a n'importe quel niveau d'indentation.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est une declaration def ou async def.

        Examples
        --------
        >>> parser.isFunction("def foo():")           # True
        >>> parser.isFunction("    async def bar():") # True
        >>> parser.isFunction("    x = def_value")    # False
        """
        return bool(_RE_FUNCTION.match(line_text))

    def isClass(self, line_text):
        """
        Detecte une declaration de classe Python.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est une declaration class.

        Examples
        --------
        >>> parser.isClass("class Foo:")           # True
        >>> parser.isClass("class Bar(Base):")     # True
        >>> parser.isClass("    x = class_name")  # False
        """
        return bool(_RE_CLASS.match(line_text))

    def isMain(self, line_text):
        """
        Detecte le bloc principal Python (if __name__ == '__main__':).

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est un bloc if __name__ == '__main__'.
        """
        return bool(_RE_MAIN.match(line_text))

    def findMain(self):
        """
        Trouve le bloc if __name__ == '__main__' dans tout le document.

        La recherche part toujours du debut du fichier (ligne 0),
        independamment de la position courante du curseur.

        Returns
        -------
        int or None
            Numero de ligne (base 0) du bloc principal, ou None si absent.
        """
        try:
            total = self._sci.getLineCount()
            for line in range(0, total):
                text = self._sci.getLine(line).rstrip("\r\n")
                if self.isMain(text):
                    log.debug(
                        "Bloc principal trouve a la ligne %d", line
                    )
                    return line
            log.debug("Bloc if __name__ == '__main__' non trouve")
            return None
        except Exception as e:
            log.error("Erreur findMain : %s", e, exc_info=True)
            return None
