from django.http import JsonResponse
from django.views import View
from bson import ObjectId
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from pymongo.errors import PyMongoError
from db_conection import db
from .serializers import UserSerializer, JoinedChitSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64
import requests

users_collection = db["user"]
invoices_collection = db["invoices"]

# Helper to convert ObjectId to string
def safe_objectid(value):
    try:
        return ObjectId(value)
    except Exception:
        return None

from django.http import HttpResponse

def get_public_key(request):
    with open(r"C:\Users\Shiv\Desktop\MEGHA\SEM 9\SOA LAB\chit-fund-backennd\CHIT-FUND\BACKEND\public.pem", "rb") as f:
        public_key = f.read()
    return HttpResponse(public_key, content_type="text/plain")

@api_view(['POST'])
def signup_user(request):
    name = request.data.get("name")
    email = request.data.get("email")
    phone = request.data.get("phone")
    address = request.data.get("address")
    city = request.data.get("city")
    pincode = request.data.get("pincode")
    encrypted_password = request.data.get("password")  # encrypted if you want like login

    if not all([name, email, phone, address, city, pincode, encrypted_password]):
        return Response({"error": "All fields are required"}, status=400)
    
    verify_url = "http://192.168.169.109:5000/service/verify_email"
    headers = {
        # "X-API-KEY": "0898c79d9edee1eaf79e1f97718ea84da47472f70884944ba1641b58ed24796c",
        # "X-CLIENT-SECRET": "gjpCS(sj{UOGE!p3*J=|?hzq^$@Tmot+",
        "Content-Type": "application/json"
    }
    try:
        verify_response = requests.post(
            verify_url,
            json={"email": "danusri@gmail.com"},
            headers=headers,
            timeout=5
        )
        verify_response.raise_for_status()  # raises for HTTP errors

        verify_data = verify_response.json()
        if not verify_data.get("verified", False):
            return Response({"error": "Invalid email address"}, status=400)

    except requests.RequestException as e:
        return Response({"error": f"Email verification request failed: {e}"}, status=502)


    # Password decryption (if encrypted like login)
    try:
        with open(r"C:\Users\Shiv\Desktop\MEGHA\SEM 9\SOA LAB\chit-fund-backennd\CHIT-FUND\BACKEND\private.pem", "rb") as f:
            private_key = RSA.import_key(f.read())
        cipher_rsa = PKCS1_v1_5.new(private_key)
        sentinel = b'Error'
        encrypted_password_bytes = base64.b64decode(encrypted_password)
        password = cipher_rsa.decrypt(encrypted_password_bytes, sentinel).decode('utf-8')
    except Exception as e:
        return Response({"error": "Password decryption failed"}, status=400)

    # Check if email already exists
    if users_collection.find_one({"email": email}):
        return Response({"error": "Email already registered"}, status=409)

    # Create username automatically from email prefix or name
    username = email.split("@")[0]

    # Insert into MongoDB
    new_user = {
        "username": username,
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "pincode": pincode,
        "password": password,  # store hashed ideally
        "role": "user"
    }
    result = users_collection.insert_one(new_user)

    return Response({
        "message": "Signup successful",
        "user_id": str(result.inserted_id),
        "username": username
    }, status=201)

@api_view(['POST'])
def login_user(request):
    username = request.data.get("username")
    encrypted_password = request.data.get("password")  # encrypted password (base64 string)

    if not username or not encrypted_password:
        return Response({"error": "Username and password are required"}, status=400)

    # Load private key once or per request (here for simplicity)
    with open(r"C:\Users\Shiv\Desktop\MEGHA\SEM 9\SOA LAB\chit-fund-backennd\CHIT-FUND\BACKEND\private.pem", "rb") as f:
        private_key = RSA.import_key(f.read())

    cipher_rsa = PKCS1_v1_5.new(private_key)
    sentinel = b'Error'

    try:
        encrypted_password_bytes = base64.b64decode(encrypted_password)
        password = cipher_rsa.decrypt(encrypted_password_bytes,sentinel).decode('utf-8')
    except Exception as e:
        print("Decryption error: ",e)
        return Response({"error": "Password decryption failed."}, status=400)

    user = users_collection.find_one({"username": username})

    if not user:
        return Response({"error": "User not found"}, status=404)

    if user.get("password") != password:
        return Response({"error": "Incorrect password"}, status=401)

    if username == "admin" and password == "admin123":
        role = "admin"
    else:
        role = "user"

    return Response({
        "message": "Login successful",
        "username": username,
        "user_id": str(user["_id"]),
        "role": role
    })

# @api_view(['POST'])
# def login_user(request):
#     username = request.data.get("username")
#     password = request.data.get("password")

#     if not username or not password:
#         return Response({"error": "Username and password are required"}, status=400)

#     user = users_collection.find_one({"username": username})

#     if not user:
#         return Response({"error": "User not found"}, status=404)

#     if user.get("password") != password:
#         return Response({"error": "Incorrect password"}, status=401)

#     # Determine role
#     if username == "admin" and password == "admin123":
#         role = "admin"
#     else:
#         role = "user"

#     return Response({
#         "message": "Login successful",
#         "username": username,
#         "user_id": str(user["_id"]),
#         "role": role
#     })

@method_decorator(csrf_exempt, name='dispatch')
class UserMeView(View):
    def get(self, request):
        user_id = request.GET.get("user_id")

        if not user_id:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid User ID"}, status=400)

        try:
            user = users_collection.find_one({"_id": obj_id})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            serialized = UserSerializer(user)
            return JsonResponse(serialized.data, status=200)
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)


class UserChitsView(View):
    def get(self, request, user_id):
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid User ID"}, status=400)

        try:
            user = users_collection.find_one({"_id": obj_id})
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            joined_chits = user.get("joined_chits", [])
            serializer = JoinedChitSerializer(joined_chits, many=True)
            return JsonResponse(serializer.data, safe=False)
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)


class UserInvoicesView(View):
    def get(self, request, user_id):
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid User ID"}, status=400)

        try:
            invoices = list(invoices_collection.find({"user_id": obj_id}))
            for invoice in invoices:
                invoice["_id"] = str(invoice["_id"])
                invoice["user_id"] = str(invoice["user_id"])
                invoice["chit_group_id"] = str(invoice["chit_group_id"])
            return JsonResponse(invoices, safe=False)
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class MyInvoicesView(View):
    def get(self, request):
        user_id = request.headers.get("X-User-ID")
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Unauthorized or missing ID"}, status=401)

        invoices = list(invoices_collection.find({"user_id": obj_id}))
        for inv in invoices:
            inv["_id"] = str(inv["_id"])
            inv["user_id"] = str(inv["user_id"])
            inv["chit_group_id"] = str(inv["chit_group_id"])
        return JsonResponse(invoices, safe=False)
