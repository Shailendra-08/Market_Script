# Open Interest Analysis
# 📊 PCR: {analysis['oi']['pcr']:.2f}
# 📈 CE OI: {analysis['oi']['total_ce_oi']:,}
# 📉 PE OI: {analysis['oi']['total_pe_oi']:,}

# Volatility Analysis
# 📈 Avg CE IV: {analysis['iv']['avg_ce_iv']}%
# 📉 Avg PE IV: {analysis['iv']['avg_pe_iv']}%
# 🔄 IV Skew: {analysis['iv']['iv_skew']:.2f}
# 🎚️ IV Rank: {analysis['iv']['iv_rank']:.1f}%

# Volume Analysis
# 📈 CE Volume: {analysis['volume']['ce_vol']:,}
# 📉 PE Volume: {analysis['volume']['pe_vol']:,}
# 🔄 Volume PCR: {analysis['volume']['volume_pcr']:.2f}

# 📢 Signals
# {' '.join(f'• {s}' for s in analysis['signals'])}



import requests
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "7596750085:AAG9tJ_Mtor6g8FqHjXZWjHG3xhLyotFJmc"

class OptionsAnalysisBot:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.session = requests.Session()
        self.session.get("https://www.nseindia.com", headers=self.headers)
        self.historical_iv = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📊 Options Analysis Bot\n\n"
            "Commands:\n"
            "/analyze [SYMBOL] - Full options analysis\n"
            "/help - Show help\n"
            "/example - Sample analysis format",
            parse_mode='Markdown'
        )

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            symbol = context.args[0].upper()
            await update.message.reply_text(f"🔍 Analyzing {symbol}...")
            
            data = self._fetch_data(symbol)
            if not data:
                await update.message.reply_text("❌ Data fetch failed")
                return

            analysis = self._full_analysis(data, symbol)
            response = self._format_response(analysis)
            
            keyboard = [
                [InlineKeyboardButton("📈 Chart", callback_data=f"chart_{symbol}"),
                 InlineKeyboardButton("📉 IV Chart", callback_data=f"iv_{symbol}")]
            ]
            
            await update.message.reply_markdown(
                response,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except IndexError:
            await update.message.reply_text("⚠️ Usage: /analyze RELIANCE")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    def _fetch_data(self, symbol):
        try:
            url = f'https://www.nseindia.com/api/option-chain-equities?symbol={symbol}'
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    def _full_analysis(self, data, symbol):
        records = data['records']
        spot_price = records['underlyingValue']
        expiry_dates = sorted(list({rec['CE']['expiryDate'] for rec in records['data'] if 'CE' in rec}))
        
        return {
            'symbol': symbol,
            'spot': spot_price,
            'expiry': expiry_dates[0],
            'oi': self._oi_analysis(records['data'], expiry_dates[0]),
            'iv': self._iv_analysis(records['data'], expiry_dates[0]),
            'volume': self._volume_analysis(records['data'], expiry_dates[0]),
            'max_pain': self._calculate_max_pain(records['data'], expiry_dates[0]),
            'signals': self._generate_signals(spot_price)
        }

    def _oi_analysis(self, data, expiry):
        ce_oi = [x['CE']['openInterest'] for x in data if 'CE' in x and x['CE']['expiryDate'] == expiry]
        pe_oi = [x['PE']['openInterest'] for x in data if 'PE' in x and x['PE']['expiryDate'] == expiry]
        
        return {
            'total_ce_oi': sum(ce_oi),
            'total_pe_oi': sum(pe_oi),
            'pcr': round(sum(pe_oi)/sum(ce_oi), 2) if ce_oi else 0,
            'max_ce_oi': max(ce_oi, default=0),
            'max_pe_oi': max(pe_oi, default=0)
        }

    def _iv_analysis(self, data, expiry):
        ce_iv = [x['CE']['impliedVolatility'] for x in data if 'CE' in x and x['CE']['expiryDate'] == expiry]
        pe_iv = [x['PE']['impliedVolatility'] for x in data if 'PE' in x and x['PE']['expiryDate'] == expiry]
        
        return {
            'avg_ce_iv': round(sum(ce_iv)/len(ce_iv), 2) if ce_iv else 0,
            'avg_pe_iv': round(sum(pe_iv)/len(pe_iv), 2) if pe_iv else 0,
            'iv_skew': round((sum(pe_iv)/len(pe_iv)) - (sum(ce_iv)/len(ce_iv)), 2),
            'iv_rank': self._iv_rank(ce_iv + pe_iv)
        }

    def _volume_analysis(self, data, expiry):
        ce_vol = [x['CE']['totalTradedVolume'] for x in data if 'CE' in x and x['CE']['expiryDate'] == expiry]
        pe_vol = [x['PE']['totalTradedVolume'] for x in data if 'PE' in x and x['PE']['expiryDate'] == expiry]
        
        return {
            'volume_pcr': round(sum(pe_vol)/sum(ce_vol), 2) if ce_vol else 0,
            'ce_vol': sum(ce_vol),
            'pe_vol': sum(pe_vol)
        }

    def _calculate_max_pain(self, data, expiry):
        strikes = sorted(list(set(x['CE']['strikePrice'] for x in data if 'CE' in x)))
        pain = []
        
        for strike in strikes:
            ce_pain = sum(x['CE']['openInterest'] * (strike - x['CE']['strikePrice']) for x in data if 'CE' in x and x['CE']['strikePrice'] < strike)
            pe_pain = sum(x['PE']['openInterest'] * (x['PE']['strikePrice'] - strike) for x in data if 'PE' in x and x['PE']['strikePrice'] > strike)
            pain.append(ce_pain + pe_pain)
        
        return strikes[pain.index(min(pain))]

    def _iv_rank(self, current_iv):
        return min(100, max(0, (pd.Series(current_iv).mean() - 20) / (40 - 20) * 100))

    def _generate_signals(self, spot_price):
        signals = []
        
        if self.historical_iv and 'iv' in self.historical_iv:
            if self.historical_iv['iv']['iv_rank'] > 70:
                signals.append("High IV Rank - Sell Options")
        if self.historical_iv and 'oi' in self.historical_iv:
            if self.historical_iv['oi']['pcr'] > 1.5:
                signals.append("High PCR - Bullish Signal")
        if spot_price < self.historical_iv.get('max_pain', float('inf')):
            signals.append("Below Max Pain - Bearish Bias")
            
        return signals or ["Neutral Market"]

    def _format_response(self, analysis):
        return f"""
📈 {analysis['symbol']} Options Analysis 📉

Price Analysis
🔼 Spot Price: ₹{analysis['spot']:.2f}
📉 Max Pain: ₹{analysis['max_pain']}

Open Interest Analysis
📊 PCR: {analysis['oi']['pcr']:.2f}
📈 CE OI: {analysis['oi']['total_ce_oi']:,}
📉 PE OI: {analysis['oi']['total_pe_oi']:,}

Volatility Analysis
📈 Avg CE IV: {analysis['iv']['avg_ce_iv']}%
📉 Avg PE IV: {analysis['iv']['avg_pe_iv']}%
🔄 IV Skew: {analysis['iv']['iv_skew']:.2f}
🎚️ IV Rank: {analysis['iv']['iv_rank']:.1f}%

Volume Analysis
📈 CE Volume: {analysis['volume']['ce_vol']:,}
📉 PE Volume: {analysis['volume']['pe_vol']:,}
🔄 Volume PCR: {analysis['volume']['volume_pcr']:.2f}

📢 Signals
{' '.join(f'• {s}' for s in analysis['signals'])}




        """

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        print(f"⚠️ Error: {context.error}")

def main():
    bot = OptionsAnalysisBot()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("analyze", bot.analyze))
    application.add_error_handler(bot.error_handler)

    print("🤖 Bot running...")
    application.run_polling()

if __name__ == "__main__":
    main()
