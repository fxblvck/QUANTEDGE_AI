import requests

URL = ("https://quantedge-dashboard.onrender.com/api/log"

data = {
    "Time" = "TEST"
    "Type" = "BUY"
    "Profit" = 50,
    "Status" = "CLOSED"
}

try:
    res = requests.post(URL, json+data)
    print("Status:", res.status_code)
    print("Response:", res.test)
except Exception as e:
    print("Error:", e)