import os
import requests
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

offset = None


# ---------- PROBABILITY HELPERS ----------

def decimal_to_prob(decimal_odds: float) -> float:
    return 1.0 / decimal_odds

def american_to_prob(american_odds: int) -> float:
    if american_odds > 0:
        return 100 / (american_odds + 100)
    return -american_odds / (-american_odds + 100)

def parse_odds(token: str) -> float:
    t = token.strip()

    # American odds
    if (t.startswith("+") or t.startswith("-")) and t[1:].isdigit():
        return american_to_prob(int(t))

    # Decimal odds
    dec = float(t)
    if dec <= 1:
        raise ValueError("Decimal odds must be > 1")
    return decimal_to_prob(dec)


# ---------- TELEGRAM MESSAGE ----------

def send_message(chat_id, text):
    requests.post(
        f"{API_URL}/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    )


# ---------- PARLAY CALCULATION ----------

def handle_parlay(chat_id, text):
    parts = text.split()
    odds_tokens = parts[1:] if text.startswith("/parlay") else parts

    if len(odds_tokens) < 2:
        send_message(chat_id, "⚠️ Please enter at least *two* odds.\nExample:\n`/parlay +150 -200 1.80`")
        return

    try:
        probs = [parse_odds(tok) for tok in odds_tokens]
    except:
        send_message(chat_id, "❌ Invalid odds format.\nTry:\n`/parlay +150 -200 1.80`")
        return

    # Calculate parlay probability
    parlay_prob = 1.0
    for p in probs:
        parlay_prob *= p

    decimal_odds = 1 / parlay_prob

    # Formatting output
    legs_text = ""
    for i, tok in enumerate(odds_tokens, 1):
        legs_text += f"• Leg {i}: `{tok}` → {probs[i-1]*100:.2f}%\n"

    message = (
        "📊 *Parlay Probability*\n"
        "────────────────────\n"
        f"{legs_text}"
        "────────────────────\n"
        f"🎯 Chance to hit: *{parlay_prob*100:.2f}%*\n"
        f"💰 Decimal Odds: *{decimal_odds:.2f}x*\n"
    )

    send_message(chat_id, message)


# ---------- MAIN LOOP ----------

def main():
    global offset

    while True:
        params = {"timeout": 25}
        if offset is not None:
            params["offset"] = offset

        response = requests.get(f"{API_URL}/getUpdates", params=params).json()

        if response.get("ok"):
            for update in response["result"]:
                offset = update["update_id"] + 1

                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")

                if text.startswith("/start"):
                    send_message(chat_id, "🤖 Send odds like:\n`/parlay +150 -200 1.80`")
                elif text.startswith("/help"):
                    send_message(chat_id, "Use `/parlay` followed by odds.\nExample:\n`/parlay +150 -200 1.80`")
                elif text.startswith("/parlay"):
                    handle_parlay(chat_id, text)
                else:
                    if any(char.isdigit() for char in text):
                        try:
                            handle_parlay(chat_id, text)
                        except:
                            pass

        time.sleep(0.5)


if __name__ == "__main__":
    main()
