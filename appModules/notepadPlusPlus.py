# Appmodule NVDA for Notepad++ v4.0
# Navigation de code accessible pour developpeurs Python sous Notepad++
# 2026-06-03

__version__ = "4.2" 
__date__ = "2026/06/03" 

import appModuleHandler
import logging
import speech
import textInfos
import gui  # Pour les boîtes de dialogue
import api
import wx
import subprocess  # Pour lancer un terminal
import os  # Pour manipuler les chemins de fichiers
import keyboardHandler  # Pour simuler l'appui sur la touche Suppr
import tempfile  # Pour créer des fichiers temporaires

import re 

# Configurer sys.path pour que lib/ soit importable
import sys as _sys
import os as _os2
import logging as _lg_cpp

_appmodules_dir = _os2.path.dirname(_os2.path.abspath(__file__))
_addon_root     = _os2.path.dirname(_appmodules_dir)
if _addon_root not in _sys.path:
    _sys.path.insert(0, _addon_root)

# Verifier que lib/ existe physiquement
_lib_dir      = _os2.path.join(_addon_root, "lib")
_parsers_dir  = _os2.path.join(_lib_dir, "parsers")
_parser_file  = _os2.path.join(_parsers_dir, "cpp_parser_pygments.py")

_lg_cpp.getLogger(__name__).warning(
    "NppAccessNav PATH : __file__=%s | addon_root=%s | lib_exists=%s | parser_exists=%s",
    __file__, _addon_root,
    _os2.path.isdir(_lib_dir),
    _os2.path.isfile(_parser_file)
)

# Chercher pygments dans l'installation NVDA et l'ajouter au sys.path
# pygments est installe dans NVDA mais pas forcement visible depuis les addons
def _find_nvda_pygments():
    """
    Ajoute library.zip de NVDA au sys.path pour rendre pygments accessible.

    Dans NVDA, les modules Python (dont pygments) sont embarques dans
    library.zip — un archive ZIP dans le dossier d installation NVDA.
    Python sait importer depuis un ZIP si celui-ci est dans sys.path.
    """
    import zipimport

    # Chemins de library.zip selon l'installation NVDA
    library_zip_paths = [
        "C:\\Program Files\\NVDA\\library.zip",
        "C:\\Program Files (x86)\\NVDA\\library.zip",
    ]

    for zip_path in library_zip_paths:
        if not _os2.path.isfile(zip_path):
            continue

        # Verifier que pygments est bien dans ce zip
        try:
            zi = zipimport.zipimporter(zip_path)
            # Tenter de trouver pygments dans le zip
            import zipfile
            with zipfile.ZipFile(zip_path, "r") as zf:
                has_pygments = any(
                    n.startswith("pygments/") or n.startswith("pygments\\")
                    for n in zf.namelist()
                )
            if has_pygments:
                if zip_path not in _sys.path:
                    _sys.path.insert(0, zip_path)
                _lg_cpp.getLogger(__name__).warning(
                    "NppAccessNav : pygments trouve dans %s", zip_path
                )
                return True
        except Exception as ze:
            _lg_cpp.getLogger(__name__).warning(
                "NppAccessNav : erreur lecture %s : %s", zip_path, ze
            )

    _lg_cpp.getLogger(__name__).warning(
        "NppAccessNav : library.zip introuvable ou sans pygments"
    )
    return False

_find_nvda_pygments()

# Parser C/C++ base sur pygments
try:
    from lib.parsers.cpp_parser_pygments import CppParserPygments as _CppParser
    _CPP_PARSER = _CppParser()
    _CPP_PARSER_AVAILABLE = _CPP_PARSER.isAvailable()
    _lg_cpp.getLogger(__name__).warning(
        "NppAccessNav : parser C++ OK, pygments=%s", _CPP_PARSER_AVAILABLE
    )
except Exception as _e_cpp:
    _lg_cpp.getLogger(__name__).warning(
        "NppAccessNav : ERREUR parser C++ : %s", str(_e_cpp)
    )
    _CPP_PARSER = None
    _CPP_PARSER_AVAILABLE = False


# Import du gestionnaire de signets
try:
    from lib.bookmarks import getManager as _getBookmarkManager
    _BM_AVAILABLE = True
    import logging as _lg_bm
    _lg_bm.getLogger(__name__).warning("NppAccessNav : BookmarkManager charge OK")
except Exception as _e_bm:
    import logging as _lg_bm
    _lg_bm.getLogger(__name__).warning(
        "NppAccessNav : ERREUR chargement BookmarkManager : %s", str(_e_bm)
    )
    _getBookmarkManager = None
    _BM_AVAILABLE = False

# Import de la fenetre de navigation
try:
    from lib.nav_dialog import NavigationDialog as _NavigationDialog
    _NAV_DIALOG_AVAILABLE = True
except Exception as _e_nav:
    _NavigationDialog = None
    _NAV_DIALOG_AVAILABLE = False


# =============================================================================
# Expressions regulieres — Python
# =============================================================================
_RE_PY_FUNCTION = re.compile(r"^\s*(async\s+)?def\s+\w+")
_RE_PY_CLASS    = re.compile(r"^\s*class\s+\w+")

# =============================================================================
# Expressions regulieres — C/C++
# Detecte les definitions de fonctions (avec corps {), pas les prototypes (;)
# Exclut mots-cles de controle (if, for, while...) et commentaires
# =============================================================================
_RE_CPP_EXCLUDE = re.compile(
    r"^\s*(?://|/\*|\*|#|}|"
    r"(?:if|for|while|switch|catch|else|do|case|return|delete|new)\b)"
)
_RE_CPP_FUNCTION = re.compile(
    r"^\s*"
    r"(?!(?:if|for|while|switch|catch|return|else|do|case|delete|new)\b)"
    r"(?:[\w:*&<>,\s]+?\s+)?"
    r"(?:\w+::)*"
    r"[~]?\w+"
    r"\s*\("
    r"[^;]*\)"
    r"[^;{]*"
    r"(?:\{|$)"
)
_RE_CPP_CLASS = re.compile(
    r"^\s*(?:class|struct)\s+\w+"
    r"(?:\s*:\s*(?:public|protected|private)\s+\w+)?"
    r"\s*[{;]?"
)

import os as _os

# =============================================================================
# Detection du langage par extension de fichier
# =============================================================================
_LANG_EXTENSIONS = {
    "python" : {".py", ".pyw", ".pyi"},
    "cpp"    : {".c", ".cpp", ".cxx", ".h", ".hpp", ".ino"},
    "vhdl"   : {".vhd", ".vhdl"},
}

def _detect_lang_from_path(file_path):
    """Detecte le langage depuis l'extension du fichier."""
    if not file_path:
        return "unknown"
    ext = _os.path.splitext(file_path)[1].lower()
    for lang, exts in _LANG_EXTENSIONS.items():
        if ext in exts:
            return lang
    return "unknown"


# Configuration du logger
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)  # Utiliser le niveau DEBUG pour voir tous les logs
handler = logging.StreamHandler()  # Afficher les logs dans la console (le débogueur de NVDA)
handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
log.addHandler(handler)

# TAB_SIZE_IN_SPACE = 4  # Nombre d'espaces équivalents à une tabulation

# Heritage du module NVDA integre pour Notepad++ (compatibilite 64 bits)
try:
    from nvdaBuiltin.appModules.notepadPlusPlus import AppModule as _NppBase
except ImportError:
    _NppBase = appModuleHandler.AppModule

