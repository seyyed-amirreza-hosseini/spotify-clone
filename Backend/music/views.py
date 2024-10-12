from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User


def index(request):
    return render(request, 'index.html')

def login(request):
    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('password2')

        if password == confirm_password:
            if User.objects.filter(email=email).exists():
                messages.info(request, "Email is already taken")
                return redirect('signup')
            elif User.objects.filter(username=username).exists():
                messages.info(request, "Username is already taken")
                return redirect('signup')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                user_login = authenticate(request, username=username, password=password)
            
                auth_login(request, user_login)
                return redirect('/')
        else:
            messages.info(request, "Passwords do not match")
            return redirect('signup')
        
    else:
        return render(request, 'signup.html')

def logout(request):
    return render(request, 'logout.html')