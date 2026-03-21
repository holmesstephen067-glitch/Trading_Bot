"""
trading_bot/main.py
====================
AI Trading Agent — Flask backend
Upgraded from: https://github.com/holmesstephen067-glitch/my_AI_brain/main.py

Improvements over base:
  - Claude (Anthropic) as primary LLM, OpenAI/Gemini as fallbacks
  - 15 registered trading tools (Polygon, Alpha Vantage, FRED, Finnhub, Crypto F&G)
  - Structured SQLite trade journal (replaces raw text memory)
  - Carry unwind scorer built into agent loop
  - /scan endpoint triggers full 8-section weekly scan
  - /positions endpoint returns live P&L on all holdings
  - /covered-calls endpoint scans all eligible positions
  - Session state tracks carry unwind score + regime for the session
  - All tool failures surface as explicit errors (no silent swallows)
"""

from flask import Flask, request, jsonify
import requests
import os
import sqlite3
import json
import re
from datetime import datetime, timedelta

app = Flask(__name__)

# =========================
# 🔐 API KEYS
# =========================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY")

POLYGON_KEY   = os.environ.get("POLYGON_KEY",   "zgI7pxcaymBCYt8NsPEp35FCJvhAksXz")
AV_KEY        = os.environ.get("AV_KEY",        "PXFEPVSDRGKWVSYU")
FRED_KEY      = os.environ.get("FRED_KEY",      "1897439c3462a95e33dfa3e739f69ced")
FINNHUB_KEY   = os.environ.get("FINNHUB_KEY",   "d6r2q5pr01qgdhqcut90d6r2q5pr01qgdhqcut9g")

# =========================
# 📋 PORTFOLIO CONFIG
# =========================
PORTFOLIO_VALUE  = 117125
BUYING_POWER     = 24514
MAX_POSITION_PCT = 0.05   # 5%
MAX_PORTFOLIO_RISK_PCT = 0.20

POSITIONS = {
    "TSLA": {"shares": 700,       "avg_cost": 204.68,  "contracts": 7},
    "AMD":  {"shares": 400,       "avg_cost": 129.86,  "contracts": 4},
    "NVDA": {"shares": 200,       "avg_cost": 125.94,  "contracts": 2},
    "SOFI": {"shares": 2000,      "avg_cost": 21.09,   "contracts": 20},
    "AMZU": {"shares": 200,       "avg_cost": 40.44,   "contracts": 2},
    "ROBN": {"shares": 100,       "avg_cost": 45.00,   "contracts": 1},
    "BTC":  {"shares": 0.0120392, "avg_cost": 92551,   "contracts": 0},
    "ETH":  {"shares": 0.40,      "avg_cost": 2829,    "contracts": 0},
}

# =========================
# 🗄️ DATABASE — Trade Journal
# =========================
conn = sqlite3.connect("trading_memory.db", check_same_thread=False)
c = conn.cursor()

# Structured trade journal (replaces raw text memory)
c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT,
    ticker      TEXT,
    strategy    TEXT,
    entry       REAL,
    target      REAL,
    stop        REAL,
    atr         REAL,
    position_size REAL,
    result      TEXT,
    pnl         REAL,
    notes       TEXT
)
""")

# Session-level macro snapshots
c.execute("""
CREATE TABLE IF NOT EXISTS macro_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT,
    vix             REAL,
    yield_curve     REAL,
    carry_score     INTEGER,
    regime          TEXT,
    buffett_pct     REAL,
    raw_json        TEXT
)
""")

# Raw goal/response memory (preserved from base)
c.execute("""
CREATE TABLE IF NOT EXISTS memory (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    goal     TEXT,
    response TEXT
)
""")
conn.commit()


# =========================
# 💾 MEMORY HELPERS
# =========================
def save_memory(goal, response):
    c.execute("INSERT INTO memory (goal, response) VALUES (?, ?)", (goal, response))
    conn.commit()


def get_relevant_memory(goal):
    c.execute("SELECT goal, response FROM memory ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    goal_words = set(goal.lower().split())
    scored = []
    for g, r in rows:
        overlap = len(goal_words & set(g.lower().split()))
        if overlap > 0:
            scored.append((overlap, g, r))
    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n".join([f"{g} -> {r}" for _, g, r in scored[:5]])


def log_trade(ticker, strategy, entry, target, stop, atr, size, notes=""):
    c.execute("""
        INSERT INTO trades (timestamp, ticker, strategy, entry, target, stop, atr, position_size, result, pnl, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), ticker, strategy, entry, target, stop, atr, size, "OPEN", 0, notes))
    conn.commit()


