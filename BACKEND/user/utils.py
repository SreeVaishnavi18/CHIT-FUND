import jwt
from django.conf import settings
from rest_framework.response import Response

def verify_jwt(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, Response({"error": "Token missing"}, status=401)

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return decoded, None
    except jwt.ExpiredSignatureError:
        return None, Response({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return None, Response({"error": "Invalid token"}, status=401)
