@echo off
chcp 65001 >nul
title Cabinet Médical — Construction du .exe

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║        🏥 CABINET MÉDICAL — CRÉATION DU .EXE            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python non trouvé !
    echo     Téléchargez Python sur : https://python.org/downloads
    echo     Cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

echo  ✅ Python trouvé
echo.

:: Installer les dépendances
echo  📦 Installation des dépendances...
pip install flask flask-cors pyinstaller --quiet
if errorlevel 1 (
    echo  ❌ Erreur installation pip
    pause
    exit /b 1
)
echo  ✅ Dépendances installées
echo.

:: Construire le .exe
echo  🔨 Construction du .exe (2-3 minutes)...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Cabinet Medical" ^
    --add-data "src;src" ^
    --hidden-import flask ^
    --hidden-import flask_cors ^
    --hidden-import sqlite3 ^
    server.py

if errorlevel 1 (
    echo.
    echo  ❌ Erreur lors de la construction
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   ✅ SUCCÈS ! Votre .exe est dans le dossier  dist\     ║
echo  ║                                                          ║
echo  ║   📁 Fichier : dist\Cabinet Medical.exe                  ║
echo  ║   💾 Base de données : cabinet.db (créée au 1er lancement)║
echo  ║                                                          ║
echo  ║   ▶  Double-cliquez sur "Cabinet Medical.exe" pour       ║
echo  ║      lancer l'application.                               ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
