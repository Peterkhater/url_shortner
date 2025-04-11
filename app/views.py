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
    Handles URL shortening requests with premium/trial user differentiation
    Returns JSON response with:
    - Success: {status, short_url, is_premium}
    - Error: {status, message}
    """
    if request.method != 'GET':
        return JsonResponse(
            {"status": "error", "message": "Only GET requests allowed"},
            status=405
        )

    try:
        # Extract and validate parameters
        link = request.GET.get("link", "").strip()
        user_id = request.GET.get("user_id", "").strip()
        username = request.GET.get("user_name", "").strip()
        first_name = request.GET.get("first_name", "User").strip()

        if not link:
            return JsonResponse(
                {"status": "failed", "message": "URL is required"},
                status=400
            )
        if not user_id:
            return JsonResponse(
                {"status": "failed", "message": "user_id is required"},
                status=400
            )

        # Convert user_id to integer
        try:
            user_id_int = int(user_id)
        except ValueError:
            return JsonResponse(
                {"status": "failed", "message": "Invalid user ID format"},
                status=400
            )

        # Get or create user profile
        user, _ = User.objects.get_or_create(
            id=user_id_int,
            defaults={
                'username': username or f"user_{user_id_int}",
                'first_name': first_name
            }
        )

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'telegram_user_id': str(user_id_int),
                'sub_status': 'trial'
            }
        )

        # Check subscription limits
        if profile.sub_status == 'trial' and user.links.count() >= 3:
            return JsonResponse({
                "status": "failed",
                "message": "Trial limit reached. Upgrade to premium for unlimited links."
            })

        # Generate and save short URL
        short_code = generate_code(f"{user_id_int}{datetime.now().timestamp()}")
        Link.objects.create(
            user=user,
            original=link,
            short_code=short_code
        )

        return JsonResponse({
            "status": "success",
            "short_url": f"{BASE_URL}{short_code}",
            "is_premium": profile.sub_status == 'premium'
        })

    except Exception as e:
        logger.error(f"Shortener error: {str(e)}", exc_info=True)
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


# def check_user(request):
#     chat_id = int(request.GET.get("chat_id"))
#     user = User.objects.filter(id=chat_id).first()
#     status = user.profile.sub_status
#     return JsonResponse({'status':status})

@csrf_exempt
def check_user(request):
    
    try:
        # Validate chat_id parameter
        chat_id = request.GET.get("chat_id")
        if not chat_id:
            return JsonResponse(
                {"error": "chat_id parameter is required"},
                status=400
            )

        try:
            chat_id = int(chat_id)
        except ValueError:
            return JsonResponse(
                {"error": "chat_id must be an integer"},
                status=400
            )

        # Get user and profile
        user = User.objects.filter(id=chat_id).first()
        if not user:
            return JsonResponse(
                {"error": "User not found"},
                status=404
            )

        try:
            profile = user.profile
            return JsonResponse({
                "status": profile.sub_status,
                "user_id": user.id,
                "username": user.username
            })
            
        except Profile.DoesNotExist:
            return JsonResponse(
                {"error": "Profile not found for this user"},
                status=404
            )

    except Exception as e:
        logger.error(f"Error in check_user: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )