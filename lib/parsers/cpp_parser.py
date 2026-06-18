# =============================================================================
# lib/parsers/cpp_parser.py
# NotepadPlusPlus NVDA AppModule v4.0
#
# Parser de structures C/C++ pour la navigation de code.
#
# Reconnait :
#   - Fonctions libres      : type nom(params) {
#   - Methodes de classe    : Classe::methode(params) {
#   - Classes               : class Nom {  ou class Nom : public Base {
#   - Structures            : struct Nom {
#   - Namespaces            : namespace Nom {
#
# La detection C/C++ est plus complexe que Python car :
#   1. Pas d'indentation semantique (les accolades definissent les blocs)
#   2. Les declarations de fonctions peuvent s'etaler sur plusieurs lignes
#   3. Les prototypes (declarations sans corps) doivent etre ignores
#   4. Les macros #define et commentaires peuvent ressembler a des fonctions
#
# Approche retenue : detection par regex sur la ligne courante uniquement,
# en cherchant le pattern "type nom(" suivi de ")" et optionnellement "{".
# Les faux positifs sont filtres (commentaires, #define, etc.).
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
# Expressions regulieres C/C++
# =============================================================================

# Classe C++ ou struct
# Exemples :
#   class MyClass {
#   class MyClass : public Base {
#   struct MyStruct {
#   struct Point { int x, y; };
_RE_CLASS = re.compile(
    r'^\s*(?:class|struct)\s+\w+'
    r'(?:\s*:\s*(?:public|protected|private)\s+\w+)?'
    r'\s*[{;]?'
)

# Namespace C++
# Exemples : namespace std {   namespace MyApp {
_RE_NAMESPACE = re.compile(r'^\s*namespace\s+\w+\s*\{')

# Fonction ou methode C/C++
# Detection par heuristique : une ligne contenant une paire de parentheses
# avec un identifiant avant, et se terminant par { ou rien (pas par ; seul)
# Exemples :
#   void myFunc(int a, int b) {
#   int MyClass::method(const std::string& s) {
#   static bool helper() {
#   MyClass::MyClass() {        (constructeur)
#   MyClass::~MyClass() {       (destructeur)
#
# Exclusions :
#   - Lignes commencant par // ou *  (commentaires)
#   - Lignes commencant par #        (preprocesseur)
#   - Prototypes se terminant par ;  (sans corps)
#   - Appels de fonctions ordinaires (pas de type de retour apparent)
_RE_FUNCTION = re.compile(
    r'^\s*'
    r'(?!'               # debut du groupe de negative lookahead
    r'(?:if|for|while|switch|catch|return|else|do|case|delete|new)\b'
    r')'                 # fin du groupe d'exclusion des mots-cles
    r'(?:'
    r'(?:[\w:*&<>,\s]+?\s+)'  # type de retour (optionnel, greedy minimal)
    r')?'
    r'(?:\w+::)*'        # eventuel prefixe de classe (MyClass::)
    r'[~]?'              # eventuel destructeur (~)
    r'\w+'               # nom de la fonction
    r'\s*\('             # parenthese ouvrante
    r'[^;]*'             # parametres (tout sauf ; pour exclure les prototypes)
    r'\)'                # parenthese fermante
    r'[^;{]*'            # eventuel const, override, noexcept...
    r'(?:\{|$)'          # accolade ouvrante ou fin de ligne
)

# Marqueurs a exclure absolument (ne peuvent pas etre des fonctions)
_RE_EXCLUDE = re.compile(
    r'^\s*(?:'
    r'//|'              # commentaire C++ ligne
    r'/\*|'             # debut commentaire bloc
    r'\*|'              # ligne de commentaire bloc
    r'#|'               # preprocesseur (#include, #define, #ifdef...)
    r'}'                # accolade fermante seule
    r')'
)


class CppParser(BaseParser):
    """
    Parser de code C/C++ pour la navigation de structures.

    Herite de BaseParser et implemente la reconnaissance des structures
    syntaxiques C/C++ : fonctions libres, methodes de classe, classes,
    structs et namespaces.

    Note sur la precision : la detection par regex est une heuristique.
    Elle couvre les cas courants (code bien formate) mais peut avoir des
    faux positifs ou negatifs sur du code tres complexe ou mal formate.

    Parameters
    ----------
    sci : ScintillaWrapper
        Instance du wrappeur Scintilla deja initialise.

    Examples
    --------
    >>> parser = CppParser(sci)
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
            "C/C++"
        """
        return "C/C++"

    def isFunction(self, line_text):
        """
        Detecte une definition de fonction ou methode C/C++.

        Utilise une heuristique regex pour identifier les lignes
        qui ressemblent a une definition de fonction (avec corps).
        Les prototypes (termines par ;) et les mots-cles de controle
        (if, for, while...) sont exclus.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne ressemble a une definition de fonction.

        Examples
        --------
        >>> parser.isFunction("void myFunc(int a) {")     # True
        >>> parser.isFunction("int MyClass::method() {")  # True
        >>> parser.isFunction("void proto(int a);")       # False (prototype)
        >>> parser.isFunction("if (condition) {")         # False (mot-cle)
        >>> parser.isFunction("// void fake() {")         # False (commentaire)
        """
        stripped = line_text.strip()
        if not stripped:
            return False
        # Exclure les lignes de commentaire et preprocesseur
        if _RE_EXCLUDE.match(line_text):
            return False
        # Tester le pattern de fonction
        return bool(_RE_FUNCTION.match(line_text))

    def isClass(self, line_text):
        """
        Detecte une declaration de classe ou structure C/C++.

        Reconnait 'class' et 'struct', avec heritage optionnel.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est une declaration class ou struct.

        Examples
        --------
        >>> parser.isClass("class Foo {")                  # True
        >>> parser.isClass("struct Point { int x, y; };") # True
        >>> parser.isClass("class Bar : public Base {")   # True
        >>> parser.isClass("// class Fake {")             # False
        """
        stripped = line_text.strip()
        if not stripped:
            return False
        if _RE_EXCLUDE.match(line_text):
            return False
        return bool(_RE_CLASS.match(line_text))

    def isNamespace(self, line_text):
        """
        Detecte une declaration de namespace C++.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est une declaration namespace.
        """
        stripped = line_text.strip()
        if not stripped:
            return False
        if _RE_EXCLUDE.match(line_text):
            return False
        return bool(_RE_NAMESPACE.match(line_text))

    def isClassOrNamespace(self, line_text):
        """
        Detecte une declaration de classe, struct ou namespace.

        Utile pour la navigation F7 qui groupe ces structures.

        Parameters
        ----------
        line_text : str
            Texte de la ligne (sans \\n).

        Returns
        -------
        bool
            True si la ligne est une declaration class, struct ou namespace.
        """
        return self.isClass(line_text) or self.isNamespace(line_text)