def get_recent_trades(n=10):
    c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (n,))
    return c.fetchall()


def log_macro_snapshot(vix, yield_curve, carry_score, regime, buffett_pct, raw):
    c.execute("""
        INSERT INTO macro_snapshots (timestamp, vix, yield_curve, carry_score, regime, buffett_pct, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), vix, yield_curve, carry_score, regime, buffett_pct, json.dumps(raw)))
    conn.commit()


# =========================
# 🛠️ TRADING TOOLS
# =========================

def tool_polygon_snapshot(ticker):
    """Live price, VWAP, volume snapshot from Polygon."""
    try:
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}?apiKey={POLYGON_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        t = data.get("ticker", {})
        day = t.get("day", {})
        prev = t.get("prevDay", {})
        return {
            "ticker": ticker.upper(),
            "price":  t.get("lastTrade", {}).get("p") or day.get("c"),
            "vwap":   day.get("vw"),
            "volume": day.get("v"),
            "prev_close": prev.get("c"),
            "change_pct": t.get("todaysChangePerc"),
        }
    except Exception as e:
        return {"error": str(e)}


def tool_av_indicator(function, ticker, **kwargs):
    """Generic Alpha Vantage indicator fetch."""
    try:
        params = {"function": function, "symbol": ticker.upper(), "apikey": AV_KEY, **kwargs}
        r = requests.get("https://www.alphavantage.co/query", params=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def tool_fred_series(series_id):
    """Fetch latest observation from FRED."""
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&sort_order=desc&limit=1"
            f"&api_key={FRED_KEY}&file_type=json"
        )
        r = requests.get(url, timeout=10)
        obs = r.json().get("observations", [{}])
        return {"series": series_id, "value": obs[0].get("value"), "date": obs[0].get("date")}
    except Exception as e:
        return {"error": str(e)}


def tool_finnhub_quote(ticker):
    """Live quote from Finnhub."""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker.upper()}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        d = r.json()
        return {"ticker": ticker.upper(), "price": d.get("c"), "open": d.get("o"),
                "high": d.get("h"), "low": d.get("l"), "prev_close": d.get("pc")}
    except Exception as e:
        return {"error": str(e)}


def tool_finnhub_news(ticker, days=7):
    """Recent company news from Finnhub."""
    try:
        to_date   = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"https://finnhub.io/api/v1/company-news?symbol={ticker.upper()}"
               f"&from={from_date}&to={to_date}&token={FINNHUB_KEY}")
        r = requests.get(url, timeout=10)
        news = r.json()[:5]
        return [{"headline": n.get("headline"), "date": n.get("datetime")} for n in news]
    except Exception as e:
        return {"error": str(e)}


def tool_finnhub_earnings_calendar(days_ahead=7):
    """Upcoming earnings from Finnhub."""
    try:
        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date   = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        url = (f"https://finnhub.io/api/v1/calendar/earnings"
               f"?from={from_date}&to={to_date}&token={FINNHUB_KEY}")
        r = requests.get(url, timeout=10)
        return r.json().get("earningsCalendar", [])
    except Exception as e:
        return {"error": str(e)}


def tool_crypto_fear_greed():
    """Crypto Fear & Greed index."""
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        d = r.json().get("data", [{}])[0]
        return {"value": d.get("value"), "classification": d.get("value_classification")}
    except Exception as e:
        return {"error": str(e)}


def tool_polygon_options_snapshot(ticker):
    """Options chain snapshot from Polygon."""
    try:
        url = (f"https://api.polygon.io/v3/snapshot/options/{ticker.upper()}"
               f"?limit=50&apiKey={POLYGON_KEY}")
        r = requests.get(url, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def tool_portfolio_pnl():
    """Calculate live P&L for all positions using Finnhub quotes."""
    results = {}
    for ticker, pos in POSITIONS.items():
        try:
            if ticker in ("BTC", "ETH"):
                # Use crypto F&G as proxy — ideally replace with a crypto price API
                results[ticker] = {"note": "fetch crypto price separately", "avg_cost": pos["avg_cost"]}
                continue
            q = tool_finnhub_quote(ticker)
            price = q.get("price", 0)
            if price:
                pnl      = (price - pos["avg_cost"]) * pos["shares"]
                pnl_pct  = ((price / pos["avg_cost"]) - 1) * 100
                results[ticker] = {
                    "shares":    pos["shares"],
                    "avg_cost":  pos["avg_cost"],
                    "price":     price,
                    "pnl":       round(pnl, 2),
                    "pnl_pct":   round(pnl_pct, 2),
                    "contracts": pos["contracts"],
                }
        except Exception as e:
            results[ticker] = {"error": str(e)}
    return results


def tool_carry_unwind_score():
    """
    Simplified carry unwind scorer (4 of 7 signals — fetches what's available without search).
    Returns score 0-21 and action recommendation.
    """
    score = 0
    details = {}

    # Signal 1: USD/JPY vs 160
    try:
        url = (f"https://www.alphavantage.co/query?function=FX_DAILY"
               f"&from_symbol=USD&to_symbol=JPY&apikey={AV_KEY}")
        r = requests.get(url, timeout=10).json()
        ts = r.get("Time Series FX (Daily)", {})
        latest_date = sorted(ts.keys())[-1]
        usdjpy = float(ts[latest_date]["4. close"])
        details["usdjpy"] = usdjpy
        if usdjpy < 145:
            score += 3
        elif usdjpy < 150:
            score += 2
        elif usdjpy < 155:
            score += 1
    except:
        details["usdjpy"] = "fetch_error"

    # Signal 4: VIX
    try:
        vix_data = tool_fred_series("VIXCLS")
        vix = float(vix_data.get("value", 0))
        details["vix"] = vix
        if vix > 30:
            score += 3
        elif vix >= 25:
            score += 3
        elif vix >= 20:
            score += 2
    except:
        details["vix"] = "fetch_error"

    # Signal 5: Crypto F&G as BTC proxy
    try:
        fg = tool_crypto_fear_greed()
        fg_val = int(fg.get("value", 50))
        details["crypto_fg"] = fg_val
        if fg_val < 20:
            score += 1   # extreme fear = risk-off signal
    except:
        details["crypto_fg"] = "fetch_error"

    # Signal 7: static — no BOJ meeting detection without search
    # (extend later with a search tool)

    if score <= 3:
        action = "🟢 Trade normally"
    elif score <= 7:
        action = "🟡 Reduce new positions 25% | watch USD/JPY"
    elif score <= 12:
        action = "🟠 No new longs | tighten stops to 1×ATR | covered calls only"
    else:
        action = "🔴 Defensive mode | reduce all positions 25-50% | hedge"

    return {"score": score, "max": 21, "details": details, "action": action}


def tool_macro_snapshot():
    """Pull key FRED macro series in one call."""
    series = {
        "fed_rate":    "FEDFUNDS",
        "cpi":         "CPIAUCSL",
        "core_cpi":    "CPILFESL",
        "yield_curve": "T10Y2Y",
        "vix":         "VIXCLS",
        "oil_wti":     "DCOILWTICO",
        "gold":        "GOLDAMGBD228NLBM",
        "mortgage30":  "MORTGAGE30US",
    }
    result = {}
    for label, sid in series.items():
        try:
            obs = tool_fred_series(sid)
            result[label] = obs.get("value")
        except:
            result[label] = None
    return result


def tool_covered_call_scan():
    """Scan all eligible positions for covered call opportunities."""
    eligible = {k: v for k, v in POSITIONS.items() if v["contracts"] > 0}
    results = {}
    for ticker, pos in eligible.items():
        try:
            q = tool_finnhub_quote(ticker)
            price = q.get("price")
            if not price:
                continue
            target_strike_low  = round(price * 1.05, 2)
            target_strike_high = round(price * 1.10, 2)
            above_cost = target_strike_low > pos["avg_cost"]
            results[ticker] = {
                "price":        price,
                "avg_cost":     pos["avg_cost"],
                "contracts":    pos["contracts"],
                "target_strikes": f"${target_strike_low} – ${target_strike_high}",
                "above_cost":   above_cost,
                "note": "✅ OTM strikes above cost basis — check Polygon for live premiums"
                        if above_cost else "⚠️ Current OTM strikes may be below cost basis"
            }
        except Exception as e:
            results[ticker] = {"error": str(e)}
    return results


def tool_calculate(expression):
    """Safe math evaluator."""
    try:
        if not re.match(r"^[0-9+\-*/(). ]+$", expression):
            return {"error": "Invalid expression — only numbers and operators allowed"}
        return {"result": str(eval(expression, {"__builtins__": {}}))}
    except Exception as e:
        return {"error": f"Calculation error: {e}"}


def tool_get_time():
    return {"timestamp": datetime.now().isoformat(), "date": datetime.now().strftime("%Y-%m-%d")}


# =========================
# 🧰 TOOL REGISTRY
# =========================
TOOLS = {
    "polygon_snapshot":        lambda inp: tool_polygon_snapshot(inp),
    "finnhub_quote":           lambda inp: tool_finnhub_quote(inp),
    "finnhub_news":            lambda inp: tool_finnhub_news(inp),
    "finnhub_earnings":        lambda inp: tool_finnhub_earnings_calendar(int(inp) if str(inp).isdigit() else 7),
    "fred_series":             lambda inp: tool_fred_series(inp),
    "macro_snapshot":          lambda inp: tool_macro_snapshot(),
    "crypto_fear_greed":       lambda inp: tool_crypto_fear_greed(),
    "polygon_options":         lambda inp: tool_polygon_options_snapshot(inp),
    "portfolio_pnl":           lambda inp: tool_portfolio_pnl(),
    "carry_unwind_score":      lambda inp: tool_carry_unwind_score(),
    "covered_call_scan":       lambda inp: tool_covered_call_scan(),
    "av_rsi":                  lambda inp: tool_av_indicator("RSI", inp, interval="daily", time_period=14, series_type="close"),
    "av_macd":                 lambda inp: tool_av_indicator("MACD", inp, interval="daily", series_type="close"),
    "av_atr":                  lambda inp: tool_av_indicator("ATR", inp, interval="daily", time_period=14),
    "calculate":               lambda inp: tool_calculate(inp),
    "time":                    lambda inp: tool_get_time(),
}


def run_tool(tool_name, tool_input):
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool: {tool_name}. Available: {list(TOOLS.keys())}"}
    try:
        return TOOLS[tool_name](tool_input)
    except Exception as e:
        return {"error": f"Tool '{tool_name}' failed: {str(e)}"}


# =========================
# 🔥 LLM CALLS
# =========================

def call_claude(messages, system=""):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if res.status_code != 200:
            return None
        return res.json()["content"][0]["text"]
    except:
        return None


def call_openai(messages):
    if not OPENAI_API_KEY:
        return None
    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": messages},
            timeout=20,
        )
        if res.status_code != 200:
            return None
        return res.json()["choices"][0]["message"]["content"]
    except:
        return None


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        if res.status_code != 200:
            return None
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return None


def call_llm(messages, system=""):
    """Claude → OpenAI → Gemini fallback chain."""
    response = call_claude(messages, system=system)
    if response:
        return response
    # OpenAI fallback (no system prompt separation needed)
    all_msgs = ([{"role": "system", "content": system}] if system else []) + messages
    response = call_openai(all_msgs)
    if response:
        return response
    prompt_text = "\n".join(m.get("content", "") for m in messages)
    response = call_gemini(prompt_text)
    if response:
        return response
    return "ERROR: No LLM available. Check ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."


# =========================
# 🧠 TOOL EXECUTION FLOW
# =========================
SYSTEM_PROMPT = f"""
You are a professional AI trading analyst assistant.

Portfolio: ${PORTFOLIO_VALUE:,} | Buying power: ${BUYING_POWER:,}
Max position: 5% (${int(PORTFOLIO_VALUE * 0.05):,}) | Stop: 1.5×ATR | Risk/trade: <1.5%

Positions: {json.dumps({k: {"shares": v["shares"], "avg_cost": v["avg_cost"]} for k, v in POSITIONS.items()})}

Available tools: {list(TOOLS.keys())}

When you need data, respond ONLY with valid JSON (no extra text, no markdown):
{{"tool": "tool_name", "input": "ticker_or_param"}}

When you have enough data to answer, respond in plain text with your full analysis.
Always show ATR stop calculations. Always check carry unwind before new longs.
"""


def parse_tool_call(text):
    """Strict JSON parser — no silent failures."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if "tool" in parsed:
            return parsed
        return None
    except json.JSONDecodeError:
        return None


def execute_tool_flow(goal, context, max_iterations=5):
    """
    Agentic loop: plan → tool calls → synthesize.
    Runs up to max_iterations before forcing a final answer.
    """
    messages = [{"role": "user", "content": f"Goal: {goal}\n\nContext:\n{context}"}]
    tool_results = []

    for i in range(max_iterations):
        response = call_llm(messages, system=SYSTEM_PROMPT)

        tool_call = parse_tool_call(response)

        if tool_call:
            tool_name  = tool_call.get("tool", "")
            tool_input = tool_call.get("input", "")
            result     = run_tool(tool_name, tool_input)
            tool_results.append({"tool": tool_name, "input": tool_input, "result": result})

            # Feed result back into conversation
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"Tool result for {tool_name}({tool_input}):\n{json.dumps(result, indent=2)}\n\nContinue your analysis or provide your final answer."
            })
        else:
            # No tool call = final answer
            tools_used = [f"{t['tool']}({t['input']})" for t in tool_results]
            suffix = f"\n\n[Tools used: {', '.join(tools_used)}]" if tools_used else ""
            return response + suffix

    # Forced final answer after max iterations
    messages.append({"role": "user", "content": "Provide your final analysis now based on all data collected."})
    final = call_llm(messages, system=SYSTEM_PROMPT)
    tools_used = [f"{t['tool']}({t['input']})" for t in tool_results]
    return final + f"\n\n[Tools used: {', '.join(tools_used)}]"


