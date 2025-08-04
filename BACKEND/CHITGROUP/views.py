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
    serializer = ChitGroupSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data

        # 🔐 Only admin allowed
        if data.get("created_by") != "admin123":
            return Response({"error": "Only admins can create chit groups."}, status=403)

        chit_value = data.get("chit_value")
        total_members = data.get("total_members")

        # 🕓 Joining window
        try:
            join_start = datetime.fromisoformat(request.data.get("join_start"))
            join_end = datetime.fromisoformat(request.data.get("join_end"))
        except Exception as e:
            return Response({"error": "Invalid join_start or join_end format. Must be ISO datetime."}, status=400)

        if join_end <= join_start:
            return Response({"error": "Joining end time must be after start time."}, status=400)

        # 📅 Convert start date (optional)
        start_date = data.get("start_date")
        if not isinstance(start_date, datetime):
            start_datetime = datetime.combine(start_date, datetime.min.time())
        else:
            start_datetime = start_date

        # ➕ Duration = members + 1
        duration = total_members + 1

        # 🏆 Prize Money: increasing from 50% to 100%
        prize_money = []
        min_percent = 50
        max_percent = 100
        if total_members > 0:
            increment = (max_percent - min_percent) / (total_members - 1) if total_members > 1 else 0
            for i in range(total_members):
                percent = min_percent + i * increment
                prize = int((percent / 100) * chit_value)
                prize_money.append(prize)

        # 📦 Final chit group object
        chit_group = {
            "group_name": data.get("group_name"),
            "chit_value": chit_value,
            "duration": duration,
            "monthly_contribution": data.get("monthly_contribution", 0),
            "total_members": total_members,
            "type": data.get("type", "lotterybased"),
            "start_date": start_datetime,
            "created_by": data.get("created_by"),
            "members": [],
            "status": "active",
            "current_month": 1,
            "min_bid_start_percent": 50,
            "min_bid_step": 5,
            "prize_money": prize_money,
            "join_start": join_start,
            "join_end": join_end,
            "winners": []
        }

        chits_collection.insert_one(chit_group)
        return Response({"message": "Chit group created successfully.", "prize_money": prize_money})
    
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def join_chit_group(request):
    data = request.data
    group_id = data.get("chit_group_id")  
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

    group_name = group.get("group_name", "Unnamed Group")  # Fallback if not found

    # Add user to group's members list if not already
    if user_obj_id  not in group.get("members", []):
        chits_collection.update_one(
            {"_id": group_obj_id},
            {"$addToSet": {"members": user_obj_id }}  # Avoids duplicates
        )
    group_type = group.get("type", "unknown")  
    user = users_collection.find_one({"_id": user_obj_id})
    if user:
        for chit in user.get("joined_chits", []):
            if chit.get("chit_group_id") == group_obj_id:
                return Response({"message": "User already joined this chit group."}, status=200)



    # Prepare joined chit object
    joined_chit = {
        "chit_group_id": group_obj_id,
        "group_name": group_name,
        "type": group_type,
        "joined_on": datetime.utcnow(),
        "has_paid_initial": False,
        "has_won": False,
        "bids": [],
        "invoices": []
    }

    users_collection.update_one(
    {"_id": user_obj_id},
    {"$addToSet": {"joined_chits": joined_chit}}
)

    return Response({"message": "User successfully joined chit group."}, status=200)


    # Add to user's joined_chits array
@api_view(['GET'])
def list_chit_groups(request):
    groups = list(chits_collection.find({}))  # don't filter out _id here
    return JsonResponse(groups, safe=False, json_dumps_params={"default": str})

@api_view(['GET'])
def list_available_groups(request, username):
    groups = list(chits_collection.find({
        "members": {"$ne": username}, 
        "status": "active"
    }))

    auction_groups = [g for g in groups if g.get("type") == "auctionbased"]
    lottery_groups = [g for g in groups if g.get("type") == "lotterybased"]

    return JsonResponse({
        "auctionbased": auction_groups,
        "lotterybased": lottery_groups
    }, safe=False, json_dumps_params={"default": str})
