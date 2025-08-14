# auctions/views.py (updated)
import random
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId
from pymongo.errors import PyMongoError
from datetime import datetime
from db_conection import db
from .serializers import AuctionSerializer, BidSerializer
import json
from rest_framework.response import Response
import requests

auctions_collection = db['auctions']
chits_collection = db['chit_groups']
users_collection = db['user']
invoices_collection = db['invoices']
winners_collection = db['winners']
EMAIL_API_URL = "http://192.168.167.21:5000/service/send_email"

def send_invoice_email(user_email, invoice):
    """
    Send an invoice to the user via email API (no encryption).
    """
    if not user_email:
        return False

    payload = {
        "from": "admin@lakshmi.com",
        "to": user_email,
        "subject": f"Invoice for Chit Group {invoice['chit_group_id']}",
        "body": f"Dear User,\n\nPlease find your invoice details below:\n\n{invoice}",
        "attachment": None
    }

    headers = {
        "X-API-KEY": "0898c79d9edee1eaf79e1f97718ea84da47472f70884944ba1641b58ed24796c",
        "X-CLIENT-SECRET": "gAAAAABonHWC_8L0gU4ztDHyN9fgk3FRcZ5KTc-TmJ72U4cyRCo9ATH_IUex-NrehgtsZaDxi9vl_vvpTgTKG2veDKGb07SOGeEeHxyLlSbMTw3Y7k_PVjWBT1Bqdxmakw-mhS6se6H4",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(EMAIL_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send invoice email to {user_email}: {e}")
        return False


# Helper
def safe_objectid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None
    
    

def serialize_doc(doc):
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]

    if isinstance(doc, dict):
        serialized = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                serialized[k] = str(v)
            elif isinstance(v, datetime):
                serialized[k] = v.isoformat()
            elif isinstance(v, list):
                serialized[k] = [serialize_doc(i) for i in v]
            elif isinstance(v, dict):
                serialized[k] = serialize_doc(v)
            else:
                serialized[k] = v
        return serialized

    return doc

def convert_object_ids(doc):
    if isinstance(doc, list):
        return [convert_object_ids(item) for item in doc]
    elif isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, datetime):
                new_doc[k] = v  # DRF can handle datetime
            elif isinstance(v, list):
                new_doc[k] = convert_object_ids(v)
            elif isinstance(v, dict):
                new_doc[k] = convert_object_ids(v)
            else:
                new_doc[k] = v
        return new_doc
    return doc
  
def convert_object_ids(doc):
    if isinstance(doc, list):
        return [convert_object_ids(item) for item in doc]
    elif isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, datetime):
                new_doc[k] = v  # DRF can handle datetime
            elif isinstance(v, list):
                new_doc[k] = convert_object_ids(v)
            elif isinstance(v, dict):
                new_doc[k] = convert_object_ids(v)
            else:
                new_doc[k] = v
        return new_doc
    return doc

@method_decorator(csrf_exempt, name='dispatch')
class ActiveAuctionsView(View):
    def get(self, request):
        try:
            auctions = list(auctions_collection.find({"status": "active"}))
            # Serialize all ObjectIds and nested fields
            cleaned_auctions = convert_object_ids(auctions)
            serializer = AuctionSerializer(cleaned_auctions, many=True)
            return JsonResponse(convert_object_ids(auctions), safe=False, json_dumps_params={'default': str})
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)  

