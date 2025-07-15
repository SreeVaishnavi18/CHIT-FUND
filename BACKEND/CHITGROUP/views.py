from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import ChitGroupSerializer
from .models import ChitGroup

from datetime import datetime
from db_conection import db
chits_collection = db['chit_groups']
users_collection= db['user']

@api_view(['POST'])
def create_chit_group(request):
    # data = request.data
    serializer = ChitGroupSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data


    # Check if user is admin 
        if data.get("created_by") != "admin123":
            return Response({"error": "Only admins can create chit groups."}, status=403)

        chit_group = {
            "group_name": data.get("group_name"),
            "chit_value": data.get("chit_value"),
            "duration": data.get("duration"),
            "monthly_contribution": data.get("monthly_contribution"),
            "total_members": data.get("total_members"),
            "start_date": data.get("start_date", datetime.utcnow().isoformat()),
            "created_by": data.get("created_by"),
            "members": [],
            "status": "active",
            "current_month": 1
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

    users_collection.update_one(
        {"username": username},
        {"$push": {
            "joined_chits": {
                "chit_group_id": group["_id"],
                "joined_on": datetime.utcnow(),
                "has_paid_initial": False,
                "has_won": False,
                "bids": [],
                "invoices": []
            }
        }}
    )


    return Response({"message": f"{username} joined the group {group_name}."})

@api_view(['GET'])
def list_chit_groups(request):
    groups = list(chits_collection.find({}, {"_id": 0}))  
    return Response(groups)


@api_view(['GET'])
def list_available_groups(request, username):
    groups = list(chits_collection.find(
        {
            "members": {"$ne": username}, 
            "status": "active"
        },
        {"_id": 0}
    ))
    return Response(groups)
