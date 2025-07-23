from bson import ObjectId
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ChitGroupSerializer
from .models import ChitGroup

from datetime import datetime
from db_conection import db
chits_collection = db['chit_groups']
users_collection = db['user']
@api_view(['POST'])
def create_chit_group(request):
    # data = request.data
    serializer = ChitGroupSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data


    # Check if user is admin 
        if data.get("created_by") != "admin123":
            return Response({"error": "Only admins can create chit groups."}, status=403)

        start_date = data.get("start_date")
        if isinstance(start_date, datetime):
            start_datetime = start_date
        else:
            start_datetime = datetime.combine(start_date, datetime.min.time())

        chit_group = {
            "group_name": data.get("group_name"),
            "chit_value": data.get("chit_value"),
            "duration": data.get("duration"),
            "monthly_contribution": data.get("monthly_contribution"),
            "total_members": data.get("total_members"),
            "start_date": start_datetime,   # ✅ fixed
            "created_by": data.get("created_by"),
            "members": [],
            "status": "active",
            "current_month": 1,
            "min_bid_start_percent": 50,
            "min_bid_step": 5
        }


        chits_collection.insert_one(chit_group)
        return Response({"message": "Chit group created successfully."})
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def join_chit_group(request):
    data = request.data
    group_id = data.get("chit_group_id")  # This should be a string ObjectId
    user_id = data.get("user_id")

    if not group_id or not user_id:
        return Response({"error": "Missing group_id or user_id."}, status=400)

    try:
        group_obj_id = ObjectId(group_id)
        user_obj_id = ObjectId(user_id)
    except Exception as e:
        return Response({"error": "Invalid ObjectId."}, status=400)

    # Check if group exists
    group = chits_collection.find_one({"_id": group_obj_id})
    if not group:
        return Response({"error": "Chit group not found."}, status=404)

    # Add user to group's members list if not already
    if user_id not in group.get("members", []):
        chits_collection.update_one(
            {"_id": group_obj_id},
            {"$addToSet": {"members": user_id}}  # Avoids duplicates
        )

    # Prepare joined chit object
    joined_chit = {
        "chit_group_id": group_obj_id,
        "joined_on": datetime.utcnow(),
        "has_paid_initial": False,
        "has_won": False,
        "bids": [],
        "invoices": []
    }

    # Add to user's joined_chits array
    result = users_collection.update_one(
        {"_id": user_obj_id},
        {"$addToSet": {"joined_chits": joined_chit}}
    )

    if result.modified_count == 0:
        return Response({"message": "User already joined this chit group."}, status=200)

    return Response({"message": "User successfully joined chit group."}, status=200)

@api_view(['GET'])
def list_chit_groups(request):
    groups = list(chits_collection.find({}))  # don't filter out _id here
    return JsonResponse(groups, safe=False, json_dumps_params={"default": str})

@api_view(['GET'])
def list_available_groups(request, username):
    groups = list(chits_collection.find(
        {
            "members": {"$ne": username}, 
            "status": "active"
        },
    ))
    return JsonResponse(groups, safe=False, json_dumps_params={"default": str})