class AppModule(_NppBase):
    """
    Module complémentaire NVDA pour Notepad++.

    Ce module étend les fonctionnalités de NVDA dans l'éditeur Notepad++ pour le développement enlangage python, 
    en ajoutant
    plusieurs raccourcis clavier destinés à faciliter la navigation et la compréhension
    du code source pour les utilisateurs aveugles ou malvoyants.

    Fonctions principales :
    - Annoncer le numéro de ligne courant (F4)
    - Annoncer le niveau d'indentation de la ligne courante (Ctrl+F4)
    - Aller à la classe suivante ou précédente (F7 / Maj+F7)
    - Aller à la méthode suivante ou précédente (F2 / Maj+F2
    - sélectionner la classe courante (ctrl+maj+r)
    - selctionner la methode courante (ctrl+r)
    - etc...

    Attributs
    ----------
    edit : NVDAObject or None
        Objet d'édition courant détecté par NVDA. Il est mis à jour automatiquement.
    appModuleName : str
        Nom de l'application hôte (normalement 'notepad++').
    
    attribut de classe 
    self.TAB_SIZE_IN_SPACE : int, optional
        Constante définissant l'équivalence entre tabulation logique et nombre d'espaces (par défaut : 4).

    Méthodes
    ---------
    __init__(self, *args, **kwargs)
        Initialise le module complémentaire et logge le démarrage dans le journal NVDA.

    script_sayCurrentLineNumber(self, gesture)
        Annonce le numéro de la ligne où se trouve le curseur.

    script_goToNextMethod(self, gesture)
        Déplace le curseur vers la méthode suivante (détection basée sur des motifs de syntaxe).

    script_goToPreviousMethod(self, gesture)
        Déplace le curseur vers la méthode précédente.

    script_announceCurrentIndentationLevel(self, gesture)
        Annonce le niveau d'indentation logique (calculé selon l'attribut de classe self.TAB_SIZE_IN_SPACE).
        Détecte les erreurs si l'indentation n'est pas un multiple.

    _getIndentationLevel(self, lineText)
        Retourne le nombre d'espaces en début de ligne.

    Notes
    -----
    Ce module est spécifique à l’éditeur Notepad++ et peut ne pas fonctionner correctement
    dans d'autres éditeurs ou environnements.

    Voir aussi
    ----------
    appModuleHandler.AppModule : Classe de base des modules NVDA.
    NVDAObject : Objet de contrôle du curseur dans NVDA.
    textInfos.POSITION_CARET : Position du curseur dans le texte.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialise le module NVDA pour Notepad++.

        Parameters
        ----------
        *args : tuple
            Arguments positionnels.
        **kwargs : dict
            Arguments nommés.
        """
        super().__init__(*args, **kwargs)
        log.debug("Module Notepad++ chargé avec succès.")
        self.edit = None  # Initialiser l'objet d'édition
        self._current_lang = 'unknown'  # Langage du fichier courant
        self.TAB_SIZE_IN_SPACE = 4  # nb of spaces per tab 


    def event_gainFocus(self, obj, nextHandler):
        """
        Enregistre l'objet d'édition lorsque Notepad++ obtient le focus.

        Parameters
        ----------
        obj : object
            L'objet NVDA ayant reçu le focus.
        nextHandler : function
            Fonction à appeler après le traitement de l'événement.
        """
        self.edit = obj  # Enregistrer l’objet d’édition

        # Detecter le langage du fichier courant via son nom/chemin
        try:
            file_path = None

            # Lire le titre de la fenetre Notepad++ via Win32.
            # Le titre est de la forme "chemin\fichier.ext - Notepad++"
            # C'est la source la plus fiable pour obtenir l'extension.
            try:
                import ctypes
                import ctypes.wintypes
                buf = ctypes.create_unicode_buffer(512)
                hwnd = getattr(obj, "windowHandle", None)
                if hwnd:
                    # Remonter jusqu'a la fenetre principale (qui porte le titre)
                    parent = hwnd
                    while True:
                        p = ctypes.windll.user32.GetParent(parent)
                        if not p:
                            break
                        parent = p
                    ctypes.windll.user32.GetWindowTextW(parent, buf, 512)
                    title = buf.value
                    # Extraire le chemin du fichier depuis le titre
                    # Format : "chemin\fichier.ext - Notepad++" (avec ou sans *)
                    m = re.match(r"^(.+?)\s*\*?\s*-\s*Notepad\+\+.*$", title)
                    if m:
                        file_path = m.group(1).strip()
            except Exception:
                pass

            # Fallback : attributs de l'objet NVDA
            if not file_path:
                for attr in ("name", "windowText", "description"):
                    val = getattr(obj, attr, None)
                    if val and isinstance(val, str) and "." in val:
                        file_path = val
                        break

            new_lang = _detect_lang_from_path(file_path)
            if new_lang != self._current_lang:
                self._current_lang = new_lang
                lang_names = {
                    "python" : "Python",
                    "cpp"    : "C/C++",
                    "vhdl"   : "VHDL",
                    "unknown": "type non reconnu",
                }
                import speech as _sp
                _sp.speakMessage(lang_names.get(new_lang, "type non reconnu"))
        except Exception as _e:
            import logging as _lg
            _lg.getLogger(__name__).error("lang detect : %s", _e, exc_info=True)

        nextHandler()


    def event_loseFocus(self, obj, nextHandler):
        """
        Nettoie l'objet d'édition lorsque Notepad++ perd le focus.

        Parameters
        ----------
        obj : object
            L'objet NVDA ayant perdu le focus.
        nextHandler : function
            Fonction à appeler après le traitement de l'événement.
        """
        self.edit = None  # Nettoyer l'objet d'édition
        nextHandler()

    def _getIndentationLevel(self, lineText):
        """
        Retourne le niveau d'indentation d'une ligne de texte.le nombre retourné est un nombre d'espaces en début de ligne. 

        Parameters
        ----------
        lineText : str
            La ligne de texte à analyser.

        Returns
        -------
        int
            Le niveau d'indentation de la ligne en nombre d'espaces en début de ligne avec le premier caractère de la ligne de code courante.
        """
        return len(lineText) - len(lineText.lstrip())

