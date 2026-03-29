from flask import Flask, request, jsonify, render_template
from flask import redirect, url_for

from googletrans import Translator
import sqlite3
import pandas as pd
import os

app = Flask(__name__)
translator = Translator()

# ---------------- Load Schemes (CSV) ----------------
def load_schemes():
    df = pd.read_csv("schemes.csv")
    df.fillna("", inplace=True)
    return df.to_dict(orient="records")

ALL_SCHEMES = load_schemes()

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        user_message TEXT,
        bot_reply TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()

def save_chat(chat_id, user, bot):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO chats (chat_id, user_message, bot_reply) VALUES (?, ?, ?)",
              (chat_id, user, bot))

    conn.commit()
    conn.close()

# ---------------- Smart Selector ----------------
def smart_selector(age, income, occupation):

    schemes = []

    try:
        age = int(age)
        income = int(income)
    except:
        return []

    if occupation.lower() == "farmer":
        schemes.append("PM Kisan Yojana")

    if income < 200000:
        schemes.append("Ayushman Bharat")

    if occupation.lower() == "student":
        schemes.append("MahaDBT Scholarship")

    if age > 60:
        schemes.append("Old Age Pension Scheme")

    if income < 100000 and occupation.lower() == "other":
        schemes.append("Ujjwala Yojana")

    return schemes

# ---------------- Dynamic Scheme Finder ----------------
def find_scheme_from_message(user_message):
    user_message = user_message.lower()

    for scheme in ALL_SCHEMES:
        name = str(scheme["Scheme Name"]).lower()
        category = str(scheme["Category"]).lower()

        if any(word in name for word in user_message.split()) or \
           any(word in category for word in user_message.split()):
            return scheme

    return None

# ---------------- Routes ----------------
# ---------------- Routes ----------------

# Login Page
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    return redirect(url_for("index"))

@app.route("/index")
def index():
    return render_template("index.html")
    
# ---------------- Eligibility (Selector) ----------------
@app.route("/eligibility", methods=["POST"])
def eligibility():

    data = request.get_json()

    age = data.get("age")
    income = data.get("income")
    occupation = data.get("occupation")
    lang = data.get("lang", "en")

    schemes_list = smart_selector(age, income, occupation)

    if not schemes_list:
        reply = "No schemes found for your profile."
    else:
        reply = "You are eligible for:\n\n"

    for s in schemes_list:
        reply += f"• {s}\n"

    reply += "<br>Steps:<br>1. Visit official website<br>2. Register<br>3. Submit documents"

    reply = translate_text(reply, lang)

    return jsonify({"reply": reply})

# ---------------- Chatbot ----------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data["message"]
    chat_id = data["chat_id"]
    lang = data.get("lang", "en")

    user_message_en = translate_text(user_message, "en").lower()

    # Redirect to selector
    if ("eligible" in user_message_en or
        "eligibility" in user_message_en or
        "scheme suggest" in user_message_en):

        reply = translate_text(
            "Go to 'Scheme Selector' and enter your details.", lang
        )

        save_chat(chat_id, user_message, reply)
        return jsonify({"reply": reply})

    # 🔥 Dynamic Scheme Search
    scheme = find_scheme_from_message(user_message_en)

    if scheme:
        name = scheme["Scheme Name"]
        benefits = scheme["Benefits"]
        eligibility_text = scheme["Eligibility"]
        link = scheme["Link"]

        reply = f"📌 {name}\n💰 {benefits}\n\nEligibility:\n{eligibility_text}"
        reply = translate_text(reply, lang)

    else:
        reply = translate_text(
            "Try asking about farming, education, health, or any scheme name.", lang
        )
        link = None

    save_chat(chat_id, user_message, reply)

    return jsonify({"reply": reply, "link": link})

# ---------------- Chat List ----------------
@app.route("/all_chats")
def all_chats():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
              
    SELECT chat_id, MIN(id)
    FROM chats
    GROUP BY chat_id
    ORDER BY MIN(id) DESC
    """)

    chat_ids = c.fetchall()

    result = []

    for chat_id, first_id in chat_ids:
        c.execute("SELECT user_message FROM chats WHERE id=?", (first_id,))
        first_msg = c.fetchone()[0]

        if len(first_msg) > 25:
            first_msg = first_msg[:25] + "..."

        result.append((chat_id, first_msg))

    conn.close()
    return jsonify(result)

# ---------------- Load Chat ----------------
@app.route("/get_chat/<chat_id>")
def get_chat(chat_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT user_message, bot_reply FROM chats WHERE chat_id=?", (chat_id,))
    data = c.fetchall()

    conn.close()
    return jsonify(data)

# ---------------- Delete ----------------
@app.route("/delete_chat/<chat_id>")
def delete_chat(chat_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM chats WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "deleted"})

# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
