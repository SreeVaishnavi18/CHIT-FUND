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
            "min_bid_step": 5,
            "prize_money": data.get("prize_money", [])
        }


        chits_collection.insert_one(chit_group)
        return Response({"message": "Chit group created successfully."})
    return Response(serializer.errors, status=400)


@api_view(['POST'])
def join_chit_group(request):
    data = request.data
    group_name = data.get("group_name")
    username = data.get("username")

    # Check if group exists
    group = chits_collection.find_one({"group_name": group_name})
    if not group:
        return Response({"error": "Chit group not found."}, status=404)

    # Check if user is already a member
    if username in group["members"]:
        return Response({"message": "Already joined this group."}, status=400)

    # Add user to members list
    chits_collection.update_one(
        {"group_name": group_name},
        {"$push": {"members": username}}
    )

    return Response({"message": f"{username} joined the group {group_name}."})

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
        {"_id": 0}
    ))
    return JsonResponse(groups, safe=False, json_dumps_params={"default": str})
