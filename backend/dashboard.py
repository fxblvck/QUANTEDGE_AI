from flask import Flask, jsonify, request, render_template_string
import psycopg2

app = Flask(__name__)

# =========================
# DATABASE
# =========================
DATABASE_URL = "postgresql://quantedge_db_qo0e_user:ddxIeVXZ6JrfPB0dkuwMinv52MvnVOLR@dpg-d7851inkijhs73fvvvkg-a.ohio-postgres.render.com/quantedge_db_qo0e"

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

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
# RECEIVE DATA
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

    return {"status": "saved"}

# =========================
# GET TRADES
# =========================
@app.route("/api/trades")
def trades():
    cur.execute("SELECT time, type, profit, status FROM trades ORDER BY id DESC")
    rows = cur.fetchall()

    return jsonify([
        {"Time": r[0], "Type": r[1], "Profit": r[2], "Status": r[3]}
        for r in rows
    ])

# =========================
# STATS
# =========================
def get_stats():
    cur.execute("SELECT profit FROM trades WHERE status='CLOSED'")
    profits = [r[0] for r in cur.fetchall()]

    if len(profits) == 0:
        return 0,0,0,0,0

    wins = len([p for p in profits if p > 0])
    losses = len([p for p in profits if p <= 0])
    total = len(profits)
    winrate = round((wins / total) * 100, 2)
    profit = round(sum(profits), 2)

    return total, wins, losses, winrate, profit

# =========================
# UI DASHBOARD
# =========================
@app.route("/")
def home():
    total, wins, losses, winrate, profit = get_stats()

    html = f"""
    <html>
    <head>
        <title>QuantEdge Dashboard</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body {{
                background:#0f172a;
                color:white;
                font-family:Arial;
                text-align:center;
            }}
            .card {{
                background:#1e293b;
                padding:20px;
                margin:10px;
                border-radius:10px;
                display:inline-block;
                width:200px;
            }}
            table {{
                margin:auto;
                margin-top:20px;
                border-collapse:collapse;
                width:80%;
            }}
            th, td {{
                padding:10px;
                border:1px solid #334155;
            }}
        </style>
    </head>

    <body>

        <h1>🚀 QuantEdge AI Dashboard</h1>

        <div class="card">Trades<br><h2>{total}</h2></div>
        <div class="card">Wins<br><h2>{wins}</h2></div>
        <div class="card">Losses<br><h2>{losses}</h2></div>
        <div class="card">Winrate<br><h2>{winrate}%</h2></div>
        <div class="card">Profit<br><h2>${profit}</h2></div>

        <h2>Recent Trades</h2>

        <table>
            <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Profit</th>
                <th>Status</th>
            </tr>
    """

    cur.execute("SELECT time, type, profit, status FROM trades ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()

    for r in rows:
        html += f"""
        <tr>
            <td>{r[0]}</td>
            <td>{r[1]}</td>
            <td>{r[2]}</td>
            <td>{r[3]}</td>
        </tr>
        """

    html += "</table></body></html>"

    return html

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)