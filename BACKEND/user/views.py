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

users_collection = db["user"]
invoices_collection = db["invoices"]

# Helper to convert ObjectId to string
def safe_objectid(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


@api_view(['POST'])
def login_user(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=400)

    user = users_collection.find_one({"username": username})

    if not user:
        return Response({"error": "User not found"}, status=404)

    if user.get("password") != password:
        return Response({"error": "Incorrect password"}, status=401)

    # Determine role
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
