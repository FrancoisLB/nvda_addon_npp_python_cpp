# =============================================================================
# lib/nav_dialog.py
# NotepadPlusPlus NVDA AppModule v4.1
#
# Fenetre de navigation dans le code — inspiree de la liste d'elements NVDA
# (NVDA+F7 en mode navigation web).
#
# Affiche une boite de dialogue modale listant toutes les fonctions et classes
# du fichier courant, navigable entierement au clavier, avec filtre dynamique.
#
# Raccourci d'acces : NVDA+F7 quand Notepad++ a le focus.
#
# Structure de la fenetre :
#   - Champ filtre (focus a l'ouverture)
#   - Boutons radio : Tout / Fonctions / Classes
#   - Liste des elements (nom + numero de ligne)
#   - Boutons : Aller a / Fermer
#
# Auteurs : ECAM Rennes / My Human Kit
# Licence : GPL v2 ou ulterieure
# =============================================================================

__version__ = "4.1"
__date__ = "2026-06-05"

import wx
import logging

log = logging.getLogger(__name__)


class NavigationDialog(wx.Dialog):
    """
    Boite de dialogue de navigation dans le code source.

    Affiche la liste des fonctions et classes du fichier courant,
    filtrable par nom et par type. Entierement navigable au clavier.
    Compatible avec les lecteurs d'ecran (NVDA, JAWS).

    Parameters
    ----------
    parent : wx.Window
        Fenetre parente (generalement None pour une fenetre modale).
    title : str
        Titre de la fenetre (nom du fichier courant).
    elements : list of dict
        Liste des elements de code, chaque element etant un dict :
        {
            'type' : 'function' ou 'class',
            'name' : str,   nom de l'element
            'line' : int,   numero de ligne (base 0)
        }
    current_line : int
        Numero de ligne courante dans l'editeur (base 0).
        Utilise pour pre-selectionner l'element le plus proche.

    Attributes
    ----------
    selected_line : int or None
        Numero de ligne (base 0) de l'element selectionne par l'utilisateur.
        None si l'utilisateur a ferme sans naviguer.

    Examples
    --------
    >>> dlg = NavigationDialog(None, "monFichier.py", elements, current_line=45)
    >>> if dlg.ShowModal() == wx.ID_OK:
    ...     target_line = dlg.selected_line
    >>> dlg.Destroy()
    """

    # Labels des types pour l'affichage
    TYPE_LABELS = {
        "function" : "fonction",
        "class"    : "classe",
    }

    def __init__(self, parent, title, elements, current_line=0):
        """
        Initialise la fenetre de navigation.

        Parameters
        ----------
        parent : wx.Window
            Fenetre parente.
        title : str
            Titre de la fenetre.
        elements : list of dict
            Elements de code a afficher.
        current_line : int
            Ligne courante dans l'editeur (base 0).
        """
        super().__init__(
            parent,
            title=f"Navigation — {title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        # Donnees
        self._all_elements = elements          # liste complete
        self._filtered_elements = list(elements)  # liste filtree affichee
        self._current_line = current_line
        self.selected_line = None              # resultat apres fermeture

        # Construire l'interface
        self._buildUI()

        # Appliquer le filtre initial (vide) et pre-selectionner
        self._applyFilter()
        self._preselectClosest()

        # Taille et position
        self.SetSize((500, 400))
        self.Centre()

    # =========================================================================
    # Construction de l'interface
    # =========================================================================

    def _buildUI(self):
        """Construit tous les widgets de la fenetre."""

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Champ filtre ---
        filter_label = wx.StaticText(panel, label="Filtrer :")
        self._filter_ctrl = wx.TextCtrl(
            panel,
            style=wx.TE_PROCESS_ENTER,
            name="Filtre"
        )
        self._filter_ctrl.SetHint("Tapez pour filtrer par nom...")

        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filter_sizer.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        filter_sizer.Add(self._filter_ctrl, 1, wx.EXPAND)

        main_sizer.Add(filter_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # --- Boutons radio Type ---
        self._type_radio = wx.RadioBox(
            panel,
            label="Type",
            choices=["Tout", "Fonctions", "Classes", "Signets"],
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
            name="Type d'element"
        )
        self._type_radio.SetSelection(0)  # "Tout" par defaut
        main_sizer.Add(self._type_radio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Liste des elements ---
        list_label = wx.StaticText(panel, label="Elements :")
        main_sizer.Add(list_label, 0, wx.LEFT | wx.TOP, 8)

        self._list_box = wx.ListBox(
            panel,
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
            name="Liste des elements de code"
        )
        main_sizer.Add(self._list_box, 1, wx.EXPAND | wx.ALL, 8)

        # --- Boutons ---
        btn_sizer = wx.StdDialogButtonSizer()

        self._btn_goto = wx.Button(panel, wx.ID_OK, label="Aller à")
        self._btn_goto.SetDefault()
        btn_sizer.AddButton(self._btn_goto)

        self._btn_close = wx.Button(panel, wx.ID_CANCEL, label="Fermer")
        btn_sizer.AddButton(self._btn_close)

        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(main_sizer)

        # --- Connecter les evenements ---
        self._filter_ctrl.Bind(wx.EVT_TEXT, self._onFilterChanged)
        self._filter_ctrl.Bind(wx.EVT_TEXT_ENTER, self._onGoto)
        self._type_radio.Bind(wx.EVT_RADIOBOX, self._onTypeChanged)
        self._list_box.Bind(wx.EVT_LISTBOX_DCLICK, self._onGoto)
        self._list_box.Bind(wx.EVT_KEY_DOWN, self._onListKeyDown)
        self._list_box.Bind(wx.EVT_SET_FOCUS, self._onListFocus)
        self._btn_goto.Bind(wx.EVT_BUTTON, self._onGoto)
        self._btn_close.Bind(wx.EVT_BUTTON, self._onClose)
        self.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

    # =========================================================================
    # Logique de filtrage
    # =========================================================================

    def _applyFilter(self):
        """
        Applique le filtre texte et type sur la liste complete.

        Met a jour self._filtered_elements et rafraichit le ListBox.
        Annonce le nombre de resultats via le nom du widget (lu par NVDA).
        """
        filter_text = self._filter_ctrl.GetValue().strip().lower()
        type_sel    = self._type_radio.GetSelection()  # 0=Tout 1=Fonctions 2=Classes

        # Filtrer par type
        if type_sel == 1:
            elements = [e for e in self._all_elements if e['type'] == 'function']
        elif type_sel == 2:
            elements = [e for e in self._all_elements if e['type'] == 'class']
        elif type_sel == 3:
            elements = [e for e in self._all_elements if e['type'] == 'bookmark']
        else:
            elements = list(self._all_elements)

        # Filtrer par texte
        if filter_text:
            elements = [e for e in elements
                        if filter_text in e['name'].lower()]

        self._filtered_elements = elements

        # Mettre a jour le ListBox
        self._list_box.Clear()
        for elem in elements:
            # Format : "nom_element     ligne X"
            label = f"{elem['name']:<30s} ligne {elem['line'] + 1}"
            self._list_box.Append(label)

        # Mettre a jour le label de la liste pour NVDA
        nb = len(elements)
        label = f"Elements de code — {nb} resultat{'s' if nb > 1 else ''}"
        self._list_box.SetName(label)

        # L'annonce du nombre est faite lors du focus sur la liste
        # (voir _onListFocus) — pas ici pour eviter les doublons

        log.debug("Filtre applique : %d elements", nb)

    def _preselectClosest(self):
        """
        Pre-selectionne l'element le plus proche de la ligne courante.

        Cherche l'element dont le numero de ligne est le plus proche
        (en dessous ou egal) de self._current_line.
        Si aucun element n'est avant le curseur, selectionne le premier.
        """
        if not self._filtered_elements:
            return

        best_idx = 0
        best_line = -1

        for i, elem in enumerate(self._filtered_elements):
            if elem['line'] <= self._current_line:
                if elem['line'] > best_line:
                    best_line = elem['line']
                    best_idx = i

        self._list_box.SetSelection(best_idx)
        self._list_box.EnsureVisible(best_idx)
        log.debug("Pre-selection : index=%d ligne=%d",
                  best_idx, self._filtered_elements[best_idx]['line'])

    # =========================================================================
    # Gestionnaires d'evenements
    # =========================================================================

    def _onListFocus(self, event):
        """
        Annonce le nombre d'elements dans la liste quand elle recoit le focus.

        Declenche quand l'utilisateur appuie sur Tab pour aller dans la liste,
        ou clique dessus. NVDA annonce le nombre total d'elements visibles.
        """
        nb = len(self._filtered_elements)
        try:
            import speech
            speech.speakMessage(
                f"{nb} element{'s' if nb > 1 else ''}"
            )
        except Exception:
            pass
        event.Skip()

    def _onFilterChanged(self, event):
        """
        Declenche quand le texte du filtre change.

        Rafraichit la liste et maintient la pre-selection.
        """
        self._applyFilter()
        self._preselectClosest()
        event.Skip()

    def _onTypeChanged(self, event):
        """
        Declenche quand le bouton radio Type change.

        Rafraichit la liste et maintient la pre-selection.
        """
        self._applyFilter()
        self._preselectClosest()
        event.Skip()

    def _onGoto(self, event):
        """
        Declenche quand l'utilisateur valide (Entree, double-clic, bouton).

        Recupere l'element selectionne et ferme la fenetre avec ID_OK.
        """
        idx = self._list_box.GetSelection()
        if idx == wx.NOT_FOUND or idx >= len(self._filtered_elements):
            # Aucune selection — ne rien faire
            return

        self.selected_line = self._filtered_elements[idx]['line']
        elem_name = self._filtered_elements[idx]['name']
        log.debug("Navigation vers : %s ligne %d", elem_name, self.selected_line)
        self.EndModal(wx.ID_OK)

    def _onClose(self, event):
        """Ferme sans naviguer."""
        self.selected_line = None
        self.EndModal(wx.ID_CANCEL)

    def _onListKeyDown(self, event):
        """
        Gere les touches clavier dans la liste.

        Entree → naviguer vers l'element selectionne.
        Autres touches → comportement par defaut du ListBox.
        """
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN:
            self._onGoto(event)
        else:
            event.Skip()

    def _onCharHook(self, event):
        """
        Intercepte Echap pour fermer sans naviguer.

        wx.Dialog ferme avec ID_CANCEL sur Echap par defaut,
        mais on s'assure que selected_line est None.
        """
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._onClose(event)
        else:
            event.Skip()
