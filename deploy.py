import requests
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# 🔑 Replace this with your actual Telegram Bot Token
TOKEN = "7596750085:AAEH-sH5SFxJZMxx8aAEMqRbQI47I9a-68w"

class OptionChainAnalyzer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://www.nseindia.com"
        self._establish_session()

    def _establish_session(self):
        """Initialize session with retries"""
        for _ in range(5):  # Retry 5 times
            try:
                response = self.session.get(self.base_url, timeout=10)
                if response.status_code == 200:
                    return
            except requests.exceptions.RequestException:
                time.sleep(2)
        raise ConnectionError("Could not establish NSE session. Try using a proxy or different network.")

    def get_nifty_stocks(self):
        """Fetch all NIFTY 50 stock symbols dynamically"""
        try:
            url = f"{self.base_url}/api/equity-stockIndices?index=NIFTY%2050"
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []

            data = response.json()
            return [stock['symbol'] for stock in data['data']]
        except Exception as e:
            print("Error fetching NIFTY stocks:", e)
            return []

    def analyze_symbol(self, symbol):
        """Analyze a given stock"""
        try:
            url = f"{self.base_url}/api/option-chain-equities?symbol={symbol}"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                return f"❌ Error fetching {symbol}"

            data = response.json()
            if not data['records']['data']:
                return f"⚠️ No data for {symbol}"

            current_price = data['records']['underlyingValue']

            # PCR Calculation
            call_oi = sum(rec['CE']['openInterest'] for rec in data['records']['data'] if 'CE' in rec)
            put_oi = sum(rec['PE']['openInterest'] for rec in data['records']['data'] if 'PE' in rec)
            pcr_oi = put_oi / call_oi if call_oi != 0 else 0

            # Signal Determination
            signal = "Neutral"
            if pcr_oi > 1.5:
                signal = "Strong Buy"
            elif pcr_oi < 0.7:
                signal = "Strong Sell"

            # Support & Resistance Calculation
            support_1 = min(rec["strikePrice"] for rec in data["records"]["data"])
            resistance_1 = max(rec["strikePrice"] for rec in data["records"]["data"])
            target = resistance_1
            stop_loss = support_1
            recommendation = "Buy near Support" if signal == "Strong Buy" else "Hold"

            return (
                f"📊 **{symbol}**\n"
                f"💰 Current Price: {current_price}\n"
                f"🔽 Support 1: {support_1}\n"
                f"🔼 Resistance 1: {resistance_1}\n"
                f"📈 PCR OI: {round(pcr_oi, 2)}\n"
                f"📢 Signal: {signal}\n"
                f"✅ Recommendation: {recommendation}\n"
                f"🎯 Target: {target}\n"
                f"🛑 Stop Loss: {stop_loss}\n\n"
            )

        except Exception as e:
            print("Error analyzing symbol:", e)
            return f"⚠️ Error analyzing {symbol}"

# 🔍 Initialize the analyzer
analyzer = OptionChainAnalyzer()

async def start(update: Update, context):
    await update.message.reply_text("Hello! Use /allstocks to get NIFTY stock analysis and for single stock you can write the name eg: RELIANCE.")

async def analyze(update: Update, context):
    symbol = update.message.text.upper()
    result = analyzer.analyze_symbol(symbol)
    await update.message.reply_text(result)

async def analyze_all(update: Update, context):
    """Fetch all NIFTY stocks dynamically and analyze them in chunks"""
    stock_list = analyzer.get_nifty_stocks()

    if not stock_list:
        await update.message.reply_text("⚠️ Error fetching NIFTY stocks.")
        return

    results = []
    for stock in stock_list:
        result = analyzer.analyze_symbol(stock)
        if result:
            results.append(result)

    message = ""
    for result in results:
        if len(message) + len(result) > 4000:  # Check if adding new result exceeds 4096 chars
            await update.message.reply_text(message)  # Send previous chunk
            message = ""  # Reset message
        message += result + "\n"  # Add new result

    if message:  # Send any remaining data
        await update.message.reply_text(message)


# 🚀 Start the bot
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("allstocks", analyze_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
