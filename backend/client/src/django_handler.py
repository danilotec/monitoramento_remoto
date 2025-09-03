import os
import sys
import django
from pathlib import Path

# # Caminho absoluto da raiz do projeto (onde fica a pasta backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))  # Adiciona raiz do projeto no path

# Configurações do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monitoramento.settings")
django.setup()

from dashboard.models import Hospital

def sync_hospital(nome):
    # Garante que o hospital existe (cria se não existir)
    Hospital.objects.get_or_create(nome=nome)
    Hospital.objects.get_or_create(nome='CRADMIN')