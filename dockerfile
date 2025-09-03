FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["sh", "-c", "python backend/manage.py migrate && python backend/manage.py && python manage.py collectstatic --noinput && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 monitoramento.wsgi:application"]
