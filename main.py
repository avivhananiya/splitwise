import streamlit as st
from streamlit_gsheets import GSheetsConnection
from logic import Expense, TripGroup
import pandas as pd

# 1. הגדרת דף - תמיד הפקודה הראשונה!
st.set_page_config(page_title="Japan Trip Expenses", layout="centered")

# 2. חיבור ל-Google Sheets (משתמש ב-Secrets שהגדרנו)
conn = st.connection("gsheets", type=GSheetsConnection)


# 3. טעינת נתונים מהענן
def fetch_data():
    df = conn.read()
    expenses = []
    if not df.empty:
        for _, row in df.iterrows():
            # יצירת אובייקטים מהשורה בטבלה
            p_list = row['participants'].split(", ")
            expenses.append(Expense(
                row['description'], row['amount_jpy'], row['payer'],
                p_list, date=row['date'], rate=row['rate_at_time']
            ))
    return expenses


# 4. אתחול האפליקציה
all_expenses = fetch_data()
trip = TripGroup(["אביב", "יוסי", "דנה"], expenses_list=all_expenses)

st.title("🇯🇵 Splitwise יפן")

# --- ממשק הוספת הוצאה ---
with st.expander("➕ הוסף הוצאה חדשה"):
    with st.form("new_expense"):
        desc = st.text_input("תיאור")
        amount = st.number_input("סכום (JPY)", min_value=0)
        payer = st.selectbox("מי שילם?", trip.members)
        who_participated = st.multiselect("עבור מי?", trip.members, default=trip.members)

        if st.form_submit_button("שמור"):
            # יצירת הוצאה חדשה (מחשב שער חליפין אוטומטי)
            new_exp = Expense(desc, amount, payer, who_participated)

            # שמירה חזרה לגוגל שיטס
            df_existing = conn.read()
            new_row = pd.DataFrame([{
                "date": new_exp.date,
                "description": new_exp.description,
                "amount_jpy": new_exp.amount_jpy,
                "payer": new_exp.payer,
                "participants": ", ".join(new_exp.participants),
                "rate_at_time": new_exp.rate_at_time,
                "amount_ils": new_exp.amount_ils
            }])
            updated_df = pd.concat([df_existing, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("נשמר בהצלחה!")
            st.rerun()  # רענון הדף לעדכון הנתונים

# --- הצגת מאזן חובות ---
st.subheader("💰 מצב חשבון")
balances = trip.calculate_balances()
for name, bal in balances.items():
    color = "green" if bal >= 0 else "red"
    st.markdown(f"**{name}**: :{color}[{bal} ₪]")