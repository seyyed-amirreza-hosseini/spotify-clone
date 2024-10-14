import json
import time
import base64
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from requests import post, get
from decouple import config
from concurrent.futures import ThreadPoolExecutor, as_completed


# Cache token for an hour (Spotify token expiration time)
def get_token():
    token = cache.get('spotify_token')
    if token:
        return token

    client_id = config('CLIENT_ID')
    client_secret = config('CLIENT_SECRET')

    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data, timeout=10)

    json_result = json.loads(result.content)
    token = json_result["access_token"]

    # Store token in cache for 1 hour (3600 seconds)
    cache.set('spotify_token', token, timeout=3600) 
    
    return token


def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={artist_name}&type=artist&limit=1"

    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["artists"]["items"]
    if len(json_result) == 0:
        print(f"No artist with name '{artist_name}' exists...")
        return None

    return json_result[0]

# Fetch top tracks by artist ID
def get_songs_by_artist(token, artist_id):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US"
    headers = get_auth_header(token)
    result = get(url, headers=headers, timeout=10)
    json_result = json.loads(result.content)["tracks"]
    return json_result


def fetch_artist_data(artist_name, token):
    # Check if artist data is cached
    cache_key = f'artist_data_{artist_name}'
    cached_artist_data = cache.get(cache_key)
    if cached_artist_data:
        return cached_artist_data

    # If not cached, fetch artist data
    artist_result = search_for_artist(token, artist_name)
    if artist_result:
        artist_id = artist_result["id"]
        artist_image = artist_result["images"][0]["url"] if artist_result["images"] else None
        songs = get_songs_by_artist(token, artist_id)

        artist_data = {
            "name": artist_name,
            "image": artist_image,
            "songs": [
                {
                    "name": song["name"],
                    "album_image": song["album"]["images"][0]["url"] if song["album"]["images"] else None
                } for song in songs[:3]  # Limit to top 3 songs
            ]
        }

        # Cache artist data for 1 hour (3600 seconds)
        cache.set(cache_key, artist_data, timeout=3600)
        
        return artist_data

    return None


# Main view to fetch and display top artists and their songs
@login_required(login_url='login')
def index(request):
    start = time.time()

    token = get_token()
    artist_names = ['The Weeknd', 'Taylor Swift', 'Bad Bunny', 'Ed Sheeran', 'Ariana Grande', 'Billie Eilish', 'Drake', 'Justin Bieber', 'Eminem', 'BTS', 'Rihanna', 'Shakira', 'SZA', 'Kanye West', 'Travis Scott', 'Dua Lipa', 'Calvin Harris', 'Kendrick Lamar', 'Maroon 5', 'Adele', 'Lana Del Rey', 'Imagine Dragons', 'Karol G', 'Linkin Park', 'Katy Perry', 'Marshmello', 'Future', 'J Balvin', 'Sia', 'Miley Cyrus']

    artists_data = []
    
    # Use ThreadPoolExecutor to make requests in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_artist = {executor.submit(fetch_artist_data, artist_name, token): artist_name for artist_name in artist_names}
        
        for future in as_completed(future_to_artist):
            artist_data = future.result()
            if artist_data:
                artists_data.append(artist_data)

    context = {'artists_data': artists_data}
    
    end = time.time()

    total = end - start
    print(total)
    return render(request, 'index.html', context)


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect('/')
        else:
            messages.info(request, "Invalid username or password")
            return redirect('login')
    else:
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

@login_required(login_url='login')
def logout(request):
    auth_logout(request)
    return redirect('login')


def music(request, pk):
    return render(request, 'music.html')