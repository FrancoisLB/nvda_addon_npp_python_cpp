==============================================================================
  NotepadPlusPlus — Module complementaire NVDA pour Notepad++
  Version 4.2 — 2026-06-18
  Auteurs : Youenn Daviaud, Mael Fer, Baptiste Picquart (ECAM Rennes / MHK)
            FrancoisLB (My Human Kit)
  Contact : contact@myhumankit.org
  Licence : GPL v2 ou ulterieure
==============================================================================

Ce module ameliore l'accessibilite de l'editeur Notepad++ pour les
developpeurs aveugles ou malvoyants utilisant le lecteur d'ecran NVDA.
Il ajoute des raccourcis clavier pour naviguer dans le code source Python
et C/C++ sans avoir a parcourir le fichier ligne par ligne.

Compatibilite :
  - Notepad++ 32 bits et 64 bits (Windows 10 / Windows 11)
  - NVDA 2026.1 minimum, teste jusqu'a NVDA 2026.1
  - Langages supportes : Python (.py .pyw .pyi)
                         C/C++/Arduino (.c .cpp .cxx .h .hpp .ino)

------------------------------------------------------------------------------
  INSTALLATION
------------------------------------------------------------------------------

  1. Telecharger le fichier nvda_addon_npp_python_cpp-4.2.nvda-addon
  2. Double-cliquer dessus depuis l'Explorateur Windows
  3. NVDA affiche une boite de dialogue de confirmation — accepter
  4. Redemarrer NVDA (Ctrl+Alt+N ou depuis le menu NVDA)

  Pour desinstaller :
  Menu NVDA > Outils > Gestionnaire d'extensions
  Selectionner l'addon, cliquer sur "Supprimer", redemarrer NVDA.

------------------------------------------------------------------------------
  DETECTION AUTOMATIQUE DU LANGAGE
------------------------------------------------------------------------------

  A l'ouverture d'un fichier dans Notepad++, le module detecte
  automatiquement le langage et l'annonce vocalement :

    "Python"           pour les fichiers .py .pyw .pyi
    "C/C++"            pour les fichiers .c .cpp .cxx .h .hpp .ino
    "type non reconnu" pour les autres types de fichiers

  Les raccourcis de navigation s'adaptent automatiquement au langage.

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — INFORMATION
------------------------------------------------------------------------------

  F4              Annonce le numero de la ligne courante

  Ctrl+F4         Annonce le niveau d'indentation de la ligne courante.
                  Python : signale les erreurs si non multiple de 4.
                  C/C++  : annonce le nombre d'espaces sans jugement.

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — NAVIGATION PAR STRUCTURE DE CODE
------------------------------------------------------------------------------

  NVDA+F7         Ouvre la fenetre de navigation (voir section dediee)

  F7              Aller a la declaration de CLASSE suivante
  Maj+F7          Aller a la declaration de CLASSE precedente
                  Annonce : "nom_classe ligne X"
                  Disponible en Python et C/C++.

  F8              Aller a la declaration de FONCTION/METHODE suivante
  Maj+F8          Aller a la declaration de FONCTION/METHODE precedente
                  Annonce : "nom_fonction ligne X"
                  Disponible en Python et C/C++.

  F9              Aller au bloc if __name__ == '__main__'
                  Recherche depuis le debut du fichier.
                  Python uniquement.

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — SIGNETS (nouveaute v4.2)
------------------------------------------------------------------------------

  Ctrl+F2         Poser ou enlever un signet sur la ligne courante.
                  Annonce : "Signet pose ligne X" ou "Signet enleve ligne X".
                  Le repere visuel natif Notepad++ est pose simultanement.

  F2              Aller au signet SUIVANT (navigation circulaire)
                  Annonce : "Signet X sur Y : texte ligne N"

  Maj+F2          Aller au signet PRECEDENT (navigation circulaire)
                  Annonce : "Signet X sur Y : texte ligne N"

  Les signets poses via Ctrl+F2 sont egalement visibles dans la fenetre
  de navigation NVDA+F7 (bouton radio "Signets").

  Limitations :
  - Les signets poses via le menu Notepad++ ne sont pas vocalises par NVDA.
    Utiliser Ctrl+F2 avec NVDA actif pour une annonce vocale.
  - Les signets sont perdus a la fermeture de NVDA (session uniquement).
  - Les numeros de ligne peuvent etre inexacts apres insertion ou suppression
    de lignes dans le fichier.

------------------------------------------------------------------------------
  FENETRE DE NAVIGATION — NVDA+F7