####################################################################################################
#
#    SCRIPTS 
#
####################################################################################################    
    def _getFullText(self):
        """
        Retourne le texte complet du document via makeTextInfo.

        Returns
        -------
        str
            Contenu complet du fichier, ou chaine vide si erreur.
        """
        if not self.edit:
            return ""
        try:
            info = self.edit.makeTextInfo(textInfos.POSITION_ALL)
            return info.text
        except Exception as e:
            log.error("_getFullText : %s", e, exc_info=True)
            return ""

    def _gotoLineNumber(self, target_line_0based):
        """
        Deplace le curseur vers une ligne donnee (base 0) via makeTextInfo.

        Parameters
        ----------
        target_line_0based : int
            Numero de ligne cible (base 0).
        """
        if not self.edit:
            return
        try:
            info = self.edit.makeTextInfo(textInfos.POSITION_FIRST)
            info.move(textInfos.UNIT_LINE, target_line_0based)
            info.expand(textInfos.UNIT_LINE)
            info.updateCaret()
            # Positionner apres l'indentation
            offset = len(info.text) - len(info.text.lstrip(' \t'))
            info.move(textInfos.UNIT_CHARACTER, offset)
            info.updateCaret()
        except Exception as e:
            log.error("_gotoLineNumber : %s", e, exc_info=True)

    def _getCurrentLineNumber(self):
        """
        Retourne le numero de ligne courante (base 0) via makeTextInfo.

        Returns
        -------
        int
            Numero de ligne (base 0), ou 0 si erreur.
        """
        if not self.edit:
            return 0
        try:
            caret = self.edit.makeTextInfo(textInfos.POSITION_CARET)
            start = self.edit.makeTextInfo(textInfos.POSITION_FIRST)
            line_num = 0
            info = start.copy()
            while info.bookmark.startOffset < caret.bookmark.startOffset:
                if info.move(textInfos.UNIT_LINE, 1) == 0:
                    break
                line_num += 1
            return line_num
        except Exception as e:
            log.error("_getCurrentLineNumber : %s", e, exc_info=True)
            return 0

    def _navigateCpp(self, direction, element_type):
        """
        Navigation C/C++ via le parser pygments.

        Parse le fichier complet avec pygments et navigue vers l'element
        suivant ou precedent selon la direction.

        Parameters
        ----------
        direction : str
            "next" ou "prev".
        element_type : str
            "function" ou "class".
        """
        if not self.edit:
            speech.speakMessage("Aucun editeur actif.")
            return

        if not _CPP_PARSER_AVAILABLE:
            speech.speakMessage("Parser C/C++ non disponible (pygments requis).")
            return

        source = self._getFullText()
        if not source:
            speech.speakMessage("Fichier vide.")
            return

        current_line = self._getCurrentLineNumber()
        log.debug("_navigateCpp : direction=%s type=%s ligne=%d",
                  direction, element_type, current_line)

        if element_type == "function":
            if direction == "next":
                elem = _CPP_PARSER.findNextFunction(source, current_line)
                not_found = "Aucune fonction suivante trouvee."
            else:
                elem = _CPP_PARSER.findPrevFunction(source, current_line)
                not_found = "Aucune fonction precedente trouvee."
        else:  # class
            if direction == "next":
                elem = _CPP_PARSER.findNextClass(source, current_line)
                not_found = "Aucune classe suivante trouvee."
            else:
                elem = _CPP_PARSER.findPrevClass(source, current_line)
                not_found = "Aucune classe precedente trouvee."

        if elem:
            self._gotoLineNumber(elem['line'])
            label = "Fonction" if element_type == "function" else "Classe"
            speech.speakMessage(f"{label} : {elem['name']} ligne {elem['line'] + 1}")
            log.debug("_navigateCpp : %s %s ligne %d", label, elem['name'], elem['line'])
        else:
            speech.speakMessage(not_found)

    def _isFunction(self, line_text):
        """
        Teste si une ligne est une declaration de fonction selon le langage courant.

        Parameters
        ----------
        line_text : str
            Texte de la ligne a tester.

        Returns
        -------
        bool
            True si la ligne est une declaration de fonction/methode.
        """
        stripped = line_text.strip()
        if not stripped:
            return False
        if self._current_lang == "cpp":
            if _RE_CPP_EXCLUDE.match(line_text):
                return False
            return bool(_RE_CPP_FUNCTION.match(line_text))
        else:
            # Python par defaut (ou langage inconnu : on tente Python)
            return bool(_RE_PY_FUNCTION.match(line_text))

    def _isClass(self, line_text):
        """
        Teste si une ligne est une declaration de classe selon le langage courant.

        Parameters
        ----------
        line_text : str
            Texte de la ligne a tester.

        Returns
        -------
        bool
            True si la ligne est une declaration de classe/struct.
        """
        stripped = line_text.strip()
        if not stripped:
            return False
        if self._current_lang == "cpp":
            if _RE_CPP_EXCLUDE.match(line_text):
                return False
            return bool(_RE_CPP_CLASS.match(line_text))
        else:
            return bool(_RE_PY_CLASS.match(line_text))

    def script_moveToNextFunction(self, gesture):
        """
        Déplace le curseur à la déclaration de la fonction Python suivante.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (F2)")

        # Dispatcher selon le langage detecte
        if self._current_lang == "cpp":
            self._navigateCpp("next", "function")
            return

        # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLine = caretInfo.bookmark.startOffset  # Position de départ de la ligne actuelle


                # Parcourir les lignes suivantes pour trouver la déclaration de fonction
                while True:
                    # Déplacer le curseur à la ligne suivante
                    caretInfo.move(textInfos.UNIT_LINE, 1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text.strip()  # Obtenir le texte de la ligne


                    # Vérifier si la ligne commence par "def " (déclaration de fonction Python)
                    # FLB 2025-06-07
                    # if lineText.startswith("def "):
                    if self._isFunction(lineText):
                        # Déplacer le curseur au début de la ligne
                        caretInfo.updateCaret()
                        # FLB 1 : deplacement du curseur au niveau de def 
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' '))
                        # lineText
                        # log.debug(f"Line text : {caretInfo.text}")
                        # log.debug(f"Len : {len(caretInfo.text)}")
                        # log.debug(f"caret offset : {caretOffset}")
                        # move caret close to def  
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret()
                        
                        log.debug(f"Déclaration de fonction suivante trouvée : {lineText}")
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break


                    # Si on atteint la fin du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset <= currentLine:
                        log.debug("Aucune déclaration de fonction suivante trouvée.")
                        speech.speakMessage("Aucune déclaration de fonction suivante trouvée.")
                        break


                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset


            except Exception as e:
                log.error(f"Erreur lors de la recherche de la déclaration de fonction suivante : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToNextFunction.__doc__ = _("Déplace le curseur vers la première ligne de la déclaration de fonction Python suivante.")
    script_moveToNextFunction.category = "Notepad++"

####################################################################################################
    def script_moveToPreviousFunction(self, gesture):
        """
        Déplace le curseur à la déclaration de la fonction Python précédente.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (Shift+F2)")


        # Dispatcher selon le langage detecte
        if self._current_lang == "cpp":
            self._navigateCpp("prev", "function")
            return


        # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLine = caretInfo.bookmark.startOffset  # Position de départ de la ligne actuelle


                # Parcourir les lignes précédentes pour trouver la déclaration de fonction
                while True:
                    # Déplacer le curseur à la ligne précédente
                    caretInfo.move(textInfos.UNIT_LINE, -1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text.strip()  # Obtenir le texte de la ligne


                    # Vérifier si la ligne commence par "def " (déclaration de fonction Python)
                    # FLB 2025-06-07
                    # if lineText.startswith("def "):
                    if self._isFunction(lineText):
                        # Déplacer le curseur au début de la ligne
                        caretInfo.updateCaret()
                        log.debug(f"Déclaration de fonction précédente trouvée : {lineText}")
                        # FLB 2 : deplacement du curseur vers le haut 
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' ')) 
                        # move caret close to def  
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret()
                        
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break


                    # Si on atteint le début du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset >= currentLine:
                        log.debug("Aucune déclaration de fonction précédente trouvée.")
                        speech.speakMessage("Aucune déclaration de fonction précédente trouvée.")
                        break


                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset


            except Exception as e:
                log.error(f"Erreur lors de la recherche de la déclaration de fonction précédente : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToPreviousFunction.__doc__ = _("Déplace le curseur vers la première ligne de la déclaration de fonction Python précédente.")
    script_moveToPreviousFunction.category = "Notepad++"

####################################################################################################
    def script_moveToNextClass(self, gesture):
        """
        Déplace le curseur à la déclaration de la classe Python suivante.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
    # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (F7)")

        # F7 cherche les classes — supporte en C/C++ via pygments (class, struct)
        if self._current_lang == "cpp":
            self._navigateCpp("next", "class")
            return

    # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLine = caretInfo.bookmark.startOffset  # Position de départ de la ligne actuelle


                # Parcourir les lignes suivantes pour trouver la déclaration de classe
                while True:
                    # Déplacer le curseur à la ligne suivante
                    caretInfo.move(textInfos.UNIT_LINE, 1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text.strip()  # Obtenir le texte de la ligne


                    # Vérifier si la ligne commence par "class " (déclaration de classe Python)
                    if self._isClass(lineText):
                        # Déplacer le curseur au début de la ligne
                        caretInfo.updateCaret()
                        # FLB 3 : deplacement du curseur vers le base definition de classe 
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' ')) 
                        # move caret close to def  
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret() 

                        log.debug(f"Déclaration de classe suivante trouvée : {lineText}")
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break


                    # Si on atteint la fin du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset <= currentLine:
                        log.debug("Aucune déclaration de classe suivante trouvée.")
                        speech.speakMessage("Aucune déclaration de classe suivante trouvée.")
                        break


                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset


            except Exception as e:
                log.error(f"Erreur lors de la recherche de la déclaration de classe suivante : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToNextClass.__doc__ = _("Déplace le curseur vers la première ligne de la déclaration de classe Python suivante.")
    script_moveToNextClass.category = "Notepad++"

####################################################################################################
    def script_moveToPreviousClass(self, gesture):
        """
        Déplace le curseur vers la première ligne de la déclaration de classe Python précédente.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (Shift+F7)")

        # Dispatcher selon le langage detecte
        if self._current_lang == "cpp":
            self._navigateCpp("prev", "class")
            return



        # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLine = caretInfo.bookmark.startOffset  # Position de départ de la ligne actuelle


                # Parcourir les lignes précédentes pour trouver la déclaration de classe
                while True:
                    # Déplacer le curseur à la ligne précédente
                    caretInfo.move(textInfos.UNIT_LINE, -1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text.strip()  # Obtenir le texte de la ligne


                    # Vérifier si la ligne commence par "class " (déclaration de classe Python)
                    if self._isClass(lineText):
                        # Déplacer le curseur au début de la ligne
                        caretInfo.updateCaret()
                        # FLB 3 : deplacement du curseur vers le bas pour la classe precedent  
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' ')) 
                        # move caret close to classe   
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret()
                        
                        log.debug(f"Déclaration de classe précédente trouvée : {lineText}")
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break


                    # Si on atteint le début du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset >= currentLine:
                        log.debug("Aucune déclaration de classe précédente trouvée.")
                        speech.speakMessage("Aucune déclaration de classe précédente trouvée.")
                        break


                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset


            except Exception as e:
                log.error(f"Erreur lors de la recherche de la déclaration de classe précédente : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToPreviousClass.__doc__ = _("Déplace le curseur vers la première ligne de la déclaration de classe Python précédente.")
    script_moveToPreviousClass.category = "Notepad++"

####################################################################################################
    def script_jumpToMain(self, gesture):
        """
        Déplace le curseur vers la ligne contenant le bloc principal Python.

        Cette méthode recherche la ligne 'if __name__ == "__main__":' dans tout
        le fichier, en partant du début, indépendamment de la position actuelle
        du curseur.

        Parameters
        ----------
        gesture : inputCore.InputGesture
            L'événement de raccourci clavier (F8) déclenchant cette action.

        Returns
        -------
        None

        Notes
        -----
        - Recherche TOUJOURS depuis le début du fichier (correction du bug)
        - Supporte les guillemets simples ou doubles
        - Positionne le curseur au niveau de l'indentation de 'if'
        - Si la ligne n'est pas trouvée, annonce un message approprié

        Examples
        --------
        Quelque soit la position du curseur dans le fichier, appuyer sur F8 
        déplace vers:
        ```python
        if __name__ == '__main__':
            main()
        ```
        """
        log.debug("Raccourci F9 detecte - recherche bloc principal if __name__ == '__main__'")

        # F8 est specifique a Python — sans objet pour C/C++ ou autres langages
        if self._current_lang != "python" and self._current_lang != "unknown":
            speech.speakMessage("F8 est disponible uniquement pour les fichiers Python.")
            return

        if not self.edit:
            log.debug("Aucun objet d'édition trouvé")
            speech.speakMessage("Aucun éditeur détecté.")
            return

        try:
            # CORRECTION : Partir du début du fichier au lieu de la position actuelle
            caretInfo = self.edit.makeTextInfo(textInfos.POSITION_FIRST)
            caretInfo.expand(textInfos.UNIT_LINE)

            # Parcourir toutes les lignes du fichier
            foundLine = False
            while True:
                lineText = caretInfo.text.strip()

                # Vérifier si la ligne contient le bloc principal
                # Supporte: if __name__ == '__main__': ou if __name__ == "__main__":
                if lineText.startswith("if __name__") and "__main__" in lineText:
                    # Ligne trouvée ! Positionner le curseur au niveau de 'if'
                    caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' '))
                    caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                    caretInfo.updateCaret()

                    log.debug("Ligne principale trouvée : %s", lineText)
                    speech.speakMessage("Bloc principal trouvé.")
                    foundLine = True
                    break

                # Essayer de passer à la ligne suivante
                # move() retourne 0 si on ne peut plus bouger (fin du fichier)
                if caretInfo.move(textInfos.UNIT_LINE, 1) == 0:
                    log.debug("Fin du fichier atteinte sans trouver le bloc principal")
                    break
                
                caretInfo.expand(textInfos.UNIT_LINE)

            if not foundLine:
                log.debug("Ligne if __name__ == '__main__': non trouvée dans le document")
                speech.speakMessage("Ligne if name égal main non trouvée.")

        except Exception as e:
            log.error("Erreur lors de la recherche du bloc principal : %s", e, exc_info=True)
            speech.speakMessage("Erreur lors de la recherche.")

    script_jumpToMain.__doc__ = _("Déplace le curseur vers la ligne principale if __name__ == '__main__'")
    script_jumpToMain.category = "Notepad++"

