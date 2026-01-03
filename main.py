import streamlit as st
from streamlit_gsheets import GSheetsConnection
from logic import Expense, TripGroup
import pandas as pd

# 1. הגדרת דף - תמיד הפקודה הראשונה!
st.set_page_config(page_title="Japan Trip Expenses", layout="centered", page_icon="🇯🇵")

# 2. חיבור ל-Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


# 3. פונקציה לטעינת נתונים מהגיליון
def fetch_data():
    try:
        df = conn.read(ttl=0)
        expenses = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                p_list = row['participants'].split(", ")
                expenses.append(Expense(
                    row['description'], row['amount_jpy'], row['payer'],
                    p_list, date=row['date'], rate=row['rate_at_time']
                ))
        return expenses
    except Exception as e:
        st.error(f"שגיאה במשיכת נתונים: {e}")
        return []


# 4. פונקציה לחישוב סגירת חובות (מי מעביר למי)
def calculate_settlements(balances):
    debtors = [[name, abs(bal)] for name, bal in balances.items() if bal < 0]
    creditors = [[name, bal] for name, bal in balances.items() if bal > 0]
    settlements = []

    while debtors and creditors:
        debtor, creditor = debtors[0], creditors[0]
        transfer = min(debtor[1], creditor[1])
        if transfer > 0.01:
            settlements.append(f"**{debtor[0]}** מעביר ל-**{creditor[0]}**: {transfer:,.2f} ₪")

        debtor[1] -= transfer
        creditor[1] -= transfer

        if debtor[1] < 0.01: debtors.pop(0)
        if creditor[1] < 0.01: creditors.pop(0)

    return settlements


# --- פונקציית Pop-up (Dialog) להיסטוריה ---
@st.dialog("📜 היסטוריית הוצאות מלאה")
def show_history_dialog():
    if st.session_state.all_expenses:
        history_df = pd.DataFrame([
            {"#": i + 1, "תיאור": e.description, "₪": f"{e.amount_ils:,.2f}", "שילם": e.payer, "תאריך": e.date}
            for i, e in enumerate(st.session_state.all_expenses)
        ])
        # הצגת הטבלה מהסוף להתחלה (הכי חדש למעלה) עם רוחב מותאם ל-2026
        st.dataframe(history_df.iloc[::-1], width='stretch', hide_index=True)
    else:
        st.info("עדיין אין הוצאות רשומות בטיול.")


# 5. ניהול ה-State והגדרת המשתתפים
if 'all_expenses' not in st.session_state:
    st.session_state.all_expenses = fetch_data()

# עדכון השמות כאן: אביב, לידור ועומרי
participants = ["אביב", "לידור", "עומרי"]
trip = TripGroup(participants, expenses_list=st.session_state.all_expenses)

st.title("🇯🇵 Splitwise יפן")

# כפתור שפותח את חלון ההיסטוריה
if st.button("📜 לצפייה בהיסטוריית הוצאות"):
    show_history_dialog()

# --- ממשק הוספת הוצאה ---
with st.expander("➕ הוסף הוצאה חדשה"):
    with st.form("new_expense", clear_on_submit=True):
        desc = st.text_input("תיאור ההוצאה")
        amount = st.number_input("סכום ביאנים (JPY)", min_value=0, step=100)
        payer = st.selectbox("מי שילם?", trip.members)
        who_participated = st.multiselect("עבור מי?", trip.members, default=trip.members)

        if st.form_submit_button("שמור"):
            if desc and amount > 0 and who_participated:
                new_exp = Expense(desc, amount, payer, who_participated)
                st.session_state.all_expenses.append(new_exp)

                # שמירה לגוגל
                df_existing = conn.read(ttl=0)
                new_row = pd.DataFrame([{
                    "date": new_exp.date, "description": new_exp.description,
                    "amount_jpy": new_exp.amount_jpy, "payer": new_exp.payer,
                    "participants": ", ".join(new_exp.participants),
                    "rate_at_time": new_exp.rate_at_time, "amount_ils": new_exp.amount_ils
                }])
                updated_df = pd.concat([df_existing, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("ההוצאה נשמרה בהצלחה!")
                st.rerun()
            else:
                st.warning("נא למלא את כל הפרטים (תיאור, סכום ומשתתפים)")

# --- ממשק עריכת הוצאה ---
with st.expander("✏️ עריכת הוצאה קיימת"):
    if st.session_state.all_expenses:
        exp_options = [f"{i + 1}: {e.description} ({e.amount_jpy}¥)" for i, e in
                       enumerate(st.session_state.all_expenses)]
        selected_edit = st.selectbox("בחר הוצאה לעריכה:", exp_options)
        edit_idx = int(selected_edit.split(":")[0]) - 1
        current_exp = st.session_state.all_expenses[edit_idx]

        with st.form("edit_form"):
            new_desc = st.text_input("תיאור חדש", value=current_exp.description)
            new_amount = st.number_input("סכום חדש (JPY)", value=int(current_exp.amount_jpy), min_value=1)
            new_payer = st.selectbox("מי שילם?", trip.members, index=trip.members.index(current_exp.payer))
            new_who = st.multiselect("עבור מי?", trip.members, default=current_exp.participants)

            if st.form_submit_button("עדכן שינויים"):
                updated_exp = Expense(new_desc, new_amount, new_payer, new_who)
                st.session_state.all_expenses[edit_idx] = updated_exp

                df_to_edit = conn.read(ttl=0)
                df_to_edit.iloc[edit_idx] = [
                    updated_exp.date, updated_exp.description, updated_exp.amount_jpy,
                    updated_exp.payer, ", ".join(updated_exp.participants),
                    updated_exp.rate_at_time, updated_exp.amount_ils
                ]
                conn.update(data=df_to_edit)
                st.success("המידע עודכן!")
                st.rerun()

# --- ממשק מחיקת הוצאה ---
with st.expander("🗑️ מחיקת הוצאה"):
    if st.session_state.all_expenses:
        del_options = [f"{i + 1}: {e.description}" for i, e in enumerate(st.session_state.all_expenses)]
        selected_del = st.selectbox("בחר הוצאה להסרה:", del_options)
        del_idx = int(selected_del.split(":")[0]) - 1

        if st.button("מחק לצמיתות", type="primary"):
            st.session_state.all_expenses.pop(del_idx)
            df_to_del = conn.read(ttl=0)
            df_to_del = df_to_del.drop(del_idx).reset_index(drop=True)
            conn.update(data=df_to_del)
            st.warning(f"הוצאה מס' {del_idx + 1} הוסרה.")
            st.rerun()

# --- תצוגת מאזן וחובות ---
st.divider()
balances = trip.calculate_balances()

col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 מאזן כללי")
    for name, bal in balances.items():
        color = "green" if bal >= 0 else "red"
        st.markdown(f"**{name}**: :{color}[{bal:,.2f} ₪]")

with col2:
    st.subheader("🤝 סגירת חובות")
    settlements = calculate_settlements(balances)
    if not settlements:
        st.write("כולם מאוזנים! 🎉")
    for s in settlements:
        st.info(s)