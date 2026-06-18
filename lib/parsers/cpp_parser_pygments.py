# =============================================================================
# lib/parsers/cpp_parser_pygments.py
# NotepadPlusPlus NVDA AppModule v4.0
#
# Parser C/C++ base sur pygments pour la detection precise des structures.
#
# Utilise le lexer CppLexer de pygments pour tokeniser le code source et
# identifier les fonctions, methodes et classes avec une precision bien
# superieure aux expressions regulieres.
#
# Avantages sur les regex :
#   - Ignore automatiquement les commentaires (// et /* */)
#   - Ignore le contenu des chaines de caracteres
#   - Detecte correctement les methodes de classe (MonCapteur::lire)
#   - Distingue les definitions de fonctions des appels de fonctions
#   - Supporte les templates, les namespaces, les qualificateurs
#
# Token.Name.Function : fonctions libres et methodes de classe
# Token.Name.Class    : declarations de classes et structs
#
# Auteurs : ECAM Rennes / My Human Kit
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.0"
__date__ = "2026-06-03"

import logging
import re

log = logging.getLogger(__name__)

# pygments est importe de facon differee (lazy) dans __init__
# pour eviter les problemes d'ordre de chargement des modules.
# Le sys.path doit etre configure avant que ce module soit utilise.
PYGMENTS_AVAILABLE = False  # sera mis a True dans __init__ si import reussi


