import redis
import json
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Usuário ou senha inválidos'})

    return render(request, 'login.html')

def custom_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    hospital = request.user.hospital
    # 🔍 Tenta buscar no Redis como AirCentral
    data = r.hget("Central", hospital.nome)
    if data:
        hospital_details = json.loads(data) #type: ignore
        context = {
            'hospital': hospital,
            'hospital_details': hospital_details
        }
        return render(request, 'dashboard_central.html', context)

    # 🔍 Se não achou, tenta como OxygenCentral
    data = r.hget("Usina", hospital.nome)
    if data:
        oxygen_details = json.loads(data) #type: ignore
        context = {
            'hospital': hospital,
            'oxygen_details': oxygen_details
        }
        return render(request, 'dashboard_oxygenerator.html', context)

    # ❌ Se não achar em nenhum lugar
    context = {
        'hospital': hospital,
        'error': 'Detalhes do hospital não encontrados no Redis'
    }
    return render(request, 'hospital_404.html', context)