@method_decorator(csrf_exempt, name='dispatch')
class ClosedAuctionsView(View):
    def get(self, request):
        try:
            auctions = list(auctions_collection.find({"status": "closed"}))
            # Serialize all ObjectIds and nested fields
            cleaned_auctions = convert_object_ids(auctions)
            serializer = AuctionSerializer(cleaned_auctions, many=True)
            return JsonResponse(convert_object_ids(auctions), safe=False, json_dumps_params={'default': str})
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)  
@method_decorator(csrf_exempt, name='dispatch')
class AuctionDetailView(View):
    def get(self, request, auction_id):
        obj_id = safe_objectid(auction_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid auction ID."}, status=400)

        auction = auctions_collection.find_one({"_id": obj_id})
        if not auction:
            return JsonResponse({"error": "Auction not found."}, status=404)

        auction['_id'] = str(auction['_id'])
        auction['chit_group_id'] = str(auction['chit_group_id'])
        return JsonResponse(serialize_doc(auction), status=200)


# @method_decorator(csrf_exempt, name='dispatch')
# class StartAuctionView(View):
#     def post(self, request, chit_id):
#         chit_obj_id = safe_objectid(chit_id)
#         if not chit_obj_id:
#             return JsonResponse({"error": "Invalid chit ID."}, status=400)

#         chit_group = chits_collection.find_one({"_id": chit_obj_id})
#         if not chit_group:
#             return JsonResponse({"error": "Chit group not found."}, status=404)

#         existing = auctions_collection.find_one({"chit_group_id": chit_obj_id, "status": "active"})
#         if existing:
#             return JsonResponse({"error": "An auction is already active for this chit group."}, status=400)

#         auction_doc = {
#             "chit_group_id": chit_obj_id,
#             "start_time": datetime.utcnow(),
#             "status": "active",
#             "bids": []
#         }
#         auctions_collection.insert_one(auction_doc)
#         return JsonResponse(serialize_doc(auction_doc), status=201)   
@method_decorator(csrf_exempt, name='dispatch')
class StartAuctionView(View):
    def post(self, request, chit_id):
        chit_obj_id = safe_objectid(chit_id)
        if not chit_obj_id:
            return JsonResponse({"error": "Invalid chit ID."}, status=400)

        chit_group = chits_collection.find_one({"_id": chit_obj_id})
        if not chit_group:
            return JsonResponse({"error": "Chit group not found."}, status=404)

        # Validate current_month vs duration
        current_month = chit_group.get("current_month")
        duration = chit_group.get("duration")
        if current_month is None or duration is None:
            return JsonResponse({"error": "Missing current_month or duration in chit group."}, status=400)

        if current_month >= duration:
            return JsonResponse({"error": "Chit group has already completed its full duration."}, status=400)

        # Check if auction is already active
        existing = auctions_collection.find_one({"chit_group_id": chit_obj_id, "status": "active"})
        if existing:
            return JsonResponse({"error": "An auction is already active for this chit group."}, status=400)

        # Create new auction
        auction_doc = {
            "chit_group_id": chit_obj_id,
            "start_time": datetime.utcnow(),
            "status": "active",
            "bids": []
        }
        # auctions_collection.insert_one(auction_doc)
        # auction_id = auctions_collection.inserted_id
        auction_insert = auctions_collection.insert_one(auction_doc)
        auction_id = auction_insert.inserted_id 

        if chit_group.get("type") == "lotterybased":
            monthly_contribution = chit_group.get("monthly_contribution")
            members = chit_group.get("members", [])

            invoices = []
            for user_id in members:
                invoice_doc = {
                    "user_id": user_id,
                    "chit_group_id": chit_obj_id,
                    "auction_id": auction_id,
                    "month": (current_month or 0) + 1,
                    "type": "monthly",
                    "amount": monthly_contribution,
                    "is_paid": False,
                    "issued_on": datetime.utcnow(),
                    "details": {
                        "dividend": monthly_contribution,
                        "is_winner": False  # Initially false, will update later if winner
                    }
                }
                invoices.append(invoice_doc)

            if invoices:
                invoices_collection.insert_many(invoices)

        return JsonResponse(serialize_doc(auction_doc), status=201)

@method_decorator(csrf_exempt, name='dispatch')
class CloseAuctionView(View):
    def post(self, request, auction_id):
        obj_id = safe_objectid(auction_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid auction ID."}, status=400)

        auction = auctions_collection.find_one({"_id": obj_id})
        if not auction or auction['status'] != 'active':
            return JsonResponse({"error": "Auction not active or not found."}, status=404)

        chit_group = chits_collection.find_one({"_id": auction['chit_group_id']})
        if not chit_group:
            return JsonResponse({"error": "Chit group not found."}, status=404)

        current_month = chit_group["current_month"]
        members = chit_group.get("members", [])
        num_members = chit_group.get("total_members", len(members))
        monthly_contribution = chit_group["monthly_contribution"]
        monthly_bids = chit_group.get("monthly_bid_values", {})

        invoices_created = 0

        # Organizer Commission Month (Month 2)
        if current_month == 2:
            commission_amount = int(monthly_bids.get(str(current_month), 0))
            per_user_dividend = commission_amount // num_members

            for user_id in members:
                user = users_collection.find_one({"_id": user_id})
                if not user:
                    continue

                invoice = {
                    "user_id": user_id,
                    "chit_group_id": chit_group["_id"],
                    "auction_id": auction["_id"],
                    "month": current_month,
                    "type": "monthly",
                    "amount": per_user_dividend,
                    "is_paid":False,
                    "issued_on": datetime.utcnow(),
                    "details": {
                        "dividend": per_user_dividend,
                        "is_winner": False,
                        "note": "Organizer commission month"
                    }
                }

                invoices_collection.insert_one(invoice)
                user_email = user.get("email")
                if user_email:
                    var = send_invoice_email(user_email, invoice)
                    print(var)

                invoices_created += 1

            auctions_collection.update_one({"_id": obj_id}, {
                "$set": {
                    "status": "closed",
                    "winner": "Organizer (Commission)",
                    "end_time": datetime.utcnow()
                }
            })

            chits_collection.update_one({"_id": chit_group["_id"]}, {
                "$push": {"closed_auctions": auction["_id"]},
                "$set": {"current_month": current_month + 1}
            })

            return JsonResponse({
                "message": "Organizer commission month processed. No user winner.",
                "dividend": per_user_dividend,
                "invoices_generated": invoices_created
            })


        # previous_winners = chit_group.get("winners", [])
        # remaining_users = [uid for uid in members if uid not in previous_winners]
        previous_winners = [str(wid) for wid in chit_group.get("winners", [])]
        remaining_users = [uid for uid in members if str(uid) not in previous_winners]
        bids = auction.get("bids", [])
        if not bids or all(b is None or b == {} for b in bids):
            # No one bid this month and it's NOT the 2nd month (organizer commission already handled above)
            if current_month != 2:
                eligible_users = [uid for uid in members if str(uid) not in previous_winners]
                if not eligible_users:
                    return JsonResponse({"error": "No eligible user s for random selection."}, status=400)

                winner_id = random.choice(eligible_users)

                if chit_group.get("type") == "lotterybased":
                    # Just store the winner, no dividends issued
                    auctions_collection.update_one({"_id": obj_id}, {
                        "$set": {
                            "status": "closed",
                            "winner": {
                                "user_id": str(winner_id),
                                "note": "Random winner (no bids, lottery-based)"
                            },
                            "end_time": datetime.utcnow()
                        }
                    })

                    chits_collection.update_one({"_id": chit_group["_id"]}, {
                        "$push": {"winners": winner_id, "closed_auctions": auction["_id"]},
                        "$set": {"current_month": current_month + 1}
                    })

                    return JsonResponse({
                        "message": "No bids. Random winner selected for lottery-based chit.",
                        "winner": str(winner_id)
                    })

                else:
                    # Auction-based: divide full contribution among all users
                    bid_amount = monthly_contribution
                    per_user_dividend = bid_amount // num_members

                    for user_id in members:
                        user = users_collection.find_one({"_id": user_id})
                        if not user:
                            continue

                        invoice = {
                            "user_id": user_id,
                            "chit_group_id": chit_group["_id"],
                            "auction_id": auction["_id"],
                            "month": current_month,
                            "type": "monthly",
                            "amount": per_user_dividend,
                            "is_paid": False,
                            "issued_on": datetime.utcnow(),
                            "details": {
                                "dividend": per_user_dividend,
                                "is_winner": (str(user_id) == str(winner_id)),
                                "note": "Random winner assigned due to no bids"
                            }
                        }

                        invoices_collection.insert_one(invoice)
                        user_email = user.get("email")
                        if user_email:
                            var = send_invoice_email(user_email, invoice)
                            print("mail sent" ,var)

                        invoices_created += 1

                    auctions_collection.update_one({"_id": obj_id}, {
                        "$set": {
                            "status": "closed",
                            "winner": {
                                "user_id": str(winner_id),
                                "amount": bid_amount,
                                "note": "Randomly assigned due to no bids"
                            },
                            "end_time": datetime.utcnow()
                        }
                    })

                    chits_collection.update_one({"_id": chit_group["_id"]}, {
                        "$push": {"winners": winner_id, "closed_auctions": auction["_id"]},
                        "$set": {"current_month": current_month + 1}
                    })

                    # End chit if it's the last month
                    if (current_month + 1) > chit_group["duration"]:
                        chits_collection.update_one({"_id": chit_group["_id"]}, {
                            "$set": {"status": "completed", "members": []}
                        })

                    return JsonResponse({
                        "message": "No bids. Random winner selected. Dividend distributed.",
                        "winner": str(winner_id),
                        "bid_amount": bid_amount,
                        "per_user_dividend": per_user_dividend,
                        "invoices_generated": invoices_created
                    })
            else:
                return JsonResponse({"error": "No bids found."}, status=400)

        if current_month == chit_group["duration"]:
            if len(remaining_users) != 1:
                return JsonResponse({"error": "Cannot determine unique final winner."}, status=400)

            winner_id = remaining_users[0]
            bid_amount = int(monthly_bids.get(str(current_month), monthly_contribution))
            per_user_dividend = bid_amount // num_members

            for user_id in members:
                user = users_collection.find_one({"_id": ObjectId(user_id)})  
                if not user:
                    continue

                invoice = {
                    "user_id": user_id,
                    "chit_group_id": chit_group["_id"],
                    "auction_id": auction["_id"],
                    "month": current_month,
                    "type": "monthly",
                    "is_paid":False,
                    "amount": per_user_dividend,
                    "issued_on": datetime.utcnow(),
                    "details": {
                        "dividend": per_user_dividend,
                        "is_winner": (str(user_id) == str(winner_id)),
                        "note": "Final month – auto winner"
                    }
                }

                invoices_collection.insert_one(invoice)
                user_email = user.get("email")
                if user_email:
                    var = send_invoice_email(user_email, invoice)
                    print("mail sent ",var)

                invoices_created += 1

            chits_collection.update_one({"_id": chit_group["_id"]}, {
                "$push": {"winners": winner_id, "closed_auctions": auction["_id"]},
                "$set": {"current_month": current_month + 1, "status": "completed", "members": []}
            })

            auctions_collection.update_one({"_id": obj_id}, {
                "$set": {
                    "status": "closed",
                    "winner": {
                        "user_id": str(winner_id),
                        "amount": bid_amount,
                        "note": "Auto-assigned winner in final month"
                    },
                    "end_time": datetime.utcnow()
                }
            })

            return JsonResponse({
                "message": "Final month processed. Winner auto-assigned.",
                "winner": str(winner_id),
                "bid_amount": bid_amount,
                "is_paid":False,
                "per_user_dividend": per_user_dividend,
                "invoices_generated": invoices_created
            })
    
        if chit_group.get("type") == "lotterybased":
            bidders = [bid["user_id"] for bid in auction.get("bids", [])]
            unique_bidders = list(set(bidders))

            if not unique_bidders:
                return JsonResponse({"error": "No users participated in bidding."}, status=400)

            winner_id = random.choice(unique_bidders)

            auctions_collection.update_one({"_id": obj_id}, {
                "$set": {
                    "status": "closed",
                    "winner": {
                        "user_id": str(winner_id),
                        "note": "Randomly chosen in lottery-based auction"
                    },
                    "end_time": datetime.utcnow()
                }
            })

            chits_collection.update_one({"_id": chit_group["_id"]}, {
                "$push": {"winners": winner_id, "closed_auctions": auction["_id"]},
                "$set": {"current_month": current_month + 1}
            })

            return JsonResponse({
                "message": "Lottery-based auction closed.",
                "winner": str(winner_id)
            })
        # Regular Auction Month

        valid_bids = [b for b in bids if b["user_id"] not in previous_winners]
        if not valid_bids:
            return JsonResponse({"error": "No valid bids (previous winners excluded)."}, status=400)

        winner_bid = min(valid_bids, key=lambda b: b["amount"])
        winner_id = winner_bid["user_id"]
        bid_amount = winner_bid["amount"]
        per_user_dividend = bid_amount // num_members

        for user_id in members:
            user = users_collection.find_one({"_id": user_id})
            if not user:
                continue

            is_winner = (str(user_id) == str(winner_id))

            invoice = {
                "user_id": user_id,
                "chit_group_id": chit_group["_id"],
                "auction_id": auction["_id"],
                "month": current_month,
                "type": "monthly",
                "amount": per_user_dividend,
                "is_paid":False,
                "issued_on": datetime.utcnow(),
                "details": {
                    "dividend": per_user_dividend,
                    "is_winner": is_winner
                }
            }

            invoices_collection.insert_one(invoice)
            user_email = user.get("email")
            if user_email:
                var = send_invoice_email(user_email, invoice)
                print("sent mail ",var)

            invoices_created += 1

        auctions_collection.update_one({"_id": obj_id}, {
            "$set": {
                "status": "closed",
                "winner": {
                    "user_id": str(winner_id),
                    "amount": bid_amount
                },
                "end_time": datetime.utcnow()
            }
        })

        chits_collection.update_one({"_id": chit_group["_id"]}, {
            "$push": {"winners": winner_id, "closed_auctions": auction["_id"]},
            "$set": {"current_month": current_month + 1}
        })

        # Optional safeguard
        if (current_month + 1) > chit_group["duration"]:
            chits_collection.update_one({"_id": chit_group["_id"]}, {
                "$set": {"status": "completed", "members": []}
            })

        return JsonResponse({
            "message": "Auction closed successfully.",
            "winner": str(winner_id),
            "bid_amount": bid_amount,
            "is_paid":False,
            "per_user_dividend": per_user_dividend,
            "invoices_generated": invoices_created
        })



@method_decorator(csrf_exempt, name='dispatch')
class AuctionBidsView(View):
    def get(self, request, auction_id):
        auction = auctions_collection.find_one({"_id": safe_objectid(auction_id)})
        if not auction:
            return JsonResponse({"error": "Auction not found."}, status=404)

        return JsonResponse(serialize_doc(auction.get("bids", [])), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class SubmitBidView(View):
    def post(self, request, auction_id):
        try:
            auction_obj_id = safe_objectid(auction_id)
            auction = auctions_collection.find_one({"_id": auction_obj_id})
            if not auction or auction['status'] != 'active':
                return JsonResponse({"error": "Auction not active or not found."}, status=400)

            data = json.loads(request.body)
            user_id = safe_objectid(data.get("user_id"))
            amount = data.get("amount")

            if not user_id or amount is None:
                return JsonResponse({"error": "user_id and amount are required."}, status=400)

            for bid in auction.get("bids", []):
                if bid["user_id"] == user_id:
                    return JsonResponse({"error": "User already placed a bid."}, status=400)

            chit_group = chits_collection.find_one({"_id": auction['chit_group_id']})
            if not chit_group:
                return JsonResponse({"error": "Chit group not found."}, status=404)

            chit_type = chit_group.get("type", "auctionbased")

            previous_winners = chit_group.get("winners", [])
            if str(user_id) in [str(winner_id) for winner_id in previous_winners]:
                return JsonResponse({"error": "Previous winners are not allowed to bid again."}, status=403)

            current_month = chit_group.get("current_month", 1)
            monthly_bids = chit_group.get("prize_money", {})

            if chit_group.get("duration") == current_month:
                return JsonResponse({"error": "This month is the final month. Bidding not allowed."})

            if current_month == 2:
                return JsonResponse({
                    "error": "This month is reserved for organization. Bidding not allowed."
                }, status=403)

            # 👇 Handle bidding logic differently for lotterybased
            if chit_type == "lotterybased":
                # For lottery-based, no strict bid amount check
                bid = {
                    "user_id": user_id,
                    "amount": amount,
                    "bid_time": datetime.utcnow()
                }

                auctions_collection.update_one(
                    {"_id": auction_obj_id},
                    {"$push": {"bids": bid}}
                )

                return JsonResponse({"message": "Lottery request submitted successfully."})

            # 👇 Regular auction logic
            # Must be string keys in MongoDB
            current_month -=1
            month_bid_entry = monthly_bids[current_month]
            if month_bid_entry is None:
                return JsonResponse({"error": f"No bid value configured for month {current_month}."}, status=400)

            allowed_bid = int(month_bid_entry)

            if amount > allowed_bid:
                return JsonResponse({
                    "error": f"Bid too high. Max allowed for month {current_month} is ₹{allowed_bid}."
                }, status=400)

            bid = {
                "user_id": user_id,
                "amount": amount,
                "bid_time": datetime.utcnow()
            }

            auctions_collection.update_one(
                {"_id": auction_obj_id},
                {"$push": {"bids": bid}}
            )

            return JsonResponse({"message": "Bid placed successfully."})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class MyBidView(View):
    def get(self, request, auction_id):
        user_id = request.headers.get("X-User-ID")
        user_obj_id = safe_objectid(user_id)
        if not user_obj_id:
            return JsonResponse({"error": "Unauthorized or missing user ID."}, status=401)

        auction = auctions_collection.find_one({"_id": safe_objectid(auction_id)})
        if not auction:
            return JsonResponse({"error": "Auction not found."}, status=404)

        for bid in auction.get("bids", []):
            if bid["user_id"] == user_obj_id:
                bid["user_id"] = str(bid["user_id"])
                return JsonResponse(bid)

        return JsonResponse({"message": "No bid found for this user."})
# Helper
def safe_objectid(val):
    try:
        return ObjectId(val)
    except Exception:
        return None

@method_decorator(csrf_exempt, name='dispatch')
class AuctionWinnerView(View):
    def get(self, request, auction_id):
        auction = auctions_collection.find_one({"_id": safe_objectid(auction_id)})
        if not auction:
            return JsonResponse({"error": "Auction not found."}, status=404)

        winner = auction.get("winner")
        if not winner:
            return JsonResponse({"message": "No winner selected yet."}, status=200)

        # 🛡️ Check if winner is a dict or string
        if isinstance(winner, dict):
            winner["user_id"] = str(winner["user_id"])
            return JsonResponse(winner)
        else:
            return JsonResponse({"winner": winner})  # e.g., "Organizer (Commission)"

    


@method_decorator(csrf_exempt, name='dispatch')
class UserWinsView(View):
    def get(self, request, user_id):
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid user ID"}, status=400)

        auctions = list(auctions_collection.find({"winner.user_id": obj_id}))
        return JsonResponse(serialize_doc(auctions), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class UserInvoicesView(View):
    def get(self, request, user_id):
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid user ID."}, status=400)

        invoices = list(invoices_collection.find({"user_id": obj_id}))
        return JsonResponse(serialize_doc(invoices), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceDetailView(View):
    def get(self, request, invoice_id):
        obj_id = safe_objectid(invoice_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid invoice ID."}, status=400)

        invoice = invoices_collection.find_one({"_id": obj_id})
        if not invoice:
            return JsonResponse({"error": "Invoice not found."}, status=404)

        return JsonResponse(serialize_doc(invoice), status=200)

@method_decorator(csrf_exempt, name='dispatch')
class MarkInvoicePaidView(View):
    def post(self, request,auction_id):
        try:
            data = json.loads(request.body)
            # auction_id = data.get("auction_id")
            auction_idd = safe_objectid(auction_id)
            user_id = data.get("user_id")
            user_obj_id = safe_objectid(user_id)

            if not auction_idd or not user_obj_id:
                return JsonResponse({"error": "Missing auction_id or user_id"}, status=400)

            if not ObjectId.is_valid(auction_idd) or not ObjectId.is_valid(user_id):
                return JsonResponse({"error": "Invalid auction_id or user_id"}, status=400)

            result = invoices_collection.update_one(
                {
                    "auction_id": ObjectId(auction_idd),
                    "user_id": ObjectId(user_id)
                },
                {
                    "$set": {"is_paid": True}
                }
            )

            if result.modified_count == 1:
                return JsonResponse({"message": "Invoice marked as paid"}, status=200)
            else:
                print(result.modified_count)
                return JsonResponse({"message": "Invoice not found or already paid"}, status=404)

        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        

@method_decorator(csrf_exempt, name='dispatch')
class MarkPaymentDoneView(View):
    def post(self, request, auction_id):
        import json
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")

            if not ObjectId.is_valid(auction_id) or not ObjectId.is_valid(user_id):
                return JsonResponse({"error": "Invalid auction ID or user ID"}, status=400)

            result = auctions_collection.update_one(
                {"_id": ObjectId(auction_id)},
                {"$addToSet": {"aid": ObjectId(user_id)}}  # ensures no duplicates
            )

            if result.modified_count == 1:
                return JsonResponse({"message": "Payment marked successfully"}, status=200)
            else:
                return JsonResponse({"message": "User was already marked as paid or auction not found"}, status=200)
        except PyMongoError as e:
            return JsonResponse({"error": str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        

class UserInvoicesWithChitNameView(View):
    def get(self, request, user_id):
        obj_id = safe_objectid(user_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid user ID."}, status=400)

        # Fetch invoices for this user
        invoices = list(invoices_collection.find({"user_id": obj_id}))
        
        # Attach chit group name to each invoice
        for inv in invoices:
            chit = chits_collection.find_one({"_id": safe_objectid(inv["chit_group_id"])})
            inv["chit_group_name"] = chit.get("group_name") if chit else "Unknown"

        return JsonResponse(serialize_doc(invoices), safe=False)


          
