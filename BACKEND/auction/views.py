# auctions/views.py (updated)
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

auctions_collection = db['auctions']
chits_collection = db['chit_groups']
users_collection = db['user']
invoices_collection = db['invoices']

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
            elif isinstance(v, list):
                serialized[k] = [serialize_doc(i) for i in v]
            elif isinstance(v, dict):
                serialized[k] = serialize_doc(v)
            elif hasattr(v, 'isoformat'):  # datetime
                serialized[k] = v.isoformat()
            else:
                serialized[k] = v
        return serialized

    return doc

@method_decorator(csrf_exempt, name='dispatch')
class ActiveAuctionsView(View):
    def get(self, request):
        try:
            auctions = list(auctions_collection.find({"status": "active"}))
            for auction in auctions:
                auction['_id'] = str(auction['_id'])
                auction['chit_group_id'] = str(auction['chit_group_id'])
            return JsonResponse(auctions, safe=False)
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
        return JsonResponse(auction, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class StartAuctionView(View):
    def post(self, request, chit_id):
        chit_obj_id = safe_objectid(chit_id)
        if not chit_obj_id:
            return JsonResponse({"error": "Invalid chit ID."}, status=400)

        chit_group = chits_collection.find_one({"_id": chit_obj_id})
        if not chit_group:
            return JsonResponse({"error": "Chit group not found."}, status=404)

        existing = auctions_collection.find_one({"chit_group_id": chit_obj_id, "status": "active"})
        if existing:
            return JsonResponse({"error": "An auction is already active for this chit group."}, status=400)

        auction_doc = {
            "chit_group_id": chit_obj_id,
            "start_time": datetime.utcnow(),
            "status": "active",
            "bids": []
        }
        auctions_collection.insert_one(auction_doc)
        return JsonResponse({"message": "Auction started."}, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class CloseAuctionView(View):
    def post(self, request, auction_id):
        obj_id = safe_objectid(auction_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid auction ID."}, status=400)

        auction = auctions_collection.find_one({"_id": obj_id})
        if not auction:
            return JsonResponse({"error": "Auction not found."}, status=404)

        if auction['status'] != 'active':
            return JsonResponse({"error": "Auction already closed."}, status=400)

        bids = auction.get("bids", [])
        if not bids:
            return JsonResponse({"error": "No bids to process."}, status=400)

        winner = min(bids, key=lambda b: b['amount'])
        winner_user_id = winner['user_id']

        chit_group = chits_collection.find_one({"_id": auction['chit_group_id']})
        if not chit_group:
            return JsonResponse({"error": "Chit group not found."}, status=404)

        members = chit_group.get("members", [])
        invoices = []
        for member_name in members:
            user = users_collection.find_one({"name": member_name})
            if not user:
                continue
            invoice = {
                "user_id": user["_id"],
                "chit_group_id": chit_group["_id"],
                "amount": chit_group["monthly_contribution"],
                "gst": round(0.18 * chit_group["monthly_contribution"], 2),
                "month": chit_group["current_month"],
                "issued_on": datetime.utcnow()
            }
            invoices_collection.insert_one(invoice)
            invoices.append(invoice)

        auctions_collection.update_one(
            {"_id": obj_id},
            {"$set": {"status": "closed", "winner": winner, "end_time": datetime.utcnow()}}
        )

        chits_collection.update_one(
            {"_id": auction['chit_group_id']},
            {"$inc": {"current_month": 1}}
        )

        return JsonResponse({
            "message": "Auction closed.",
            "winner": winner,
            "invoices_generated": len(invoices)
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

        winner["user_id"] = str(winner["user_id"])
        return JsonResponse(winner)
    


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
        for inv in invoices:
            inv["_id"] = str(inv["_id"])
            inv["user_id"] = str(inv["user_id"])
            inv["chit_group_id"] = str(inv["chit_group_id"])
        return JsonResponse(invoices, safe=False)

@method_decorator(csrf_exempt, name='dispatch')
class InvoiceDetailView(View):
    def get(self, request, invoice_id):
        obj_id = safe_objectid(invoice_id)
        if not obj_id:
            return JsonResponse({"error": "Invalid invoice ID."}, status=400)

        invoice = invoices_collection.find_one({"_id": obj_id})
        if not invoice:
            return JsonResponse({"error": "Invoice not found."}, status=404)

        invoice["_id"] = str(invoice["_id"])
        invoice["user_id"] = str(invoice["user_id"])
        invoice["chit_group_id"] = str(invoice["chit_group_id"])
        return JsonResponse(invoice, status=200)
