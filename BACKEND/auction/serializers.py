# auctions/serializers.py
from rest_framework import serializers

class AuctionSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    chit_group_id = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=["active", "closed"])
    winner = serializers.DictField(required=False, allow_null=True)
    bids = serializers.ListField(child=serializers.DictField(), default=[])

class BidSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    amount = serializers.FloatField()
    bid_time = serializers.DateTimeField()

class TransactionSerializer(serializers.Serializer):
    txId = serializers.CharField(max_length=100)
    reference = serializers.CharField(max_length=200, required=False, allow_blank=True)
    merchant = serializers.CharField(max_length=200, required=False, allow_blank=True)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    accountNumber = serializers.CharField(max_length=50)
    ifsc = serializers.CharField(max_length=20)
    amount = serializers.FloatField()
    status = serializers.CharField(max_length=50)
    timestamp = serializers.DateTimeField()
    auction_id = serializers.CharField(max_length=100)  