from datetime import datetime
from django.apps import AppConfig
import threading, time
import os
from db_conection import db

chits_collection = db['chit_groups']
users_collection = db['user']

def finalize_chit_group_prizes():
    try:
        now_time = datetime.now()
        print(f"[{now_time}] Running prize calculation job...")

        groups = chits_collection.find({
            "join_end": {"$lt": now_time},
            "status": "active",
            "prize_money": []
        })

        for group in groups:
            print(f"Processing group: {group.get('group_name', group['_id'])}")

            members = group.get("members", [])
            total_members = len(members)
            chit_value = group.get("chit_value", 0)

            if total_members == 0:
                print("No members in group. Skipping...")
                continue
                
            # Duration is total_members + 1 (one extra month for company)
            prize_money_duration = total_members + 1
            prize_money = []

            # Debug: Print the group type to see what's actually stored
            group_type = group.get("type", "lotterybased")
            print(f"Group type: '{group_type}'")
            
            # Check for lottery-based OR auction-based type (both need progressive pricing)
            if group_type in ["lotterybased", "auctionbased", "lottery", "auction", "lottery_based", "auction_based"] or group_type is None:
                print(f"Processing as progressive pricing chit (type: {group_type})")
                min_percent = 50
                max_percent = 100
                
                # Calculate increment properly for the number of months
                # We want to go from 50% to 100% over (total_members + 1) months
                if prize_money_duration > 1:
                    increment = (max_percent - min_percent) / (prize_money_duration - 1)
                else:
                    increment = 0

                for i in range(prize_money_duration):
                    percent = min_percent + i * increment
                    prize = int((percent / 100) * chit_value)
                    prize_money.append(prize)
                    
                print(f"Prize progression: {[f'{min_percent + i * increment:.1f}%' for i in range(prize_money_duration)]}")
            else:
                print(f"Processing as fixed-amount chit (type: {group_type})")
                prize_money = [int(chit_value)] * prize_money_duration

            monthly_contribution = int(chit_value / total_members)
            print("monthly contribution:", monthly_contribution)

            update_result = chits_collection.update_one(
                {"_id": group["_id"]},
                {
                    "$set": {
                        "prize_money": prize_money,
                        "monthly_contribution": monthly_contribution,
                        "total_members": total_members,
                        "duration": total_members + 1  # Company gets one extra month
                    }
                }
            )

            if update_result.modified_count > 0:
                print(f"Updated group {group.get('group_name', group['_id'])} successfully.")
                print(f"    → Prize Money: {prize_money}")
                print(f"    → Monthly Contribution: {monthly_contribution}")
            else:
                print(f"Failed to update group {group.get('group_name', group['_id'])}.")

    except Exception as e:
        print(f"Error while finalizing chit group prizes: {e}")


# Example to demonstrate the fix:
if __name__ == "__main__":
    # Test with 10 members and 100000 chit value (your specific case)
    total_members = 10
    chit_value = 100000
    min_percent = 50
    max_percent = 100
    
    # Duration is 11 months (10 members + 1 for company)
    prize_money_duration = total_members + 1
    
    if prize_money_duration > 1:
        increment = (max_percent - min_percent) / (prize_money_duration - 1)
    else:
        increment = 0
    
    print(f"For {total_members} members with chit value {chit_value}:")
    print(f"Total duration: {prize_money_duration} months (including 1 month for company)")
    print("Month | Percentage | Prize Amount")
    print("-" * 35)
    
    for i in range(prize_money_duration):
        percent = min_percent + i * increment
        prize = int((percent / 100) * chit_value)
        print(f"  {i+1:2}  |   {percent:5.1f}%   |   {prize:,}")
        
    monthly_contribution = int(chit_value / total_members)
    print(f"\nMonthly contribution per member: {monthly_contribution:,}")
    
def run_prize_money_calculator():
    while True:
        finalize_chit_group_prizes()
        time.sleep(30)  # Every 30 seconds (adjust as needed)

class ChitgroupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CHITGROUP'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            return  # Avoid duplicate thread when using runserver
        threading.Thread(target=run_prize_money_calculator, daemon=True).start()
