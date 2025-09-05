FROM python:3.11-slim

# definir diretório de trabalho
WORKDIR /app

# instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# instalar dependências python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copiar o restante do código
COPY . /app/

# copiar script de inicialização
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# expor a porta do gunicorn/django
EXPOSE 8000

# comando de inicialização
CMD ["sh", "/app/start.sh"]
