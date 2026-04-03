from flask import Flask, jsonify, request
import pandas as pd
import os
import subprocess

app = Flask(__name__)

LOG_FILE = "trade_log.csv"
bot_process = None  # will hold bot process

# =========================
# LOAD DATA
# =========================
def load_data():
    if not os.path.exists(LOG_FILE):
        return None
    return pd.read_csv(LOG_FILE)

# =========================
# STATS API
# =========================
@app.route("/api/stats")
def stats():
    df = load_data()

    if df is None:
        return jsonify({"trades":0,"wins":0,"losses":0,"winrate":0,"profit":0})

    closed = df[df["Status"] == "CLOSED"]

    if len(closed) == 0:
        return jsonify({"trades":0,"wins":0,"losses":0,"winrate":0,"profit":0})

    total = len(closed)
    wins = len(closed[closed["Profit"] > 0])
    losses = len(closed[closed["Profit"] <= 0])
    profit = closed["Profit"].sum()
    winrate = (wins / total) * 100

    return jsonify({
        "trades": total,
        "wins": wins,
        "losses": losses,
        "winrate": round(winrate,2),
        "profit": round(profit,2)
    })

# =========================
# TRADES API
# =========================
@app.route("/api/trades")
def trades():
    df = load_data()
    if df is None:
        return jsonify([])
    return df.to_dict(orient="records")

# =========================
# START BOT
# =========================
@app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_process

    if bot_process is None:
        bot_process = subprocess.Popen(["python", "backend/mt5_bot.py"])
        return jsonify({"status":"Bot started"})
    else:
        return jsonify({"status":"Bot already running"})

# =========================
# STOP BOT
# =========================
@app.route("/api/stop", methods=["POST"])
def stop_bot():
    global bot_process

    if bot_process:
        bot_process.terminate()
        bot_process = None
        return jsonify({"status":"Bot stopped"})
    else:
        return jsonify({"status":"Bot not running"})

# =========================
# DASHBOARD UI
# =========================
@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>QuantEdge Pro</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <style>
            body {
                font-family: Arial;
                background:#0d0d0d;
                color:#fff;
                text-align:center;
            }

            h1 { color:#00ffcc; }

            .container {
                display:grid;
                grid-template-columns: repeat(2, 1fr);
                gap:20px;
                padding:20px;
            }

            .card {
                background:#1a1a1a;
                padding:20px;
                border-radius:10px;
            }

            button {
                padding:10px 20px;
                margin:10px;
                border:none;
                border-radius:5px;
                cursor:pointer;
            }

            .start { background:green; color:white; }
            .stop { background:red; color:white; }

            table {
                width:100%;
                border-collapse: collapse;
            }

            th, td {
                padding:10px;
                border-bottom:1px solid #333;
            }
        </style>
    </head>

    <body>
        <h1>🚀 QuantEdge Pro Dashboard</h1>

        <button class="start" onclick="startBot()">Start Bot</button>
        <button class="stop" onclick="stopBot()">Stop Bot</button>

        <div class="container">

            <div class="card">
                <h2>Performance</h2>
                <p id="stats">Loading...</p>
            </div>

            <div class="card">
                <h2>Equity Curve</h2>
                <canvas id="chart"></canvas>
            </div>

            <div class="card" style="grid-column: span 2;">
                <h2>Trade History</h2>
                <table id="table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Profit</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>

        </div>

        <script>
            let chart;

            async function startBot(){
                await fetch('/api/start',{method:'POST'});
                alert("Bot Started");
            }

            async function stopBot(){
                await fetch('/api/stop',{method:'POST'});
                alert("Bot Stopped");
            }

            async function loadStats(){
                let res = await fetch('/api/stats');
                let data = await res.json();

                document.getElementById('stats').innerHTML =
                    "Trades: "+data.trades+"<br>"+
                    "Wins: "+data.wins+"<br>"+
                    "Losses: "+data.losses+"<br>"+
                    "Winrate: "+data.winrate+"%<br>"+
                    "Profit: $"+data.profit;
            }

            async function loadTrades(){
                let res = await fetch('/api/trades');
                let data = await res.json();

                let tbody = document.querySelector("#table tbody");
                tbody.innerHTML = "";

                let equity = 0;
                let equityData = [];

                data.forEach(trade=>{
                    let row = `<tr>
                        <td>${trade.Time}</td>
                        <td>${trade.Type}</td>
                        <td>${trade.Profit}</td>
                        <td>${trade.Status}</td>
                    </tr>`;

                    tbody.innerHTML += row;

                    if(trade.Status==="CLOSED"){
                        equity += parseFloat(trade.Profit || 0);
                        equityData.push(equity);
                    }
                });

                drawChart(equityData);
            }

            function drawChart(data){
                let ctx = document.getElementById('chart');

                if(chart) chart.destroy();

                chart = new Chart(ctx,{
                    type:'line',
                    data:{
                        labels:data.map((_,i)=>i+1),
                        datasets:[{
                            label:'Equity',
                            data:data,
                            borderColor:'#00ffcc'
                        }]
                    }
                });
            }

            async function update(){
                await loadStats();
                await loadTrades();
            }

            setInterval(update,3000);
            update();
        </script>

    </body>
    </html>
    """

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(debug=True)