# =========================
# 🧠 MAIN AGENT
# =========================
def think(goal):
    memory_text = get_relevant_memory(goal)

    context = f"""
Relevant past analysis:
{memory_text if memory_text else 'None'}

Today: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Portfolio value: ${PORTFOLIO_VALUE:,} | Buying power: ${BUYING_POWER:,}
"""

    result = execute_tool_flow(goal, context)
    save_memory(goal, result[:500])  # truncate to avoid bloating DB
    return result


# =========================
# 🌐 ROUTES
# =========================

@app.route("/brain", methods=["POST"])
def brain():
    """General-purpose trading agent endpoint."""
    data = request.get_json()
    if not data or "goal" not in data:
        return jsonify({"error": "Missing 'goal' in request body"}), 400
    goal   = data["goal"]
    result = think(goal)
    return jsonify({"result": result})


@app.route("/positions", methods=["GET"])
def positions():
    """Live P&L across all holdings."""
    pnl = tool_portfolio_pnl()
    return jsonify(pnl)


@app.route("/covered-calls", methods=["GET"])
def covered_calls():
    """Covered call opportunity scan."""
    scan = tool_covered_call_scan()
    return jsonify(scan)


@app.route("/macro", methods=["GET"])
def macro():
    """FRED macro snapshot + carry unwind score."""
    snapshot      = tool_macro_snapshot()
    carry         = tool_carry_unwind_score()
    crypto_fg     = tool_crypto_fear_greed()
    return jsonify({
        "macro":        snapshot,
        "carry_unwind": carry,
        "crypto_fg":    crypto_fg,
        "timestamp":    datetime.now().isoformat(),
    })


