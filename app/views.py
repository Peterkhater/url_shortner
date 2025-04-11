from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Profile, Link
from datetime import datetime
import hashlib
import base64
import logging
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)
BASE_URL = "http://127.0.0.1:8000/"  
DEFAULT_REDIRECT = "https://web.telegram.org/k/#@MinMsakirBot"  

def home(request, code):
    try:
        link = Link.objects.get(short_code=code)
        print(f"Redirecting: {code} -> {link.original}")  # Debug log
        return HttpResponseRedirect(link.original)
    except Link.DoesNotExist:
        print(f"Short code not found: {code}")  # Debug log
        return HttpResponseRedirect("https://web.telegram.org/k/#@MinMsakirBot")
    except Exception as e:
        print(f"Error redirecting: {str(e)}")  # Debug other errors
        return HttpResponseRedirect("https://web.telegram.org/k/#@MinMsakirBot")
    
@csrf_exempt
def short(request):
    """
    Handles URL shortening requests from the Telegram bot.
    Returns JSON (never redirects).
    """
    if request.method != 'GET':
        return JsonResponse(
            {"status": "error", "message": "Only GET requests are allowed"},
            status=405
        )

    try:
        # Extract parameters
        link = request.GET.get("link")
        user_id = request.GET.get("user_id")
        username = request.GET.get("user_name", "")
        first_name = request.GET.get("first_name", "Anonymous")

        # Validate required fields
        if not link:
            logger.error("Missing 'link' parameter")
            return JsonResponse(
                {"status": "failed", "message": "URL is required"},
                status=400
            )

        if not user_id:
            logger.error("Missing 'user_id' parameter")
            return JsonResponse(
                {"status": "failed", "message": "user_id is required"},
                status=400
            )

        # Ensure user_id is an integer
        try:
            user_id_int = int(user_id)
        except ValueError:
            logger.error(f"Invalid user_id: {user_id}")
            return JsonResponse(
                {"status": "failed", "message": "user_id must be a number"},
                status=400
            )

        # Create or update user
        user, created = User.objects.get_or_create(
            id=user_id_int,
            defaults={
                'username': username or f"user_{user_id_int}",
                'first_name': first_name
            }
        )

        # Create or update profile
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'telegram_user_id': user_id_int,
                'sub_status': 'trial'
            }
        )

        # Check trial limit (3 links max)
        if profile.sub_status == "trial" and user.links.count() >= 3:
            logger.info(f"User {user_id_int} exceeded trial limit")
            return JsonResponse({
                "status": "failed",
                "message": "Trial limit reached. Subscribe to continue."
            })

        # Generate short code
        short_code = generate_code(username or str(user_id_int))

        # Create the link
        Link.objects.create(
            user=user,
            original=link,
            short_code=short_code
        )

        # Success response
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
    """Generates a unique short code."""
    salt = f"{identifier}{datetime.now().timestamp()}"
    return base64.urlsafe_b64encode(
        hashlib.sha256(salt.encode()).digest()[:6]
    ).decode().rstrip("=")