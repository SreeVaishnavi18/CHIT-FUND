from rest_framework import serializers

class ChitGroupSerializer(serializers.Serializer):
    _id = serializers.SerializerMethodField()
    group_name = serializers.CharField(max_length=100)
    chit_value = serializers.IntegerField()
    duration = serializers.IntegerField()
    monthly_contribution = serializers.IntegerField()
    total_members = serializers.IntegerField()
    type = serializers.ChoiceField(choices=["lotterybased", "auctionbased"])  
    created_by = serializers.CharField()
    start_date = serializers.DateField(required=False)
    status = serializers.CharField(default="active")
    current_month = serializers.IntegerField(default=1)
    prize_money = serializers.ListField(
        child=serializers.IntegerField(), required=False,allow_empty=True
    )
    closed_auctions = serializers.SerializerMethodField()

    def get__id(self, obj):
        return str(obj.get("_id"))

    def get_closed_auctions(self, obj):
        chit_group_id = str(obj.get("_id"))
        closed_auctions_data = self.context.get("closed_auctions_by_group_id", {})
        return closed_auctions_data.get(chit_group_id, [])

class ClosedAuctionSerializer(serializers.Serializer):
    auction_id = serializers.CharField(source='_id')
    auction_end_time = serializers.DateTimeField()
    amount = serializers.IntegerField()
