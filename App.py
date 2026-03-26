from flask import Flask, request, jsonify, render_template
from googletrans import Translator
import sqlite3

app = Flask(__name__)
translator = Translator()

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

# ---------------- Schemes ----------------
schemes = {
    "pm kisan": {
        "info": "PM Kisan Scheme: In this Farmers get ₹6000 per year.",
        "link": "https://pmkisan.gov.in/",
        "eligibility": "\n1)You must be a farmer.\n2)You should have agricultural land."
    },
    "ayushman bharat": {
        "info": "Ayushman Bharat : In this citizens can get free health insurance up to ₹5 lakh.",
        "link": "https://pmjay.gov.in/",
        "eligibility": "Families listed in SECC database are eligible."
    },
    "ujjwala": {
        "info": "Ujjwala Yojna : Free LPG connection for poor families.",
        "link": "https://www.pmuy.gov.in/",
        "eligibility": "Women from BPL households can apply."
    },
    "taem": {
        "info": "Renuka (Leader),Harsha(representator),Prathamesh(frontend Developer),Amar(Backend developer)",
        "link": "https://www.pmuy.gov.in/",
        "eligibility": ""
    }
}

# ---------------- Routes ----------------
@app.route("/")
def home():
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
        reply = "You are eligible for:<br><br>"

    for s in schemes_list:
        reply += f"• {s}"

    reply += "<br><br>Steps to apply:</b><br>1. Visit official website<br>2. Register<br>3. Submit documents"

    # Translate output
    try:
        reply = translator.translate(reply, dest=lang).text
    except:
        pass

    return jsonify({"reply": reply})

# ---------------- Chatbot ----------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data["message"]
    chat_id = data["chat_id"]
    lang = data.get("lang", "en")

    try:
        user_message_en = translator.translate(user_message, dest="en").text.lower()
    except:
        user_message_en = user_message.lower()

    user_message_lower = user_message.lower()

    # 🔥 Redirect to selector if needed
    if ("eligible" in user_message_en or "eligibility" in user_message_en or
        "scheme suggest" in user_message_en or "yojana batao" in user_message_lower):

        reply = "Please go to 'Scheme Selector' tab and enter your details."

        try:
            reply = translator.translate(reply, dest=lang).text
        except:
            pass

        save_chat(chat_id, user_message, reply)
        return jsonify({"reply": reply})

    scheme = None

    if ("kisan" in user_message_en or "pm" in user_message_en or
        "किसान" in user_message_lower):
        scheme = "pm kisan"

    elif ("ayushman" in user_message_en or "bharat" in user_message_en or
          "health" in user_message_en or "insurance" in user_message_en or
          "आयुष्मान" in user_message_lower):
        scheme = "ayushman bharat"

    elif ("ujjwala" in user_message_en or "gas" in user_message_en or
          "उज्वला" in user_message_lower or "उज्जवला" in user_message_lower):
        scheme = "ujjwala"

    elif ("team" in user_message_en or "" in user_message_en or
          "amar" in user_message_lower or "उज्जवला" in user_message_lower):
        scheme = "amar"

    if scheme:

        text = schemes[scheme]["info"]
        eligibility_text = schemes[scheme]["eligibility"]
        link = schemes[scheme]["link"]

        try:
            translated_text = translator.translate(text, dest=lang).text
            translated_eligibility = translator.translate(eligibility_text, dest=lang).text
            label = translator.translate("Eligibility", dest=lang).text
        except:
            translated_text = text
            translated_eligibility = eligibility_text
            label = "Eligibility"

        reply = translated_text + "\n" + label + ": " + translated_eligibility

    else:
        reply = "Ask about schemes like PM Kisan, Ayushman Bharat, Ujjwala."
        link = None

    save_chat(chat_id, user_message, reply)

    return jsonify({"reply": reply, "link": link if scheme else None})

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
    app.run(debug=True)