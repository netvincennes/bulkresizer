"""Point d'entrée pour Pydroid 3.

Utilisation dans Pydroid 3 :
  1. Ouvrir ce dossier dans Pydroid 3
  2. Installer les dépendances : pip install -r requirements.txt
  3. Lancer : python run_pydroid.py
"""
import os, sys

# S'assurer que le projet est dans le path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compresseurauto import ImageOptimizerApp

ImageOptimizerApp().run()
