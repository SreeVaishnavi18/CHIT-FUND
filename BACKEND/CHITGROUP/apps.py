from datetime import datetime
from bson import ObjectId
from django.apps import AppConfig
import threading, time
import os

import requests
from db_conection import db

chits_collection = db['chit_groups']
users_collection = db['user']
invoices_collection = db["invoices"]


# Email API
EMAIL_API_URL = "http://192.168.167.21:5000/service/send_email"
EMAIL_HEADERS = {
    "X-API-KEY": "0898c79d9edee1eaf79e1f97718ea84da47472f70884944ba1641b58ed24796c",
    "X-CLIENT-SECRET": "gAAAAABonHWC_8L0gU4ztDHyN9fgk3FRcZ5KTc-TmJ72U4cyRCo9ATH_IUex-NrehgtsZaDxi9vl_vvpTgTKG2veDKGb07SOGeEeHxyLlSbMTw3Y7k_PVjWBT1Bqdxmakw-mhS6se6H4",
    "Content-Type": "application/json"
}

# -----------------------------
# Invoice Reminder Thread
# -----------------------------
def send_invoice_email(user_email, subject, body):
    """Send an invoice reminder email via API."""
    if not user_email:
        return False
    payload = {"from": "admin@lakshmi.com", "to": user_email, "subject": subject, "body": body, "attachment": None}
    try:
        response = requests.post(EMAIL_API_URL, json=payload, headers=EMAIL_HEADERS, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Failed to send invoice email to {user_email}: {e}")
        return False

def send_weekly_invoice_reminder():
    """Send weekly unpaid invoice reminders to users."""
    while True:
        try:
            now_time = datetime.now()
            print(f"[{now_time}] Running weekly invoice reminder...")
            unpaid_invoices = list(invoices_collection.find({"is_paid": False}))
            print(f"Found {len(unpaid_invoices)} unpaid invoices.")

            user_invoices_map = {}
            for inv in unpaid_invoices:
                user_id = str(inv["user_id"])
                user_invoices_map.setdefault(user_id, []).append(inv)

            for user_id, invoices in user_invoices_map.items():
                user = users_collection.find_one({"_id": ObjectId(user_id)})
                if not user or not user.get("email"):
                    print(f"Skipping user {user_id}: email not found.")
                    continue

                user_email = user["email"]
                user_name = user.get("name", "User")
                invoice_lines = []
                total_amount = 0

                for inv in invoices:
                    chit = chits_collection.find_one({"_id": ObjectId(inv["chit_group_id"])})
                    chit_name = chit.get("group_name") if chit else "Unknown Group"
                    month = inv.get("month", "N/A")
                    amount = inv.get("amount", 0)
                    total_amount += amount
                    invoice_lines.append(f"Chit Group: {chit_name}\nMonth: {month}\nAmount: ₹{amount}\n")
                    inv["chit_group_name"] = chit_name

                if len(invoices) >= 2:
                    invoice_lines.append(f"\nTotal Amount Due: ₹{total_amount}")

                invoice_text = "\n".join(invoice_lines)
                email_subject = f"Unpaid Invoice Reminder - {len(invoices)} Invoice(s)"
                email_body = f"Dear {user_name} ({user_email}),\n\nHere are your unpaid invoice details:\n\n{invoice_text}\n\nPlease make the payment at the earliest."

                sent = send_invoice_email(user_email, email_subject, email_body)
                print(f"Reminder sent to {user_email} ({len(invoices)} invoices)." if sent else f"Failed to send reminder to {user_email}.")
        except Exception as e:
            print(f"[{datetime.now()}] Error in weekly invoice reminder: {e}")

        time.sleep(100)  # 7 days 604800


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
        time.sleep(60)  # Every 30 seconds (adjust as needed)

class ChitgroupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CHITGROUP'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            return  # Avoid duplicate thread when using runserver
        threading.Thread(target=send_weekly_invoice_reminder, daemon=True).start()
        threading.Thread(target=run_prize_money_calculator, daemon=True).start()
        print("Invoice reminder and prize calculation threads started.")