class CppParserPygments:
    """
    Parser C/C++ base sur pygments pour la detection de structures de code.

    Tokenise le code source complet et identifie les fonctions, methodes
    et classes en exploitant les types de tokens pygments.

    Parameters
    ----------
    Aucun parametre — la classe est instanciee sans argument.

    Attributes
    ----------
    _lexer : CppLexer or None
        Instance du lexer pygments C++.

    Examples
    --------
    >>> parser = CppParserPygments()
    >>> elements = parser.parseElements(code_source)
    >>> for elem in elements:
    ...     print(elem['type'], elem['name'], elem['line'])
    """

    def __init__(self):
        """Initialise le parser avec le lexer pygments C++."""
        global PYGMENTS_AVAILABLE
        self._lexer = None
        self._Token = None

        # Import lazy de pygments avec fallback sur le lexer embarque.
        # pygments de base est dans library.zip de NVDA, mais
        # pygments.lexers.c_cpp peut etre absent (version allégée).
        # On embarque c_cpp.py dans lib/pygments_lexers/ comme fallback.
        try:
            import pygments as _pygments
            from pygments.token import Token as _Token

            # Tenter d'importer CppLexer depuis pygments standard
            try:
                from pygments.lexers import CppLexer as _CppLexer
                log.warning("NppAccessNav : CppLexer depuis pygments standard")
            except ImportError:
                # Fallback : utiliser notre c_cpp.py embarque
                import sys as _sys2
                import os as _os3
                # Ajouter lib/pygments_lexers/ au path
                _addon_root2 = _os3.path.dirname(
                    _os3.path.dirname(_os3.path.dirname(_os3.path.abspath(__file__)))
                )
                _lex_dir = _os3.path.join(_addon_root2, "lib", "pygments_lexers")
                if _lex_dir not in _sys2.path:
                    _sys2.path.insert(0, _lex_dir)
                from c_cpp import CppLexer as _CppLexer
                log.warning("NppAccessNav : CppLexer depuis lexer embarque")

            self._lexer = _CppLexer()
            self._Token = _Token
            self._pygments = _pygments
            PYGMENTS_AVAILABLE = True
            log.warning(
                "pygments %s charge avec succes pour le parser C/C++",
                _pygments.__version__
            )
        except ImportError as e:
            PYGMENTS_AVAILABLE = False
            log.warning("pygments non disponible : %s", e)

    def isAvailable(self):
        """
        Verifie si pygments est disponible.

        Returns
        -------
        bool
            True si pygments est installe et le lexer est pret.
        """
        return PYGMENTS_AVAILABLE and self._lexer is not None

    def parseElements(self, source_code):
        """
        Analyse le code source et retourne la liste de tous les elements
        (fonctions et classes) avec leur numero de ligne.

        Parameters
        ----------
        source_code : str
            Code source C/C++ complet du fichier.

        Returns
        -------
        list of dict
            Liste d'elements tries par numero de ligne.
            Chaque element est un dict :
            {
                'type' : 'function' ou 'class',
                'name' : str,          nom de la fonction ou classe
                'line' : int,          numero de ligne (base 0)
            }
        """
        if not self.isAvailable():
            log.warning("parseElements : pygments non disponible")
            return []

        elements = []

        try:
            # Tokeniser le code source complet
            Token = self._Token
            tokens = list(self._pygments.lex(source_code, self._lexer))

            # Construire une table de correspondance position -> ligne
            # (pygments retourne des positions en octets)
            line_map = self._buildLineMap(source_code)

            # Parcourir les tokens et collecter les elements pertinents
            for i, (ttype, value) in enumerate(tokens):
                if not value.strip():
                    continue

                # Detecter les definitions de fonctions/methodes
                # Token.Name.Function est emis pour les noms de fonctions
                # qui sont suivis d'une parenthese ouvrante
                if ttype is Token.Name.Function:
                    # Verifier que c'est bien une definition (suivie de '(')
                    next_meaningful = self._nextMeaningfulToken(tokens, i + 1)
                    if next_meaningful and next_meaningful[0] is Token.Punctuation \
                            and next_meaningful[1] == '(':
                        # Calculer le numero de ligne
                        line_num = self._getLineForToken(tokens, i, line_map, source_code)
                        elements.append({
                            'type': 'function',
                            'name': value,
                            'line': line_num,
                        })
                        log.debug(
                            "Fonction trouvee : %s (ligne %d)", value, line_num
                        )

                # Detecter les declarations de classes et structs
                # Token.Name.Class est emis pour les noms apres 'class' ou 'struct'
                elif ttype is Token.Name.Class:
                    line_num = self._getLineForToken(tokens, i, line_map, source_code)
                    elements.append({
                        'type': 'class',
                        'name': value,
                        'line': line_num,
                    })
                    log.debug(
                        "Classe trouvee : %s (ligne %d)", value, line_num
                    )

        except Exception as e:
            log.error("parseElements : erreur pygments : %s", e, exc_info=True)

        # Trier par numero de ligne
        elements.sort(key=lambda x: x['line'])
        return elements

    def findNextFunction(self, source_code, current_line):
        """
        Trouve la prochaine definition de fonction apres la ligne courante.

        Parameters
        ----------
        source_code : str
            Code source complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        dict or None
            Element {'type', 'name', 'line'} ou None si aucun trouve.
        """
        elements = self.parseElements(source_code)
        for elem in elements:
            if elem['type'] == 'function' and elem['line'] > current_line:
                return elem
        return None

    def findPrevFunction(self, source_code, current_line):
        """
        Trouve la definition de fonction precedant la ligne courante.

        Parameters
        ----------
        source_code : str
            Code source complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        dict or None
            Element ou None si aucun trouve.
        """
        elements = self.parseElements(source_code)
        candidates = [e for e in elements
                      if e['type'] == 'function' and e['line'] < current_line]
        return candidates[-1] if candidates else None

    def findNextClass(self, source_code, current_line):
        """
        Trouve la prochaine declaration de classe apres la ligne courante.

        Parameters
        ----------
        source_code : str
            Code source complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        dict or None
            Element ou None si aucun trouve.
        """
        elements = self.parseElements(source_code)
        for elem in elements:
            if elem['type'] == 'class' and elem['line'] > current_line:
                return elem
        return None

    def findPrevClass(self, source_code, current_line):
        """
        Trouve la declaration de classe precedant la ligne courante.

        Parameters
        ----------
        source_code : str
            Code source complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        dict or None
            Element ou None si aucun trouve.
        """
        elements = self.parseElements(source_code)
        candidates = [e for e in elements
                      if e['type'] == 'class' and e['line'] < current_line]
        return candidates[-1] if candidates else None

    # =========================================================================
    # Methodes privees utilitaires
    # =========================================================================

    def _buildLineMap(self, source_code):
        """
        Construit une liste des positions de debut de chaque ligne.

        Parameters
        ----------
        source_code : str
            Code source complet.

        Returns
        -------
        list of int
            line_map[i] = position du premier caractere de la ligne i.
        """
        line_map = [0]
        for i, ch in enumerate(source_code):
            if ch == '\n':
                line_map.append(i + 1)
        return line_map

    def _getLineForToken(self, tokens, token_index, line_map, source_code):
        """
        Calcule le numero de ligne (base 0) d'un token.

        Reconstitue la position du token en parcourant les tokens precedents.

        Parameters
        ----------
        tokens : list
            Liste complete des tokens pygments.
        token_index : int
            Index du token dans la liste.
        line_map : list of int
            Table position -> ligne.
        source_code : str
            Code source complet.

        Returns
        -------
        int
            Numero de ligne (base 0).
        """
        # Calculer la position absolue du token dans le source
        pos = 0
        for i in range(token_index):
            pos += len(tokens[i][1])

        # Trouver le numero de ligne via line_map (recherche dichotomique)
        lo, hi = 0, len(line_map) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_map[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def _nextMeaningfulToken(self, tokens, start_index):
        """
        Retourne le prochain token non-espace/non-vide depuis start_index.

        Parameters
        ----------
        tokens : list
            Liste des tokens.
        start_index : int
            Index de depart.

        Returns
        -------
        tuple or None
            (ttype, value) du prochain token significatif, ou None.
        """
        for i in range(start_index, min(start_index + 5, len(tokens))):
            ttype, value = tokens[i]
            if value.strip():
                return (ttype, value)
        return None