####################################################################################################
    def script_selectCurrentClass(self, gesture):
        """
        Sélectionne la classe entière à partir de la position du curseur en fonction de l'indentation.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (Shift+F8)")

        # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLineText = caretInfo.text.strip()  # Obtenir le texte de la ligne actuelle

                # Vérifier si la ligne actuelle contient une déclaration de classe
                if self._isClass(currentLineText):
                    # Si c'est le cas, on commence la sélection à partir de cette ligne
                    startInfo = caretInfo.copy()
                    startIndentation = self._getIndentationLevel(currentLineText)
                else:
                    # Sinon, on cherche la déclaration de classe précédente
                    while True:
                        caretInfo.move(textInfos.UNIT_LINE, -1)
                        caretInfo.expand(textInfos.UNIT_LINE)
                        lineText = caretInfo.text.strip()

                        if self._isClass(lineText):
                            startInfo = caretInfo.copy()
                            startIndentation = self._getIndentationLevel(lineText)
                            break

                        # Si on atteint le début du document, on arrête la recherche
                        if caretInfo.bookmark.startOffset <= 0:
                            log.debug("Aucune déclaration de classe trouvée.")
                            speech.speakMessage("Aucune déclaration de classe trouvée.")
                            return

                # Trouver la fin de la classe en parcourant les lignes suivantes
                endInfo = startInfo.copy()
                endInfo.expand(textInfos.UNIT_LINE)
                endInfo.collapse(end=True)

                lineCounter = 0  # Compteur de lignes

                while True:
                    endInfo.move(textInfos.UNIT_LINE, 1)
                    endInfo.expand(textInfos.UNIT_LINE)
                    lineText = endInfo.text
                    currentIndentation = self._getIndentationLevel(lineText)

                    # Si l'indentation est inférieure ou égale à celle de la déclaration
                    if currentIndentation <= startIndentation:
                        # Si la ligne contient du texte, on s'arrête
                        if lineText.strip():
                            # Revenir en arrière d'une ligne
                            endInfo.move(textInfos.UNIT_LINE, -1)
                            endInfo.expand(textInfos.UNIT_LINE)
                            break

                    lineCounter += 1

                # Appliquer la sélection
                selectionInfo = self.edit.makeTextInfo(startInfo)
                selectionInfo.setEndPoint(endInfo, "endToEnd")
                self.edit.selection = selectionInfo

                log.debug(f"Classe sélectionnée avec succès. Nombre de lignes sélectionnées : {lineCounter}")
                speech.speakMessage(f"Classe sélectionnée. {lineCounter} lignes sélectionnées.")

            except Exception as e:
                log.error(f"Erreur lors de la sélection de la classe : {e}")
                speech.speakMessage("Erreur lors de la sélection de la classe.")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectCurrentClass.__doc__ = _("Sélectionne la classe entière à partir de la position du curseur en fonction de l'indentation.")
    script_selectCurrentClass.category = "Notepad++"

####################################################################################################
    def script_selectClass(self, gesture):
        """
        Sélectionne la classe entière à partir de la première ligne.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci détecté (Ctrl+Shift+R)")


        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                lineText = caretInfo.text.strip()


                # Vérifier si la ligne commence par "class " (déclaration de classe Python)
                if lineText.startswith("class "):
                    self._selectClass(caretInfo)
                    log.debug("Classe sélectionnée avec succès.")
                    speech.speakMessage("Classe sélectionnée.")
                else:
                    log.debug("Le curseur n'est pas sur une déclaration de classe.")
                    speech.speakMessage("Le curseur n'est pas sur une déclaration de classe.")


            except Exception as e:
                log.error(f"Erreur lors de la sélection de la classe : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectClass.__doc__ = _("Sélectionne la classe entière")
    script_selectClass.category = "Notepad++"

####################################################################################################
    def script_selectCurrentFunction(self, gesture):
        """
        Sélectionne la fonction entière à partir de la position du curseur en fonction de l'indentation.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        # Envoyer un message dans le journal de NVDA
        log.debug("Raccourci DETECTE (Shift+F3)")

        # Vérifier si l'objet d'édition est disponible
        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLineText = caretInfo.text.strip()  # Obtenir le texte de la ligne actuelle

                # Vérifier si la ligne actuelle contient une déclaration de fonction
                # FLB 2025-06-07 
                # if currentLineText.startswith("def "):
                if self._isFunction(currentLineText):
                    # Si c'est le cas, on commence la sélection à partir de cette ligne
                    startInfo = caretInfo.copy()
                    startIndentation = self._getIndentationLevel(currentLineText)
                else:
                    # Sinon, on cherche la déclaration de fonction précédente
                    while True:
                        caretInfo.move(textInfos.UNIT_LINE, -1)
                        caretInfo.expand(textInfos.UNIT_LINE)
                        lineText = caretInfo.text.strip()

                        # FLB 2025-06-07
                        # if lineText.startswith("def "):
                        if self._isFunction(lineText):
                            startInfo = caretInfo.copy()
                            startIndentation = self._getIndentationLevel(lineText)
                            break

                        # Si on atteint le début du document, on arrête la recherche
                        if caretInfo.bookmark.startOffset <= 0:
                            log.debug("Aucune déclaration de fonction trouvée.")
                            speech.speakMessage("Aucune déclaration de fonction trouvée.")
                            return

                # Trouver la fin de la fonction en parcourant les lignes suivantes
                endInfo = startInfo.copy()
                endInfo.expand(textInfos.UNIT_LINE)
                endInfo.collapse(end=True)

                lineCounter = 0  # Compteur de lignes

                while True:
                    endInfo.move(textInfos.UNIT_LINE, 1)
                    endInfo.expand(textInfos.UNIT_LINE)
                    lineText = endInfo.text
                    currentIndentation = self._getIndentationLevel(lineText)

                    # Si l'indentation est inférieure ou égale à celle de la déclaration
                    if currentIndentation <= startIndentation:
                        # Si la ligne contient du texte, on s'arrête
                        if lineText.strip():
                            # Revenir en arrière d'une ligne
                            endInfo.move(textInfos.UNIT_LINE, -1)
                            endInfo.expand(textInfos.UNIT_LINE)
                            break

                    lineCounter += 1

                # Appliquer la sélection
                selectionInfo = self.edit.makeTextInfo(startInfo)
                selectionInfo.setEndPoint(endInfo, "endToEnd")
                self.edit.selection = selectionInfo

                log.debug(f"Fonction sélectionnée avec succès. Nombre de lignes sélectionnées : {lineCounter}")
                speech.speakMessage(f"Fonction sélectionnée. {lineCounter} lignes sélectionnées.")

            except Exception as e:
                log.error(f"Erreur lors de la sélection de la fonction : {e}")
                speech.speakMessage("Erreur lors de la sélection de la fonction.")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectCurrentFunction.__doc__ = _("Sélectionne la fonction entière à partir de la position du curseur en fonction de l'indentation.")
    script_selectCurrentFunction.category = "Notepad++"

####################################################################################################
    def script_selectFunction(self, gesture):
        """
        Sélectionne la fonction entière à partir de la première ligne.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci détecté (Ctrl+R)")


        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                lineText = caretInfo.text.strip()


                # Vérifier si la ligne commence par "def " (déclaration de fonction Python)
                # FLB 2025-06-07 
                # if lineText.startswith("def "):
                if re.match(r"^\s*(async\s+)?def\s+", lineText):
                    self._selectFunction(caretInfo)
                    log.debug("Fonction sélectionnée avec succès.")
                    speech.speakMessage("Fonction sélectionnée.")
                else:
                    log.debug("Le curseur n'est pas sur une déclaration de fonction.")
                    speech.speakMessage("Le curseur n'est pas sur une déclaration de fonction.")


            except Exception as e:
                log.error(f"Erreur lors de la sélection de la fonction : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectFunction.__doc__ = _("Sélectionne la fonction entière")
    script_selectFunction.category = "Notepad++"
    
####################################################################################################
    def _deleteClass(self, caretInfo):
        """
        Supprime la classe entière à partir de la position du curseur après confirmation.

        Parameters
        ----------
        caretInfo : object
            L'objet contenant les informations de texte et la position du curseur.
        """
        try:
            # Trouver le début de la classe (ligne contenant "class")
            startInfo = caretInfo.copy()
            startInfo.expand(textInfos.UNIT_LINE)
            startInfo.collapse()

            # Obtenir le texte de la ligne de déclaration de la classe
            startLineText = startInfo.text
            startIndentation = self._getIndentationLevel(startLineText)

            # Trouver la fin de la classe en parcourir les lignes suivantes
            endInfo = startInfo.copy()
            endInfo.expand(textInfos.UNIT_LINE)
            endInfo.collapse(end=True)

            lineCounter = 0  # Compteur de lignes

            while True:
                endInfo.move(textInfos.UNIT_LINE, 1)
                endInfo.expand(textInfos.UNIT_LINE)
                lineText = endInfo.text
                currentIndentation = self._getIndentationLevel(lineText)

                # Si l'indentation est inférieure ou égale à celle de la déclaration
                if currentIndentation <= startIndentation:
                    # Si la ligne contient du texte, on s'arrête
                    if lineText.strip():
                        # Revenir en arrière d'une ligne
                        endInfo.move(textInfos.UNIT_LINE, -1)
                        endInfo.expand(textInfos.UNIT_LINE)
                        break

                lineCounter += 1

            # Appliquer la sélection
            selectionInfo = self.edit.makeTextInfo(startInfo)
            selectionInfo.setEndPoint(endInfo, "endToEnd")
            self.edit.selection = selectionInfo
            speech.speakMessage(f"êtes vous sûr de vouloir supprimer la classe?")
            # Demander confirmation avant suppression avec un message personnalisé
            if gui.messageBox(
                "Voulez-vous vraiment supprimer cette classe ?",  # Message personnalisé
                "Confirmation de suppression",  # Titre de la boîte de dialogue
                wx.YES_NO | wx.ICON_QUESTION  # Boutons Oui/Non et icône de question
            ) == wx.YES:
                # Simuler l'appui sur la touche Suppr pour supprimer la sélection
                keyboardHandler.KeyboardInputGesture.fromName("delete").send()
                log.debug(f"Classe supprimée avec succès. Nombre de lignes supprimées : {lineCounter}")
                speech.speakMessage(f"Classe supprimée. {lineCounter} lignes supprimées.")
            else:
                log.debug("Suppression annulée par l'utilisateur.")
                speech.speakMessage("Suppression annulée.")

        except Exception as e:
            log.error(f"Erreur lors de la suppression de la classe : {e}")
            speech.speakMessage("Erreur lors de la suppression de la classe.")

####################################################################################################
    def script_moveToNextIndentLevel(self, gesture):
        """
        Déplace le curseur vers la prochaine ligne avec PLUS d'indentation.

        Cette méthode cherche la prochaine ligne ayant un niveau d'indentation
        supérieur à la ligne courante, permettant de "descendre" dans la
        structure du code (ex: entrer dans une fonction, une boucle, etc.).

        Parameters
        ----------
        gesture : inputCore.InputGesture
            L'événement de raccourci clavier (Alt+Down) déclenchant cette action.

        Returns
        -------
        None

        Notes
        -----
        - Cherche uniquement vers le BAS du fichier
        - Ne s'arrête qu'à un niveau d'indentation STRICTEMENT SUPÉRIEUR
        - Utile pour entrer dans une structure imbriquée
        - Annonce le niveau d'indentation trouvé
        - Si aucun niveau supérieur n'est trouvé, annonce fin du document
        """
        log.debug("Raccourci Alt+Down détecté - recherche niveau plus indenté")

        if not self.edit:
            log.debug("Aucun objet d'édition trouvé")
            speech.speakMessage("Aucun éditeur détecté.")
            return

        try:
            # Obtenir la position actuelle du curseur
            caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
            caretInfo.expand(textInfos.UNIT_LINE)
            currentLineText = caretInfo.text

            # Calculer l'indentation actuelle (tabs = 4 espaces)
            currentIndent = 0
            for char in currentLineText:
                if char == '\t':
                    currentIndent += 4
                elif char == ' ':
                    currentIndent += 1
                else:
                    break

            currentLine = caretInfo.bookmark.startOffset

            # Parcourir les lignes suivantes pour trouver un niveau SUPÉRIEUR
            while True:
                # Passer à la ligne suivante
                moveResult = caretInfo.move(textInfos.UNIT_LINE, 1)
                if moveResult == 0:
                    # Fin du fichier
                    log.debug("Fin du document - aucun niveau supérieur trouvé")
                    speech.speakMessage("Fin du document atteinte.")
                    break

                caretInfo.expand(textInfos.UNIT_LINE)
                lineText = caretInfo.text

                # Calculer l'indentation de cette ligne
                lineIndent = 0
                for char in lineText:
                    if char == '\t':
                        lineIndent += 4
                    elif char == ' ':
                        lineIndent += 1
                    else:
                        break

                # CORRECTION : Chercher uniquement un niveau SUPÉRIEUR
                if lineIndent > currentIndent:
                    # Niveau supérieur trouvé !
                    caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' \t'))
                    caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                    caretInfo.updateCaret()

                    log.debug("Niveau superieur trouve : %s (indent: %d)", lineText.strip(), lineIndent)
                    line_num = self._getCurrentLineNumber() + 1
                    speech.speakMessage(f"{lineText.strip()} ligne {line_num}, indentation {lineIndent}")
                    break

                # Vérifier boucle infinie
                if caretInfo.bookmark.startOffset <= currentLine:
                    log.debug("Erreur : boucle infinie détectée")
                    speech.speakMessage("Aucun niveau supérieur trouvé.")
                    break

                currentLine = caretInfo.bookmark.startOffset

        except Exception as e:
            log.error("Erreur lors de la recherche du niveau supérieur : %s", e, exc_info=True)
            speech.speakMessage("Erreur lors de la recherche.")

    script_moveToNextIndentLevel.__doc__ = _("Déplace le curseur vers la prochaine ligne avec plus d'indentation (descendre dans la structure).")
    script_moveToNextIndentLevel.category = "Notepad++"

