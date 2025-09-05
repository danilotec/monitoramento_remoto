#!/bin/sh
set -e

echo "==> Aplicando migrações..."
python backend/manage.py migrate

echo "==> Coletando arquivos estáticos..."
python backend/manage.py collectstatic --noinput

echo "==> Iniciando cliente MQTT em background..."
python backend/client/run_client.py &

echo "==> Iniciando servidor Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 monitoramento.wsgi:application