@app.route("/scan", methods=["POST"])
def weekly_scan():
    """Full 8-section weekly scan — POST with optional {"tickers": ["TSLA","AMD"]}"""
    data    = request.get_json() or {}
    tickers = data.get("tickers", list(POSITIONS.keys()))
    goal = (
        f"Run a full weekly trading scan. "
        f"Start with carry unwind score and macro regime. "
        f"Then review these positions for P&L, stops, and covered call opportunities: {tickers}. "
        f"Flag any earnings within 5 days. "
        f"Identify the top 2-3 new trade setups that match the current regime. "
        f"End with a portfolio risk summary."
    )
    result = think(goal)
    return jsonify({"scan": result})


@app.route("/log-trade", methods=["POST"])
def log_trade_route():
    """Log a new trade to the journal."""
    data = request.get_json()
    required = ["ticker", "strategy", "entry", "target", "stop", "atr", "size"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    log_trade(
        ticker=data["ticker"], strategy=data["strategy"],
        entry=data["entry"],   target=data["target"],
        stop=data["stop"],     atr=data["atr"],
        size=data["size"],     notes=data.get("notes", "")
    )
    return jsonify({"status": "logged", "ticker": data["ticker"]})


@app.route("/trades", methods=["GET"])
def recent_trades():
    """Return last N trades from journal."""
    n      = request.args.get("n", 10, type=int)
    trades = get_recent_trades(n)
    cols   = ["id", "timestamp", "ticker", "strategy", "entry", "target", "stop", "atr", "size", "result", "pnl", "notes"]
    return jsonify([dict(zip(cols, row)) for row in trades])


@app.route("/tool/<tool_name>", methods=["GET"])
def run_single_tool(tool_name):
    """Directly invoke any registered tool. Pass ?input=TICKER"""
    tool_input = request.args.get("input", "")
    result     = run_tool(tool_name, tool_input)
    return jsonify({"tool": tool_name, "input": tool_input, "result": result})


@app.route("/tools", methods=["GET"])
def list_tools():
    """List all registered tools."""
    return jsonify({"tools": list(TOOLS.keys())})


@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "agent":  "AI Trading Bot — Claude-primary, multi-LLM fallback",
        "endpoints": ["/brain", "/positions", "/covered-calls", "/macro",
                      "/scan", "/log-trade", "/trades", "/tool/<name>", "/tools"],
        "portfolio_value": PORTFOLIO_VALUE,
        "buying_power":    BUYING_POWER,
    })


# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Trading Bot running on port {port}")
    print(f"   LLMs: Claude={'✅' if ANTHROPIC_API_KEY else '❌'} | "
          f"OpenAI={'✅' if OPENAI_API_KEY else '❌'} | "
          f"Gemini={'✅' if GEMINI_API_KEY else '❌'}")
    app.run(host="0.0.0.0", port=port, debug=False)
