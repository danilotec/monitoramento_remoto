# Projeto Novo Sistema

Este projeto utiliza **Django**, **Redis** e um **client MQTT**.  
Abaixo estão as instruções para configurar e rodar o sistema localmente.

---

## Pré-requisitos

- Python 3.11+  
- Redis (rodando em container local)  
- Pip  

---

## 1. Preparar o ambiente

1. Ativar o ambiente virtual:

```bash
# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

Instalar as dependências do projeto:

```bash
pip install -r requirements.txt
```

2. Rodar o Redis

Certifique-se de que o Redis está rodando em um container local.
Exemplo usando Docker:

```bash
docker run -d -p 6379:6379 --name redis redis
```

3. Rodar o client MQTT

O client MQTT precisa estar rodando para enviar/receber dados:

```bash
python backend/client/run_client.py
```

4. Inicializar o Django

Criar as migrações:

```bash
python backend/manage.py makemigrations
python backend/manage.py migrate
```
Criar um superusuário para acessar o admin:

```bash
python backend/manage.py createsuperuser
```

Rodar o servidor de desenvolvimento:

```bash
python backend/manage.py runserver
```
O Django estará disponível em: http://127.0.0.1:8000
