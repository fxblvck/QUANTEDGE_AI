import MetaTrader5 as mt5

print("🚀 Starting MT5 test...")

connected = mt5.initialize()

print("Connection status:", connected)

if connected:
    print("✅ Connected to MT5")
else:
    print("❌ Failed to connect")
    print("Error code:", mt5.last_error())