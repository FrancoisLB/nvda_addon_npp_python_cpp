# =============================================================================
# lib/bookmarks.py
# NotepadPlusPlus NVDA AppModule v4.2
#
# Gestion autonome des signets de code pour l'addon NVDA Notepad++.
#
# ARCHITECTURE :
# Les signets sont geres independamment des signets natifs Notepad++.
# Quand l'utilisateur pose un signet via Ctrl+F2, le geste est transmis
# a Notepad++ (qui pose le repere visuel dans la marge) ET enregistre
# dans notre table interne (qui permet la vocalisation et la navigation).
#
# LIMITATION DOCUMENTEE :
# Les signets poses via le menu Notepad++ ou d'autres moyens que Ctrl+F2
# ne sont pas vocalises par cet addon car ils ne sont pas dans notre table.
# Les signets sont perdus a la fermeture de NVDA (session uniquement).
# Les numeros de ligne peuvent etre inexacts apres insertion/suppression
# de lignes dans le fichier.
#
# STRUCTURE DE DONNEES :
# {
#   "C:\\chemin\\fichier.py" : {
#       14: "def __init__(self):",     # ligne (base 0) : texte au marquage
#       45: "class MonCapteur:",
#   }
# }
#
# Auteurs : ECAM Rennes / My Human Kit
# Contact : contact@myhumankit.org
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.2"
__date__ = "2026-06-06"

import logging

log = logging.getLogger(__name__)


class BookmarkManager:
    """
    Gestionnaire de signets de code pour l'addon NVDA Notepad++.

    Maintient une table des signets en memoire pour la session courante.
    Les signets sont associes a un fichier par son chemin complet.

    Attributes
    ----------
    _bookmarks : dict
        Table des signets : {chemin_fichier : {ligne_base0 : texte_ligne}}

    Examples
    --------
    >>> bm = BookmarkManager()
    >>> bm.toggle("C:\\\\mon_fichier.py", 14, "def __init__(self):")
    ('added', 1)
    >>> bm.getNext("C:\\\\mon_fichier.py", 10)
    (14, "def __init__(self):")
    """

    def __init__(self):
        """Initialise le gestionnaire avec une table vide."""
        # { chemin_fichier : { ligne_base0 : texte_ligne } }
        self._bookmarks = {}
        log.debug("BookmarkManager initialise")

    # =========================================================================
    # Gestion des signets
    # =========================================================================

    def toggle(self, file_path, line, line_text=""):
        """
        Pose ou retire un signet sur une ligne donnee.

        Si la ligne n'est pas marquee, elle est ajoutee.
        Si la ligne est deja marquee, elle est retiree.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier courant.
        line : int
            Numero de ligne (base 0).
        line_text : str, optional
            Texte de la ligne au moment du marquage.

        Returns
        -------
        tuple (str, int)
            ('added', total) si le signet a ete ajoute,
            ('removed', total) si le signet a ete retire.
            total = nombre de signets restants dans le fichier.
        """
        if file_path not in self._bookmarks:
            self._bookmarks[file_path] = {}

        file_bm = self._bookmarks[file_path]

        if line in file_bm:
            del file_bm[line]
            action = 'removed'
            log.debug("Signet retire : %s ligne %d", file_path, line)
        else:
            file_bm[line] = line_text.strip()
            action = 'added'
            log.debug("Signet pose : %s ligne %d texte=%r",
                      file_path, line, line_text.strip())

        return (action, len(file_bm))

    def hasBookmark(self, file_path, line):
        """
        Verifie si une ligne est marquee d'un signet.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.
        line : int
            Numero de ligne (base 0).

        Returns
        -------
        bool
            True si la ligne est marquee.
        """
        return (file_path in self._bookmarks and
                line in self._bookmarks[file_path])

    def getAll(self, file_path):
        """
        Retourne tous les signets d'un fichier, tries par ligne.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.

        Returns
        -------
        list of tuple (int, str)
            Liste de (ligne_base0, texte_ligne) triee par numero de ligne.
            Liste vide si aucun signet.
        """
        if file_path not in self._bookmarks:
            return []
        bm = self._bookmarks[file_path]
        return sorted(bm.items(), key=lambda x: x[0])

    def getCount(self, file_path):
        """
        Retourne le nombre de signets dans un fichier.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.

        Returns
        -------
        int
            Nombre de signets.
        """
        if file_path not in self._bookmarks:
            return 0
        return len(self._bookmarks[file_path])

    def getNext(self, file_path, current_line):
        """
        Retourne le signet suivant apres la ligne courante.

        Navigation circulaire : si aucun signet apres la ligne courante,
        retourne le premier signet du fichier.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        tuple (int, str, int, int) or None
            (ligne, texte, index_1based, total) ou None si aucun signet.
            index_1based : position du signet dans la liste (base 1).
            total : nombre total de signets.
        """
        bookmarks = self.getAll(file_path)
        if not bookmarks:
            return None

        total = len(bookmarks)

        # Chercher le premier signet apres la ligne courante
        for idx, (line, text) in enumerate(bookmarks):
            if line > current_line:
                return (line, text, idx + 1, total)

        # Navigation circulaire : revenir au premier
        line, text = bookmarks[0]
        return (line, text, 1, total)

    def getPrevious(self, file_path, current_line):
        """
        Retourne le signet precedent avant la ligne courante.

        Navigation circulaire : si aucun signet avant la ligne courante,
        retourne le dernier signet du fichier.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.
        current_line : int
            Numero de ligne courante (base 0).

        Returns
        -------
        tuple (int, str, int, int) or None
            (ligne, texte, index_1based, total) ou None si aucun signet.
        """
        bookmarks = self.getAll(file_path)
        if not bookmarks:
            return None

        total = len(bookmarks)

        # Chercher le dernier signet avant la ligne courante
        for idx in range(len(bookmarks) - 1, -1, -1):
            line, text = bookmarks[idx]
            if line < current_line:
                return (line, text, idx + 1, total)

        # Navigation circulaire : aller au dernier
        line, text = bookmarks[-1]
        return (line, text, total, total)

    def clearAll(self, file_path):
        """
        Supprime tous les signets d'un fichier.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.

        Returns
        -------
        int
            Nombre de signets supprimes.
        """
        if file_path not in self._bookmarks:
            return 0
        count = len(self._bookmarks[file_path])
        del self._bookmarks[file_path]
        log.debug("Signets supprimes : %s (%d signets)", file_path, count)
        return count

    def getOrderOf(self, file_path, line):
        """
        Retourne le numero d'ordre (base 1) d'un signet dans la liste.

        Parameters
        ----------
        file_path : str
            Chemin complet du fichier.
        line : int
            Numero de ligne (base 0).

        Returns
        -------
        tuple (int, int) or None
            (index_1based, total) ou None si le signet n'existe pas.
        """
        bookmarks = self.getAll(file_path)
        for idx, (bm_line, _) in enumerate(bookmarks):
            if bm_line == line:
                return (idx + 1, len(bookmarks))
        return None


# Instance unique partagee par tout l'addon (singleton de session)
_manager = BookmarkManager()


def getManager():
    """
    Retourne l'instance unique du gestionnaire de signets.

    Returns
    -------
    BookmarkManager
        Instance singleton du gestionnaire.
    """
    return _manager
