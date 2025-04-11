from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Profile, Link
from datetime import datetime
import hashlib
import base64
import logging

logger = logging.getLogger(__name__)
BASE_URL = "http://127.0.0.1:8000/"

def home(request):
    pass

@csrf_exempt  
def short(request):
    try:
        # Get parameters from request
        link = request.GET.get("link")
        username = request.GET.get("user_name", "")
        first_name = request.GET.get("first_name", "Anonymous")
        chat_id = request.GET.get("user_id")

        # Validate required fields
        if not chat_id:
            logger.error("Missing user_id in request")
            return JsonResponse({"status": "failed", "message": "user_id is required"}, status=400)

        if not link:
            logger.error("Missing link in request")
            return JsonResponse({"status": "failed", "message": "link is required"}, status=400)

        try:
            chat_id_int = int(chat_id)
        except ValueError:
            logger.error(f"Invalid user_id format: {chat_id}")
            return JsonResponse({"status": "failed", "message": "Invalid user_id format"}, status=400)

        # Generate username if not provided
        if not username:
            username = f"user_{chat_id_int}"

        # Get or create user
        user, created = User.objects.get_or_create(
            id=chat_id_int,
            defaults={
                'username': username,
                'first_name': first_name
            }
        )

        # Get or create profile
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'telegram_user_id': chat_id_int,
                'sub_status': 'trial'
            }
        )

        
        if profile.sub_status == "trial" and user.links.count() >= 3:
            logger.info(f"User {chat_id_int} exceeded trial limit")
            return JsonResponse({
                "status": "failed",
                "message": "You have used all your free trial. Please click on /subscribe to continue."
            })

        
        short_code = generate_code(username)
        Link.objects.create(
            user=user,
            original=link,
            short_code=short_code
        )

        logger.info(f"Successfully created short link for user {chat_id_int}")
        return JsonResponse({
            "status": "success",
            "short_url": f"{BASE_URL}{short_code}",
            "short_code": short_code
        })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": "error",
            "message": "Internal server error"
        }, status=500)

def generate_code(identifier):
    """Generate short code using user identifier"""
    no_of_link = Link.objects.count()
    salt = f"{no_of_link}{identifier}{datetime.now()}"
    code = hashlib.sha256(salt.encode()).digest()
    return base64.urlsafe_b64encode(code[:6]).decode().rstrip("=")