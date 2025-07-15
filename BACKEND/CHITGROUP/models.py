from django.db import models

# Create your models here.
class ChitGroup:
    def __init__(self, group_name, chit_value, duration, monthly_contribution,
                 total_members, created_by, start_date=None, members=None, status="active", current_month=1):
        self.group_name = group_name
        self.chit_value = chit_value
        self.duration = duration
        self.monthly_contribution = monthly_contribution
        self.total_members = total_members
        self.created_by = created_by
        self.start_date = start_date
        self.members = members or []
        self.status = status
        self.current_month = current_month

    def to_dict(self):
        return self.__dict__
