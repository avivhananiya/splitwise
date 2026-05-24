from datetime import datetime

class Expense:
    def __init__(self, description, amount_krw, payer, participants, date=None):
        self.description = description
        self.amount_krw = amount_krw
        self.payer = payer
        self.participants = participants
        self.date = date if date else datetime.now().strftime("%Y-%m-%d %H:%M")
        # הסרנו לחלוטין את המרות המטבע (rate ואת amount_ils)

class TripGroup:
    def __init__(self, members, expenses_list=None):
        self.members = members
        # אנחנו מקבלים רשימת הוצאות מוכנה (מה-DB) ולא קוראים לקובץ JSON
        self.expenses = expenses_list if expenses_list else []

    def calculate_balances(self):
        balances = {member: 0.0 for member in self.members}
        for exp in self.expenses:
            # החישוב עכשיו מתבצע ישירות על amount_krw
            share = exp.amount_krw / len(exp.participants)
            balances[exp.payer] += exp.amount_krw
            for p in exp.participants:
                balances[p] -= share
                
        # מחזיר את המאזן כשהוא מעוגל למספר שלם (כי אין חלקי וון)
        return {k: round(v) for k, v in balances.items()}
        
