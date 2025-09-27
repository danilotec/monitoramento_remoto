import redis
import json
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import os
from dotenv import load_dotenv

load_dotenv()

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_password = os.getenv('REDIS_PASSWORD')
r = redis.Redis(host=redis_host, port=6379, db=0, password=redis_password, decode_responses=True)

def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            return render(request, 'login.html', {'error': 'Usuário ou senha inválidos'})

    return render(request, 'login.html')

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def admin_dashboard(request):
    hospital = request.user.hospital

    if not hasattr(request.user, "hospital") or hospital.nome != "CRADMIN":
        return redirect("dashboard") 

    hospitals = []

    central_data = r.hgetall("Central")
    if central_data:
        for hospital_nome, dados in central_data.items(): #type: ignore
            try:
                hospital_details = json.loads(dados)  
                hospital_details["hospital"] = hospital_nome
                hospitals.append(hospital_details)
            except Exception as e:
                print(f"Erro ao processar hospital {hospital_nome}: {e}")

    usina_data = r.hgetall("Usina")
    if usina_data:
        for hospital_nome, dados in usina_data.items(): #type: ignore
            try:
                oxygen_details = json.loads(dados)  # dict
                oxygen_details["hospital"] = hospital_nome
                hospitals.append(oxygen_details)
            except Exception as e:
                print(f"Erro ao processar hospital {hospital_nome}: {e}")

    context = {
        "hospitals": hospitals
    }
    return render(request, "admin_dashboard.html", context)

@login_required
def dashboard(request):
    hospital = request.user.hospital
    print(hospital)

    data = r.hget("Central", hospital.nome)
    if data:
        hospital_details = json.loads(data) #type: ignore
        context = {
            'hospital': hospital,
            'hospital_details': hospital_details
        }
        return render(request, 'dashboard_central.html', context)

    data = r.hget("Usina", hospital.nome)
    if data:
        oxygen_details = json.loads(data) #type: ignore
        context = {
            'hospital': hospital,
            'oxygen_details': oxygen_details
        }
        return render(request, 'dashboard_oxygenerator.html', context)

    context = {
        'hospital': hospital,
        'error': 'Detalhes do hospital não encontrados no Redis'
    }
    return render(request, 'hospital_404.html', context)