####################################################################################################

    def script_moveToPreviousIndentLevel(self, gesture):
        """
        Déplace le curseur vers la ligne précédente avec MOINS d'indentation.

        Cette méthode cherche la ligne précédente ayant un niveau d'indentation
        inférieur à la ligne courante, permettant de "remonter" dans la
        structure du code (ex: sortir d'une fonction, revenir au niveau parent).

        Parameters
        ----------
        gesture : inputCore.InputGesture
            L'événement de raccourci clavier (Alt+Up) déclenchant cette action.

        Returns
        -------
        None

        Notes
        -----
        - Cherche uniquement vers le HAUT du fichier
        - Ne s'arrête qu'à un niveau d'indentation STRICTEMENT INFÉRIEUR
        - Utile pour remonter vers la structure englobante
        - Annonce le niveau d'indentation trouvé
        - Si aucun niveau inférieur n'est trouvé, annonce un message
        """
        log.debug("Raccourci Alt+Up détecté - recherche niveau moins indenté")

        if not self.edit:
            log.debug("Aucun objet d'édition trouvé")
            speech.speakMessage("Aucun éditeur détecté.")
            return

        try:
            # Obtenir la position actuelle du curseur
            caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
            caretInfo.expand(textInfos.UNIT_LINE)
            currentLineText = caretInfo.text

            # Calculer l'indentation actuelle (tabs = 4 espaces)
            currentIndent = 0
            for char in currentLineText:
                if char == '\t':
                    currentIndent += 4
                elif char == ' ':
                    currentIndent += 1
                else:
                    break

            currentLine = caretInfo.bookmark.startOffset

            # Parcourir les lignes précédentes pour trouver un niveau INFÉRIEUR
            while True:
                # Passer à la ligne précédente
                moveResult = caretInfo.move(textInfos.UNIT_LINE, -1)
                if moveResult == 0:
                    # Début du fichier
                    log.debug("Début du document - aucun niveau inférieur trouvé")
                    speech.speakMessage("Aucun niveau inférieur trouvé.")
                    break

                caretInfo.expand(textInfos.UNIT_LINE)
                lineText = caretInfo.text

                # Calculer l'indentation de cette ligne
                lineIndent = 0
                for char in lineText:
                    if char == '\t':
                        lineIndent += 4
                    elif char == ' ':
                        lineIndent += 1
                    else:
                        break

                # CORRECTION : Chercher uniquement un niveau INFÉRIEUR
                if lineIndent < currentIndent:
                    # Niveau inférieur trouvé !
                    caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' \t'))
                    caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                    caretInfo.updateCaret()

                    log.debug("Niveau inférieur trouvé : %s (indent: %d)", lineText.strip(), lineIndent)
                    line_num = self._getCurrentLineNumber() + 1
                    speech.speakMessage(f"{lineText.strip()} ligne {line_num}, indentation {lineIndent}")
                    break

                # Vérifier boucle infinie
                if caretInfo.bookmark.startOffset >= currentLine:
                    log.debug("Erreur : boucle infinie détectée")
                    speech.speakMessage("Aucun niveau inférieur trouvé.")
                    break

                currentLine = caretInfo.bookmark.startOffset

        except Exception as e:
            log.error("Erreur lors de la recherche du niveau inférieur : %s", e, exc_info=True)
            speech.speakMessage("Erreur lors de la recherche.")

    script_moveToPreviousIndentLevel.__doc__ = _("Déplace le curseur vers la ligne précédente avec moins d'indentation (remonter dans la structure).")
    script_moveToPreviousIndentLevel.category = "Notepad++"

