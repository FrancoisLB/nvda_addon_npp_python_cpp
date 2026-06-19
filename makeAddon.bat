@echo off
REM =============================================================================
REM makeAddon.bat
REM NotepadPlusPlus NVDA AppModule — Script de packaging Windows
REM
REM Usage    : double-cliquer sur ce fichier ou l'executer dans un terminal
REM Resultat : nvda_addon_npp_python_cpp-4.2.nvda-addon dans le repertoire courant
REM Prerequis: Python 3.x installe et accessible dans le PATH
REM
REM Le nom exact du fichier produit est determine dynamiquement par
REM buildVars.py (addon_name + addon_version). Pas de SCons requis.
REM =============================================================================

echo.
echo Lancement du script de build...
echo.

REM Appeler le script Python de build
python build_addon.py

REM Afficher le code de retour
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build termine avec succes.
) else (
    echo.
    echo Build termine avec des erreurs. Verifier les messages ci-dessus.
)

echo.
pause
