import requests
from datetime import datetime

class CurrencyService:
    @staticmethod
    def get_jpy_to_ils_rate():
        try:
            url = "https://api.exchangerate-api.com/v4/latest/JPY"
            response = requests.get(url)
            return response.json()['rates']['ILS']
        except:
            return 0.024 # Fallback

class Expense:
    def __init__(self, description, amount_jpy, payer, participants, date=None, rate=None):
        self.description = description
        self.amount_jpy = amount_jpy
        self.payer = payer
        self.participants = participants
        self.date = date if date else datetime.now().strftime("%Y-%m-%d %H:%M")
        self.rate_at_time = rate if rate else CurrencyService.get_jpy_to_ils_rate()
        self.amount_ils = round(self.amount_jpy * self.rate_at_time, 2)

class TripGroup:
    def __init__(self, members, expenses_list=None):
        self.members = members
        # אנחנו מקבלים רשימת הוצאות מוכנה (מה-DB) ולא קוראים לקובץ JSON
        self.expenses = expenses_list if expenses_list else []

    def calculate_balances(self):
        balances = {member: 0.0 for member in self.members}
        for exp in self.expenses:
            share = exp.amount_ils / len(exp.participants)
            balances[exp.payer] += exp.amount_ils
            for p in exp.participants:
                balances[p] -= share
        return {k: round(v, 2) for k, v in balances.items()}