####################################################################################################        

    def script_moveToNextIndentedLine(self, gesture):
        """
        Déplace le curseur vers la ligne suivante ayant le même niveau d'indentation et annonce le niveau actuel.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Control+Alt+Down détecté, exécution de moveToNextIndentedLine.")

        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLineText = caretInfo.text

                # Calculer l'indentation actuelle en tenant compte des tabulations
                currentIndent = 0
                for char in currentLineText:
                    if char == '\t':
                        currentIndent += 4  # Une tabulation = 4 espaces (ajuste selon ton éditeur)
                    elif char == ' ':
                        currentIndent += 1
                    else:
                        break

                # FLB : moveToNextIndentedLine 
                caretInfo.move(textInfos.UNIT_CHARACTER, currentIndent)
                caretInfo.updateCaret()
                
                # Annoncer le niveau d'indentation actuel
                speech.speakMessage(f"Indentation actuel : {currentIndent}")

                # Initialiser la position de la ligne actuelle
                currentLine = caretInfo.bookmark.startOffset

                # Parcourir les lignes suivantes pour trouver une ligne avec le même niveau d'indentation
                while True:
                    # Déplacer le curseur à la ligne suivante
                    caretInfo.move(textInfos.UNIT_LINE, 1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text

                    # Calculer l'indentation de la ligne suivante
                    lineIndent = 0
                    for char in lineText:
                        if char == '\t':
                            lineIndent += 4  # Une tabulation = 4 espaces (ajuste selon ton éditeur)
                        elif char == ' ':
                            lineIndent += 1
                        else:
                            break

                    # Vérifier si l'indentation est égale à l'actuelle
                    if lineIndent == currentIndent:
                        # Déplacer le curseur au début de la ligne
                        # FLB : moveToNextIndentedLine 
                        caretInfo.move(textInfos.UNIT_CHARACTER, currentIndent)
                        caretInfo.updateCaret()
                        log.debug(f"Ligne suivante avec le même niveau d'indentation trouvée : {lineText.strip()}")
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break

                    # Si on atteint la fin du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset <= currentLine:
                        log.debug("Aucune ligne suivante avec le même niveau d'indentation trouvée.")
                        speech.speakMessage("Fin du document.")
                        break

                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset

            except Exception as e:
                log.error(f"Erreur lors de la recherche de la ligne suivante avec le même niveau d'indentation : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToNextIndentedLine.__doc__ = _("Déplace le curseur vers la ligne suivante ayant le même niveau d'indentation et annonce le niveau actuel.")
    script_moveToNextIndentedLine.category = "Notepad++"

####################################################################################################

    def script_moveToPreviousIndentedLine(self, gesture):
        """
        Déplace le curseur vers la ligne précédente ayant le même niveau d'indentation et annonce le niveau actuel.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Control+Alt+Up détecté, exécution de moveToPreviousIndentedLine.")

        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)  # Étendre à la ligne entière
                currentLineText = caretInfo.text

                # Calculer l'indentation actuelle en tenant compte des tabulations
                currentIndent = 0
                for char in currentLineText:
                    if char == '\t':
                        currentIndent += 4  # Une tabulation = 4 espaces (ajuste selon ton éditeur)
                    elif char == ' ':
                        currentIndent += 1
                    else:
                        break

                # Annoncer le niveau d'indentation actuel
                speech.speakMessage(f"Indentation actuel : {currentIndent}")

                # Initialiser la position de la ligne actuelle
                currentLine = caretInfo.bookmark.startOffset

                # Parcourir les lignes précédentes pour trouver une ligne avec le même niveau d'indentation
                while True:
                    # Déplacer le curseur à la ligne précédente
                    caretInfo.move(textInfos.UNIT_LINE, -1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text

                    # Calculer l'indentation de la ligne précédente
                    lineIndent = 0
                    for char in lineText:
                        if char == '\t':
                            lineIndent += 4  # Une tabulation = 4 espaces (ajuste selon ton éditeur)
                        elif char == ' ':
                            lineIndent += 1
                        else:
                            break

                    # Vérifier si l'indentation est égale à l'actuelle
                    if lineIndent == currentIndent:
                        # Déplacer le curseur au début de la ligne
                        # FLB : moveToNextIndentedLine 
                        caretInfo.move(textInfos.UNIT_CHARACTER, currentIndent)
                        caretInfo.updateCaret()
                        log.debug(f"Ligne précédente avec le même niveau d'indentation trouvée : {lineText.strip()}")
                        line_num = self._getCurrentLineNumber() + 1
                        speech.speakMessage(f"{lineText.strip()} ligne {line_num}")
                        break

                    # Si on atteint le début du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset >= currentLine:
                        log.debug("Aucune ligne précédente avec le même niveau d'indentation trouvée.")
                        speech.speakMessage("Début du document.")
                        break

                    # Mettre à jour la position actuelle pour éviter les boucles infinies
                    currentLine = caretInfo.bookmark.startOffset

            except Exception as e:
                log.error(f"Erreur lors de la recherche de la ligne précédente avec le même niveau d'indentation : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    # Définir la docstring et la catégorie pour la fonction
    script_moveToPreviousIndentedLine.__doc__ = _("Déplace le curseur vers la ligne précédente ayant le même niveau d'indentation et annonce le niveau actuel.")
    script_moveToPreviousIndentedLine.category = "Notepad++"

####################################################################################################

    def script_selectToPreviousIndentLevel(self, gesture):
        """
        Sélectionne le texte jusqu'au niveau d'indentation précédent, puis place le curseur au début de la sélection.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Shift+Alt+Up détecté, exécution de selectToPreviousIndentLevel.")

        if self.edit:
            try:
                # Obtenir la position actuelle du curseur
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)
                currentLineText = caretInfo.text
                currentIndent = len(currentLineText) - len(currentLineText.lstrip())  # Calculer l'indentation actuelle
                startPosition = caretInfo.bookmark.startOffset  # Position de départ de la ligne actuelle

                # Créer un objet TextInfo pour la sélection
                selectionInfo = self.edit.makeTextInfo(textInfos.POSITION_SELECTION)
                selectionInfo.setEndPoint(caretInfo, "endToEnd")  # Définir le point de départ de la sélection

                # Parcourir les lignes précédentes pour trouver un niveau d'indentation différent
                while True:
                    # Déplacer le curseur à la ligne précédente
                    caretInfo.move(textInfos.UNIT_LINE, -1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text
                    lineIndent = len(lineText) - len(lineText.lstrip())  # Calculer l'indentation de la ligne

                    # Vérifier si l'indentation est différente de l'actuelle
                    if lineIndent != currentIndent:
                        # Sélectionner depuis la ligne actuelle jusqu'à cette ligne
                        selectionInfo.setEndPoint(caretInfo, "startToStart")  # Définir le point de fin de la sélection
                        selectionInfo.updateSelection()
                        log.debug(f"Sélection jusqu'au niveau d'indentation précédent : {lineText.strip()}")
                        speech.speakMessage(f"Sélection jusqu'au niveau d'indentation précédent : {lineText.strip()}")

                        # Déplacer le curseur au début de la sélection
                        startSelection = selectionInfo.copy()
                        startSelection.collapse(start=True)  # Déplacer le curseur au début de la sélection
                        startSelection.updateCaret()

                        log.debug("Curseur déplacé au début de la sélection.")
                        speech.speakMessage("Curseur déplacé au début de la sélection.")
                        break

                    # Si on atteint le début du document, arrêter la recherche
                    if caretInfo.bookmark.startOffset >= startPosition:
                        log.debug("Aucun niveau d'indentation précédent trouvé.")
                        speech.speakMessage("Aucun niveau d'indentation précédent trouvé.")
                        break

            except Exception as e:
                log.error(f"Erreur lors de la sélection jusqu'au niveau d'indentation précédent : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectToPreviousIndentLevel.__doc__ = _("Sélectionne le texte jusqu'au niveau d'indentation précédent, puis place le curseur au début de la sélection.")
    script_selectToPreviousIndentLevel.category = "Notepad++"

####################################################################################################
    def script_selectToNextIndentLevel(self, gesture):
        """
        Sélectionne le texte jusqu'au prochain niveau d'indentation.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Shift+Alt+Down détecté, exécution de selectToNextIndentLevel.")

        if self.edit:
            try:
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)
                currentLineText = caretInfo.text
                currentIndent = len(currentLineText) - len(currentLineText.lstrip())
                startPosition = caretInfo.bookmark.startOffset

                while True:
                    caretInfo.move(textInfos.UNIT_LINE, 1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text
                    lineIndent = len(lineText) - len(lineText.lstrip())

                    if lineIndent != currentIndent:
                        # Sélectionner jusqu'à cette ligne
                        selectionInfo = self.edit.makeTextInfo(textInfos.POSITION_SELECTION)
                        selectionInfo.setEndPoint(caretInfo, "endToEnd")
                        selectionInfo.updateSelection()
                        log.debug(f"Sélection jusqu'au niveau d'indentation suivant : {lineText.strip()}")
                        speech.speakMessage(f"Sélection jusqu'au niveau d'indentation suivant : {lineText.strip()}")
                        break

                    if caretInfo.bookmark.startOffset <= startPosition:
                        log.debug("Aucun niveau d'indentation suivant trouvé.")
                        speech.speakMessage("Aucun niveau d'indentation suivant trouvé.")
                        break

            except Exception as e:
                log.error(f"Erreur lors de la sélection jusqu'au niveau d'indentation suivant : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_selectToNextIndentLevel.__doc__ = _("Sélectionne le texte jusqu'au prochain niveau d'indentation.")
    script_selectToNextIndentLevel.category = "Notepad++"

####################################################################################################
    def script_moveToFirstLineInIndentation(self, gesture):
        """
        Déplace le curseur vers la première ligne du niveau d'indentation actuel.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Alt+Home détecté, exécution de moveToFirstLineInIndentation.")

        if self.edit:
            try:
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)
                currentLineText = caretInfo.text
                currentIndent = len(currentLineText) - len(currentLineText.lstrip())
                currentLine = caretInfo.bookmark.startOffset

                while True:
                    caretInfo.move(textInfos.UNIT_LINE, -1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text
                    lineIndent = len(lineText) - len(lineText.lstrip())

                    if lineIndent != currentIndent:
                        # Revenir à la ligne précédente (la première du niveau actuel)
                        caretInfo.move(textInfos.UNIT_LINE, 1)
                        # FLB indent 3 
                        # FLB 2 : deplacement du curseur vers le haut 
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' ')) 
                        # move caret close to def  
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret()                        

                        log.debug(f"Première ligne du niveau d'indentation actuel trouvée : {caretInfo.text.strip()}")
                        line_num = self._getCurrentLineNumber() + 1
                        indent = len(caretInfo.text) - len(caretInfo.text.lstrip())
                        speech.speakMessage(f"{caretInfo.text.strip()} ligne {line_num}")
                        break

                    if caretInfo.bookmark.startOffset >= currentLine:
                        log.debug("Début du fichier atteint.")
                        speech.speakMessage("Début du fichier atteint.")
                        break

            except Exception as e:
                log.error(f"Erreur lors de la recherche de la première ligne du niveau d'indentation actuel : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")

    script_moveToFirstLineInIndentation.__doc__ = _("Déplace le curseur vers la première ligne du niveau d'indentation actuel.")
    script_moveToFirstLineInIndentation.category = "Notepad++"

####################################################################################################
    def script_moveToLastLineInIndentation(self, gesture):
        """
        Déplace le curseur vers la dernière ligne du niveau d'indentation actuel.

        Parameters
        ----------
        gesture : object
            L'événement de raccourci clavier déclenchant cette action.
        """
        log.debug("Raccourci Alt+End détecté, exécution de moveToLastLineInIndentation.")

        if self.edit:
            try:
                caretInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                caretInfo.expand(textInfos.UNIT_LINE)
                currentLineText = caretInfo.text
                currentIndent = len(currentLineText) - len(currentLineText.lstrip())
                currentLine = caretInfo.bookmark.startOffset

                while True:
                    caretInfo.move(textInfos.UNIT_LINE, 1)
                    caretInfo.expand(textInfos.UNIT_LINE)
                    lineText = caretInfo.text
                    lineIndent = len(lineText) - len(lineText.lstrip())

                    if lineIndent != currentIndent:
                        # Revenir à la ligne précédente (la dernière du niveau actuel)
                        caretInfo.move(textInfos.UNIT_LINE, -1)
                        # FLB indent 3
                        # FLB 2 : deplacement du curseur vers le haut 
                        caretOffset = len(caretInfo.text) - len(caretInfo.text.lstrip(' ')) 
                        # move caret close to def  
                        caretInfo.move(textInfos.UNIT_CHARACTER, caretOffset)
                        caretInfo.updateCaret() 
                        
                        log.debug(f"Dernière ligne du niveau d'indentation actuel trouvée : {caretInfo.text.strip()}")
                        line_num = self._getCurrentLineNumber() + 1
                        indent = len(caretInfo.text) - len(caretInfo.text.lstrip())
                        speech.speakMessage(f"{caretInfo.text.strip()} ligne {line_num}")
                        break

                    if caretInfo.bookmark.startOffset <= currentLine:
                        log.debug("Fin du fichier atteinte.")
                        speech.speakMessage("Fin du fichier atteinte.")
                        break

            except Exception as e:
                log.error(f"Erreur lors de la recherche de la dernière ligne du niveau d'indentation actuel : {e}")
        else:
            log.debug("Aucun objet d'édition trouvé.")
    
    script_moveToLastLineInIndentation.__doc__ = _("Déplace le curseur vers la dernière ligne du niveau d'indentation actuel.")
    script_moveToLastLineInIndentation.category = "Notepad++"

####################################################################################################
# script_announceCurrentLineNumber
    def script_announceCurrentLineNumber(self, gesture):
        """
        Annonce le numéro de la ligne courante dans l'éditeur.

        Cette méthode calcule le numéro de ligne en parcourant le fichier depuis
        le début jusqu'à la position du curseur, garantissant un comptage précis
        incluant toutes les lignes (vides, commentaires, etc.).

        Parameters
        ----------
        gesture : inputCore.InputGesture
            L'événement de raccourci clavier (F4) déclenchant cette action.

        Returns
        -------
        None

        Notes
        -----
        - Compte TOUTES les lignes (vides, commentaires, code)
        - La numérotation commence à 1 (première ligne = ligne 1)
        - Correspond au numéro affiché par Notepad++ (Ctrl+G)
        - Méthode robuste utilisant l'API NVDA native
        """
        log.debug("Raccourci F4 détecté - annonce numéro de ligne")

        if not self.edit:
            log.debug("Aucun objet d'édition trouvé")
            speech.speakMessage("Aucun éditeur détecté.")
            return

        try:
            # Obtenir la position courante du curseur
            currentInfo = self.edit.makeTextInfo(textInfos.POSITION_CARET)
            currentInfo.expand(textInfos.UNIT_LINE)
            currentOffset = currentInfo.bookmark.startOffset

            # CORRECTION : Compter les lignes manuellement via l'API NVDA
            # Partir du début du fichier
            lineInfo = self.edit.makeTextInfo(textInfos.POSITION_FIRST)
            lineInfo.expand(textInfos.UNIT_LINE)

            lineNumber = 1  # Commencer à 1 (première ligne)

            # Parcourir les lignes jusqu'à atteindre la position du curseur
            while lineInfo.bookmark.startOffset < currentOffset:
                # Essayer de passer à la ligne suivante
                moveResult = lineInfo.move(textInfos.UNIT_LINE, 1)
                
                if moveResult == 0:
                    # Impossible de bouger = fin du fichier atteinte
                    log.debug("Fin du fichier atteinte lors du comptage")
                    break
                
                lineInfo.expand(textInfos.UNIT_LINE)
                lineNumber += 1

            # Annoncer le résultat
            speech.speakMessage(f"Ligne {lineNumber}")
            log.debug("Ligne actuelle annoncée : %d (offset: %d)", lineNumber, currentOffset)

        except Exception as e:
            log.error("Erreur lors de l'annonce du numéro de ligne : %s", e, exc_info=True)
            speech.speakMessage("Erreur lors de l'annonce.")

    script_announceCurrentLineNumber.__doc__ = _("Annonce le numéro de la ligne courante.")
    script_announceCurrentLineNumber.category = "Notepad++"

####################################################################################################
# script_announceCurrentIndentationLevel
    def script_announceCurrentIndentationLevel(self, gesture):
        """
        Annonce le niveau d'indentation logique de la ligne courante, basé sur l'attribut de classe self.TAB_SIZE_IN_SPACE.

        - Si l'indentation est nulle : annonce "pas d'indentation".
        - Si le nombre d'espaces est multiple de self.TAB_SIZE_IN_SPACE : annonce "niveau d'indentation N de X".
        - Sinon : annonce "erreur d'indentation, X détectés en début de ligne".

        Parameters
        ----------
        gesture : inputCore.InputGesture
            Le geste clavier qui a déclenché le script.
        """
        log.debug("Raccourci Ctrl+F4 déclenché : annonce du niveau d'indentation")

        if self.edit:
            try:
                info = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                info.expand(textInfos.UNIT_LINE)
                lineText = info.text
                nb_espaces = self._getIndentationLevel(lineText)

                if nb_espaces == 0:
                    speech.speakMessage("Pas d'indentation")
                    log.debug("Indentation : 0 espace")
                elif self._current_lang != "cpp" and nb_espaces % self.TAB_SIZE_IN_SPACE != 0:
                    # En Python, l'indentation doit etre un multiple de TAB_SIZE_IN_SPACE
                    # En C/C++, l'indentation est libre — on annonce juste le nombre d'espaces
                    speech.speakMessage(f"Erreur d'indentation, {nb_espaces} espace{'s' if nb_espaces != 1 else ''} en debut de ligne")
                    log.debug(f"Indentation incorrecte : {nb_espaces} espaces")
                elif self._current_lang == "cpp":
                    # En C/C++ : annoncer le nombre brut d'espaces sans jugement
                    speech.speakMessage(f"{nb_espaces} espace{'s' if nb_espaces != 1 else ''} d'indentation")
                    log.debug(f"Indentation C/C++ : {nb_espaces} espaces")
                else:
                    niveau = nb_espaces // self.TAB_SIZE_IN_SPACE
                    speech.speakMessage(f"Niveau d'indentation {niveau} de {nb_espaces} espaces")
                    log.debug(f"Indentation niveau {niveau}, {nb_espaces} espaces")
            except Exception as e:
                log.error(f"Erreur dans announceCurrentIndentationLevel : {e}")
                speech.speakMessage("Erreur lors de l'annonce de l'indentation.")
        else:
            speech.speakMessage("Aucun éditeur détecté.")
            log.debug("Éditeur non détecté au moment de l'annonce d'indentation")


    def script_showNavigationDialog(self, gesture):
        """
        Affiche la fenetre de navigation dans le code (NVDA+F7).

        Liste toutes les fonctions et classes du fichier courant,
        avec filtre dynamique et pre-selection de l'element le plus
        proche de la position courante du curseur.
        Entierement navigable au clavier, compatible NVDA.

        Parameters
        ----------
        gesture : InputGesture
            Raccourci clavier NVDA+F7.
        """
        log.debug("NVDA+F7 : ouverture fenetre de navigation")

        if not self.edit:
            speech.speakMessage("Aucun editeur actif.")
            return

        if not _NAV_DIALOG_AVAILABLE:
            speech.speakMessage("Fenetre de navigation non disponible.")
            return

        # Collecter les elements du fichier
        elements = self._collectElements()
        if not elements:
            speech.speakMessage("Aucun element de code trouve dans ce fichier.")
            return

        # Nom court du fichier pour le titre
        file_title = self._getFileTitle()

        # Ligne courante pour la pre-selection
        current_line = self._getCurrentLineNumber()

        log.debug("Nav dialog : %d elements, ligne=%d", len(elements), current_line)

        # Afficher la boite de dialogue via gui.mainFrame (methode correcte NVDA)
        # gui.mainFrame est le thread wx principal de NVDA
        import wx
        import gui

        def _showDialog():
            # prePopup/postPopup encadrent l'affichage d'une fenetre modale
            # dans NVDA pour eviter les conflits avec le focus NVDA
            gui.mainFrame.prePopup()
            try:
                dlg = _NavigationDialog(
                    parent=gui.mainFrame,
                    title=file_title,
                    elements=elements,
                    current_line=current_line
                )
                result = dlg.ShowModal()
                if result == wx.ID_OK and dlg.selected_line is not None:
                    target = dlg.selected_line
                    dlg.Destroy()
                    self._gotoAndAnnounce(target)
                else:
                    dlg.Destroy()
            finally:
                gui.mainFrame.postPopup()

        wx.CallAfter(_showDialog)

    script_showNavigationDialog.__doc__ = _(
        "Affiche la fenetre de navigation dans le code (fonctions et classes)."
    )
    script_showNavigationDialog.category = "Notepad++"

    def _gotoAndAnnounce(self, line):
        """
        Navigue vers une ligne et annonce le numero.

        Utilise wx.CallLater pour laisser la boite de dialogue se fermer
        completement avant de tenter de deplacer le focus vers Notepad++.

        Parameters
        ----------
        line : int
            Numero de ligne cible (base 0).
        """
        import wx

        def _doGoto():
            # Cette fonction est appelee via wx.CallLater apres fermeture
            # de la dialog. On utilise queueHandler pour repasser dans le
            # thread NVDA ou makeTextInfo et updateCaret fonctionnent.
            import queueHandler

            def _naviguer():
                try:
                    self._gotoLineNumber(line)
                    speech.speakMessage(f"Ligne {line + 1}")
                    log.debug("_gotoAndAnnounce : ligne %d", line)
                except Exception as e:
                    log.error("_naviguer : %s", e, exc_info=True)

            queueHandler.queueFunction(
                queueHandler.eventQueue, _naviguer
            )

        # Delai de 300ms pour laisser la dialog se fermer et Notepad++
        # reprendre le focus avant de tenter de deplacer le curseur
        wx.CallLater(300, _doGoto)

    def _collectElements(self):
        """
        Collecte tous les elements de code du fichier courant.

        Inclut les fonctions, classes ET les signets poses sur ce fichier.

        Returns
        -------
        list of dict
            Elements {'type', 'name', 'line'} tries par numero de ligne.
            type peut etre 'function', 'class' ou 'bookmark'.
        """
        if self._current_lang == "cpp":
            elements = self._collectCppElements()
        else:
            elements = self._collectPythonElements()

        # Ajouter les signets
        elements += self._collectBookmarkElements()

        # Trier par ligne
        elements.sort(key=lambda x: x['line'])
        return elements

    def _collectBookmarkElements(self):
        """
        Collecte les signets du fichier courant depuis le gestionnaire.

        Returns
        -------
        list of dict
            Signets sous forme d'elements {'type':'bookmark', 'name', 'line'}.
        """
        if not _BM_AVAILABLE:
            return []
        file_path = self._getCurrentFilePath()
        if not file_path:
            return []
        bm = _getBookmarkManager()
        result = []
        for line, text in bm.getAll(file_path):
            result.append({
                'type': 'bookmark',
                'name': f"[Signet] {text}" if text else f"[Signet] ligne {line + 1}",
                'line': line,
            })
        return result

    def _collectPythonElements(self):
        """
        Collecte les fonctions et classes Python via makeTextInfo.

        Returns
        -------
        list of dict
            Elements Python tries par ligne.
        """
        elements = []
        if not self.edit:
            return elements
        try:
            info = self.edit.makeTextInfo(textInfos.POSITION_FIRST)
            line_num = 0
            while True:
                info.expand(textInfos.UNIT_LINE)
                line_text = info.text.rstrip("\r\n")
                stripped = line_text.strip()

                if stripped and self._isFunction(line_text):
                    name = self._extractPythonName(line_text)
                    if name:
                        elements.append({
                            'type': 'function',
                            'name': name,
                            'line': line_num,
                        })
                elif stripped and self._isClass(line_text):
                    name = self._extractPythonName(line_text)
                    if name:
                        elements.append({
                            'type': 'class',
                            'name': name,
                            'line': line_num,
                        })

                if info.move(textInfos.UNIT_LINE, 1) == 0:
                    break
                line_num += 1
        except Exception as e:
            log.error("_collectPythonElements : %s", e, exc_info=True)
        return elements

    def _collectCppElements(self):
        """
        Collecte les fonctions et classes C/C++ via pygments.

        Returns
        -------
        list of dict
            Elements C/C++ tries par ligne.
        """
        if not _CPP_PARSER_AVAILABLE or not self.edit:
            return []
        try:
            info = self.edit.makeTextInfo(textInfos.POSITION_ALL)
            source = info.text
            return _CPP_PARSER.parseElements(source)
        except Exception as e:
            log.error("_collectCppElements : %s", e, exc_info=True)
            return []

    def _extractPythonName(self, line_text):
        """
        Extrait le nom d'une fonction ou classe Python.

        Parameters
        ----------
        line_text : str
            Texte de la ligne.

        Returns
        -------
        str or None
            Nom extrait ou None.
        """
        m = re.search(r'(?:async\s+)?def\s+(\w+)|class\s+(\w+)', line_text)
        if m:
            return m.group(1) or m.group(2)
        return None

    def _getFileTitle(self):
        """
        Retourne le nom court du fichier courant (sans chemin).

        Returns
        -------
        str
            Nom du fichier ou 'fichier inconnu'.
        """
        try:
            import ctypes
            import os
            buf = ctypes.create_unicode_buffer(512)
            hwnd = getattr(self.edit, "windowHandle", None)
            if hwnd:
                parent = hwnd
                while True:
                    p = ctypes.windll.user32.GetParent(parent)
                    if not p:
                        break
                    parent = p
                ctypes.windll.user32.GetWindowTextW(parent, buf, 512)
                title = buf.value
                m = re.match(r"^(.+?)\s*\*?\s*-\s*Notepad\+\+", title)
                if m:
                    return os.path.basename(m.group(1).strip())
        except Exception:
            pass
        return "fichier inconnu"

    # =========================================================================
    # Utilitaire : chemin du fichier courant
    # =========================================================================

    def _getCurrentFilePath(self):
        """
        Retourne le chemin complet du fichier courant depuis le titre Notepad++.

        Returns
        -------
        str
            Chemin complet du fichier, ou chaine vide si non disponible.
        """
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(512)
            hwnd = getattr(self.edit, "windowHandle", None) if self.edit else None
            if hwnd:
                parent = hwnd
                while True:
                    p = ctypes.windll.user32.GetParent(parent)
                    if not p:
                        break
                    parent = p
                ctypes.windll.user32.GetWindowTextW(parent, buf, 512)
                title = buf.value
                m = re.match(r"^(.+?)\s*\*?\s*-\s*Notepad\+\+", title)
                if m:
                    return m.group(1).strip()
        except Exception as e:
            log.error("_getCurrentFilePath : %s", e, exc_info=True)
        return ""

    # =========================================================================
    # SCRIPTS — Signets
    # =========================================================================

    def script_toggleBookmark(self, gesture):
        """
        Pose ou retire un signet sur la ligne courante (Ctrl+F2).

        Transmet d'abord le geste a Notepad++ pour le repere visuel
        dans la marge, puis enregistre dans la table interne de l'addon
        et vocalise l'action effectuee.

        Parameters
        ----------
        gesture : InputGesture
            Raccourci clavier Ctrl+F2.
        """
        log.debug("Ctrl+F2 : toggle signet")

        if not self.edit:
            gesture.send()
            return

        if not _BM_AVAILABLE:
            gesture.send()
            return

        # Lire la ligne courante avant d'envoyer le geste
        current_line = self._getCurrentLineNumber()
        file_path    = self._getCurrentFilePath()

        # Lire le texte de la ligne courante via makeTextInfo
        line_text = ""
        try:
            if self.edit:
                info = self.edit.makeTextInfo(textInfos.POSITION_CARET)
                info.expand(textInfos.UNIT_LINE)
                line_text = info.text.rstrip("\r\n").strip()
        except Exception:
            line_text = ""


        # Laisser Notepad++ poser/retirer le signet visuellement
        gesture.send()

        # Mettre a jour notre table interne et vocaliser
        if file_path:
            bm = _getBookmarkManager()
            action, total = bm.toggle(file_path, current_line, line_text)
            if action == 'added':
                order = bm.getOrderOf(file_path, current_line)
                if order:
                    speech.speakMessage(
                        f"Signet {order[0]} sur {order[1]} pose "
                        f"ligne {current_line + 1}"
                    )
                else:
                    speech.speakMessage(f"Signet pose ligne {current_line + 1}")
            else:
                speech.speakMessage(
                    f"Signet supprime ligne {current_line + 1} "
                    f"— {total} signet{'s' if total > 1 else ''} restant{'s' if total > 1 else ''}"
                )
        else:
            speech.speakMessage("Chemin du fichier non disponible.")

    script_toggleBookmark.__doc__ = _("Poser ou retirer un signet sur la ligne courante.")
    script_toggleBookmark.category = "Notepad++"

    def script_nextBookmark(self, gesture):
        """
        Navigue vers le signet suivant (F2).

        Navigation circulaire : revient au premier signet apres le dernier.
        Annonce : "Signet X sur Y : texte de la ligne, ligne N"

        Parameters
        ----------
        gesture : InputGesture
            Raccourci clavier F2.
        """
        log.debug("F2 : signet suivant")
        self._navigateBookmark("next")

    script_nextBookmark.__doc__ = _("Aller au signet suivant.")
    script_nextBookmark.category = "Notepad++"

    def script_previousBookmark(self, gesture):
        """
        Navigue vers le signet precedent (Shift+F2).

        Navigation circulaire : revient au dernier signet avant le premier.
        Annonce : "Signet X sur Y : texte de la ligne, ligne N"

        Parameters
        ----------
        gesture : InputGesture
            Raccourci clavier Shift+F2.
        """
        log.debug("Shift+F2 : signet precedent")
        self._navigateBookmark("prev")

    script_previousBookmark.__doc__ = _("Aller au signet precedent.")
    script_previousBookmark.category = "Notepad++"

    def _navigateBookmark(self, direction):
        """
        Navigation generique entre signets.

        Parameters
        ----------
        direction : str
            "next" ou "prev".
        """
        if not self.edit:
            speech.speakMessage("Aucun editeur actif.")
            return

        if not _BM_AVAILABLE:
            speech.speakMessage("Gestionnaire de signets non disponible.")
            return

        file_path = self._getCurrentFilePath()
        if not file_path:
            speech.speakMessage("Fichier non identifie.")
            return

        bm = _getBookmarkManager()

        if bm.getCount(file_path) == 0:
            speech.speakMessage("Aucun signet dans ce fichier.")
            return

        current_line = self._getCurrentLineNumber()

        if direction == "next":
            result = bm.getNext(file_path, current_line)
            circular_msg = "Retour au premier signet — "
            is_circular = (result is not None and
                           result[0] <= current_line and
                           bm.getCount(file_path) > 0)
        else:
            result = bm.getPrevious(file_path, current_line)
            circular_msg = "Retour au dernier signet — "
            is_circular = (result is not None and
                           result[0] >= current_line and
                           bm.getCount(file_path) > 0)

        if result is None:
            speech.speakMessage("Aucun signet dans ce fichier.")
            return

        target_line, text, order, total = result

        # Naviguer vers la ligne cible
        self._gotoLineNumber(target_line)

        # Construire l'annonce
        prefix = circular_msg if is_circular else ""
        annonce = (
            f"{prefix}Signet {order} sur {total} : "
            f"{text} ligne {target_line + 1}"
        )
        speech.speakMessage(annonce)
        log.debug("_navigateBookmark : %s ligne %d", direction, target_line)

####################################################################################################
#
# Gestures
#
####################################################################################################
    __gestures = {
        # --- Information ligne courante ---
        "kb:NVDA+F7"               : "showNavigationDialog",
        "kb:F4"                    : "announceCurrentLineNumber",
        "kb:control+F4"            : "announceCurrentIndentationLevel",

        # --- Navigation par structure de code ---
        "kb:F9"                    : "jumpToMain",           # Python : bloc __main__
        "kb:F2"                    : "nextBookmark",          # Signet suivant
        "kb:Shift+F2"              : "previousBookmark",      # Signet precedent
        "kb:control+F2"            : "toggleBookmark",        # Poser/enlever signet
        "kb:F7"                    : "moveToNextClass",      # Classe suivante
        "kb:Shift+F7"              : "moveToPreviousClass",  # Classe precedente
        "kb:F8"                    : "moveToNextFunction",   # Fonction suivante
        "kb:Shift+F8"              : "moveToPreviousFunction", # Fonction precedente

        # --- Navigation par indentation ---
        "kb:alt+downArrow"         : "moveToNextIndentLevel",
        "kb:alt+upArrow"           : "moveToPreviousIndentLevel",
        "kb:control+alt+downArrow" : "moveToNextIndentedLine",
        "kb:control+alt+upArrow"   : "moveToPreviousIndentedLine",
        "kb:alt+!"                 : "moveToFirstLineInIndentation",
        "kb:alt+:"                 : "moveToLastLineInIndentation",

        # --- Selection de blocs ---
        "kb:control+r"             : "selectCurrentFunction",
        "kb:control+shift+r"       : "selectCurrentClass",
        "kb:shift+alt+downArrow"   : "selectToNextIndentLevel",
        "kb:shift+alt+upArrow"     : "selectToPreviousIndentLevel",

        # --- Execution ---
        "kb:control+F5"            : "executePythonCode",
    }
