from flask import Flask, jsonify, request
import psycopg2

app = Flask(__name__)

# =========================
# DATABASE CONNECTION (YOUR URL)
# =========================
DATABASE_URL = "postgresql://quantedge_db_qo0e_user:ddxIeVXZ6JrfPB0dkuwMinv52MvnVOLR@dpg-d7851inkijhs73fvvvkg-a.ohio-postgres.render.com/quantedge_db_qo0e"

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# =========================
# CREATE TABLE
# =========================
cur.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    time TEXT,
    type TEXT,
    profit FLOAT,
    status TEXT
)
""")
conn.commit()

# =========================
# RECEIVE FROM BOT
# =========================
@app.route("/api/log", methods=["POST"])
def log_trade():
    data = request.json

    cur.execute(
        "INSERT INTO trades (time, type, profit, status) VALUES (%s,%s,%s,%s)",
        (
            data.get("Time"),
            data.get("Type"),
            float(data.get("Profit", 0)),
            data.get("Status")
        )
    )
    conn.commit()

    print("📡 Saved to DB:", data)

    return {"status": "saved"}

# =========================
# GET TRADES
# =========================
@app.route("/api/trades")
def trades():
    cur.execute("SELECT time, type, profit, status FROM trades ORDER BY id DESC")
    rows = cur.fetchall()

    data = []
    for r in rows:
        data.append({
            "Time": r[0],
            "Type": r[1],
            "Profit": r[2],
            "Status": r[3]
        })

    return jsonify(data)

# =========================
# STATS
# =========================
@app.route("/api/stats")
def stats():
    cur.execute("SELECT profit FROM trades WHERE status='CLOSED'")
    profits = [r[0] for r in cur.fetchall()]

    if len(profits) == 0:
        return jsonify({
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "profit": 0
        })

    wins = len([p for p in profits if p > 0])
    losses = len([p for p in profits if p <= 0])
    total = len(profits)

    return jsonify({
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": round((wins / total) * 100, 2),
        "profit": round(sum(profits), 2)
    })

# =========================
# SIMPLE UI TEST
# =========================
@app.route("/")
def home():
    return "🚀 QuantEdge Database Connected Successfully!"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)