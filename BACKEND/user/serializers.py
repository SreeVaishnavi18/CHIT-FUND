from rest_framework import serializers
from bson import ObjectId

# Helper to convert ObjectId to string and vice-versa
class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)

    def to_internal_value(self, data):
        try:
            return ObjectId(str(data))
        except Exception:
            raise serializers.ValidationError("Invalid ObjectId")

# 🎯 Serializer for each joined chit
class JoinedChitSerializer(serializers.Serializer):
    chit_group_id = ObjectIdField()
    joined_on = serializers.DateTimeField()
    has_paid_initial = serializers.BooleanField()
    has_won = serializers.BooleanField()
    bids = serializers.ListField(child=ObjectIdField(), required=False)
    invoices = serializers.ListField(child=ObjectIdField(), required=False)

# 🎯 Main User Serializer with embedded chit participation
class UserSerializer(serializers.Serializer):
    _id = ObjectIdField(read_only=True)
    external_id = serializers.CharField(required=False)
    username = serializers.CharField(required=True)     
    password = serializers.CharField(write_only=True)   
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    is_verified = serializers.BooleanField()
    last_active = serializers.DateTimeField(required=False)
    joined_chits = JoinedChitSerializer(many=True, required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