------------------------------------------------------------------------------

  La fenetre de navigation liste toutes les fonctions, classes et signets
  du fichier courant. Elle s'inspire de la liste d'elements NVDA (NVDA+F7
  en mode web).

  A l'ouverture :
    - Le focus est place sur le champ de filtre.
    - La liste est pre-selectionnee sur l'element le plus proche
      de la position courante du curseur dans le fichier.

  Contenu de la fenetre :
    - Champ filtre : tapez pour restreindre la liste par nom.
      Exemple : taper "init" affiche uniquement les elements
      dont le nom contient "init" (__init__, initialize...).
    - Boutons radio : filtrer par type (Tout / Fonctions / Classes / Signets).
      NVDA annonce le nombre d'elements quand le focus entre dans la liste.
    - Liste des elements : nom suivi du numero de ligne.
      Navigation avec les fleches haut et bas.
    - Bouton "Aller a" : ferme la fenetre et positionne le curseur
      sur la ligne de l'element selectionne dans Notepad++.
    - Bouton "Fermer" : ferme sans naviguer.

  Navigation clavier dans la fenetre :
    Tab / Maj+Tab   Passer d'un widget a l'autre
    Fleches haut/bas Dans la liste : element precedent/suivant
    Entree          Naviguer vers l'element selectionne (= Aller a)
    Echap           Fermer sans naviguer

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — NAVIGATION PAR INDENTATION
------------------------------------------------------------------------------

  Ces raccourcis fonctionnent pour tous les langages.

  Alt+Bas         Aller vers la prochaine ligne plus indentee
                  Annonce : "texte ligne X, indentation Y"
  Alt+Haut        Aller vers la prochaine ligne moins indentee
                  Annonce : "texte ligne X, indentation Y"

  Ctrl+Alt+Bas    Prochaine ligne de meme indentation
                  Annonce : "texte ligne X"
  Ctrl+Alt+Haut   Ligne precedente de meme indentation
                  Annonce : "texte ligne X"

  Alt+Debut       Premiere ligne du niveau d'indentation courant
                  Annonce : "texte ligne X"
  Alt+Fin         Derniere ligne du niveau d'indentation courant
                  Annonce : "texte ligne X"

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — SELECTION DE BLOCS
------------------------------------------------------------------------------

  Ctrl+R          Selectionner la fonction/methode courante
  Ctrl+Maj+R      Selectionner la classe courante

  Maj+Alt+Bas     Etendre la selection jusqu'au prochain niveau
  Maj+Alt+Haut    Etendre la selection jusqu'au niveau precedent

  Note : apres selection avec Ctrl+R ou Ctrl+Maj+R, appuyer sur la
         touche Suppression du clavier pour supprimer le bloc.

------------------------------------------------------------------------------
  RACCOURCIS CLAVIER — EXECUTION DU CODE
------------------------------------------------------------------------------

  Ctrl+F5         Executer le code Python dans un terminal externe.
                  Python uniquement.

------------------------------------------------------------------------------
  RESUME DES RACCOURCIS
------------------------------------------------------------------------------

  Touche          Action
  -------         ------
  Ctrl+F2         Poser/enlever un signet sur la ligne courante
  F2              Signet suivant
  Maj+F2          Signet precedent
  F4              Numero de ligne courante
  F7 / Maj+F7     Classe suivante / precedente
  F8 / Maj+F8     Fonction suivante / precedente
  F9              Bloc if __name__ == '__main__' (Python)
  NVDA+F7         Fenetre de navigation
  Ctrl+F4         Niveau d'indentation
  Alt+Bas/Haut    Indentation plus/moins profonde
  Ctrl+Alt+Bas    Meme indentation, ligne suivante
  Ctrl+Alt+Haut   Meme indentation, ligne precedente
  Alt+Debut       Premiere ligne du niveau
  Alt+Fin         Derniere ligne du niveau
  Ctrl+R          Selectionner la fonction courante
  Ctrl+Maj+R      Selectionner la classe courante
  Maj+Alt+Bas     Etendre selection vers le bas
  Maj+Alt+Haut    Etendre selection vers le haut
  Ctrl+F5         Executer en Python

------------------------------------------------------------------------------
  HISTORIQUE DES VERSIONS
------------------------------------------------------------------------------

  v4.2 (2026-06-18)
    - Gestion des signets : Ctrl+F2 (poser/enlever), F2 (suivant),
      Maj+F2 (precedent). Annonce vocale complete.
    - Signets visibles dans la fenetre de navigation NVDA+F7
      (bouton radio "Signets" ajoute).
    - F9 : bloc if __name__ == '__main__' (deplace depuis F2).

  v4.1 (2026-06-05)
    - Fenetre de navigation NVDA+F7 : liste fonctions et classes,
      filtre par nom, filtre par type, pre-selection sur element courant,
      navigation au clavier, compatible NVDA.
    - Disponible pour Python et C/C++.

  v4.0 (2026-06-03)
    - Detection automatique du langage (Python / C/C++ / Arduino .ino)
    - Navigation F7/F8 adaptee au langage detecte.
    - C/C++ : navigation fonctions et classes.
    - Annonce du numero de ligne pour toutes les navigations.
    - Compatible Notepad++ 32 et 64 bits.

  v3.6 (2026-06-03)
    - Corrections de bugs sur F2, F4, Alt+Bas/Haut.
    - Manifest mis a jour pour NVDA 2026.1.

  v3.5 (2025-07-23)
    - Support async def, amelioration positionnement curseur.
    - Detection erreur d'indentation (Ctrl+F4).

==============================================================================
