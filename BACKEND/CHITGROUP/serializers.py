from rest_framework import serializers

class ChitGroupSerializer(serializers.Serializer):
    _id = serializers.SerializerMethodField()
    group_name = serializers.CharField(max_length=100)
    chit_value = serializers.IntegerField()
    duration = serializers.IntegerField()
    monthly_contribution = serializers.IntegerField()
    total_members = serializers.IntegerField()
    created_by = serializers.CharField()
    start_date = serializers.DateField(required=False)
    status = serializers.CharField(default="active")
    current_month = serializers.IntegerField(default=1)
    def get__id(self, obj):
        return str(obj['_id'])  # Convert ObjectId to string
