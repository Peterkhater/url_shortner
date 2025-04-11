from django.http import JsonResponse
from django.shortcuts import redirect
from .models import User, Profile, Link
from datetime import datetime
import hashlib
import base64

BASE_URL = "http://127.0.0.1:8000/"
def home(request, code):
    link = Link.objects.filter(short_code=code).first()
    
    if link: 
        return redirect(link.original)
    else:
        return redirect('https://telegram.com')
    

def generate_code(username):
    no_of_link = Link.objects.count()
    salt = str(no_of_link) + username + str(datetime.now())  
    code = hashlib.sha256(salt.encode()).digest()
    encoded_code = base64.urlsafe_b64encode(code[:6]).decode().rstrip("=")
    return encoded_code

def short(request):
    link = request.GET.get("link")
    username = request.GET.get("user_name") 
    first_name = request.GET.get("first_name")
    chat_id = request.GET.get("user_id")  

    # Validate required fields
    if not chat_id:
        return JsonResponse({"status": "failed", "message": "user_id is required"})
    
    try:
        chat_id_int = int(chat_id)
    except ValueError:
        return JsonResponse({"status": "failed", "message": "Invalid user_id format"})

    if not first_name:
        return JsonResponse({"status": "failed", "message": "first_name is required"})

    # Handle missing username
    if not username:
        username = f"user_{chat_id_int}"

    # Get or create user
    user = User.objects.filter(id=chat_id_int).first()
    if not user:
        user = User.objects.create(
            id=chat_id_int,
            username=username,
            first_name=first_name
        )
        Profile.objects.create(user=user, telegram_user_id=chat_id_int)

    # Check subscription status
    profile = Profile.objects.get(user=user)
    if profile.sub_status == "trial" and user.links.count() >= 3:
        return JsonResponse({
            "status": "failed",
            "message": "Trial limit exceeded"
        })

    # Create short link
    short_code = generate_code(username)
    Link.objects.create(
        user=user,
        original=link,
        short_code=short_code
    )

    return JsonResponse({
        "status": "success",
        "short_url": f"{BASE_URL}{short_code}",
        "short_code": short_code
    })
