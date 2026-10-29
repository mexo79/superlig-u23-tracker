"""Daily Süper Lig U23 tracker. SofaScore is an unofficial data source.
Only performance columns are refreshed; TFF eligibility stays in the TFF Kontenjan tab.
"""
import os, json, datetime, time, urllib.request, urllib.error
import gspread
from google.oauth2.service_account import Credentials

LEAGUE_ID = 52
SEASON_ID = int(os.getenv("SOFASCORE_SEASON_ID", "98080"))
URL = f"https://www.sofascore.com/api/v1/unique-tournament/{LEAGUE_ID}/season/{SEASON_ID}/statistics"
FIELDS = "appearances,minutesPlayed,started,rating,goals,assists,yellowCards,redCards"
SHEET_NAMES = ("Tüm U23", "U23 Yabancı", "U23 Türk")
STAT_HEADERS = ("Dakika", "Maç", "İlk 11", "Ortalama reyting", "Gol", "Asist", "Sarı kart", "Kırmızı kart")
SOURCE_HEADERS = ["SofaScore ID","Oyuncu","Kulüp","Mevki","Doğum tarihi",*STAT_HEADERS,"2026-27 kontenjanı","2027-28 kontenjanı","SofaScore güncelleme","TFF kontrol tarihi","SofaScore profil","TFF kaynak","Veri durumu","Yerli / Yabancı"]

def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SuperLigU23Tracker/0.1)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=22) as response:
        return json.load(response)

def get_player_stats():
    # Undocumented SofaScore endpoint. It may change or reject automated access.
    players = {}
    for offset in range(0, 1200, 100):
        query = "?limit=100&offset=" + str(offset) + "&order=-rating&accumulation=total&fields=" + FIELDS
        data = fetch_json(URL + query)
        items = data.get("results")
        if not isinstance(items, list):
            raise RuntimeError("SofaScore response did not contain a results list")
        for result in items:
            p = result.get("player") or {}
            player_id = p.get("id")
            if not player_id:
                continue
            stats = result.get("statistics") or {}
            players[str(player_id)] = {"player": p, "statistics": stats, "team":result.get("team") or {}}
        if len(items) < 100:
            break
        time.sleep(1)
    if not players:
        raise RuntimeError("No players received; refusing to overwrite the sheet")
    return players

def sheet_connection():
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds).open_by_key(os.environ["GOOGLE_SHEET_ID"])

def stat_value(value, *, rating=False):
    if value is None:
        return ""
    try:
        n = float(value)
        return round(n, 2) if rating else int(n)
    except (TypeError, ValueError):
        return ""

def build_output(source, players):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    output = []
    for entry in source:
        if not entry or not str(entry[0]).strip():
            continue
        row = (entry + [""] * len(SOURCE_HEADERS))[:len(SOURCE_HEADERS)]
        pid = str(row[0]).strip().replace(".0","")
        item = players.get(pid)
        if item:
            stats = item["statistics"]
            values = [
                stat_value(stats.get("minutesPlayed")), stat_value(stats.get("appearances")),
                stat_value(stats.get("started")),stat_value(stats.get("rating"),rating=True),
                stat_value(stats.get("goals")),stat_value(stats.get("assists")),
                stat_value(stats.get("yellowCards")),stat_value(stats.get("redCards"))
            ]
            row[5:13] = values
            row[15] = now
            row[17] = "https://www.sofascore.com/player/" + str(pid)
            row[19] = "SofaScore doğrulandı"
        else:
            # Retain previous performance values; do not fabricate zeroes.
            row[19] = "Eşleşme yok / eski veri korundu" if pid else "SofaScore oyuncu ID eksik"
        output.append(row)
    return output

def main():
    book = sheet_connection()
    tff = book.worksheet("TFF Kontenjan")
    all_rows = tff.get_all_values()
    if len(all_rows) < 2:
        raise RuntimeError("TFF Kontenjan oyuncu listesi boş; başlangıç kadrosu gerekli")
    # Seed input is the stable ID table. TFF eligibility never comes from SofaScore.
    master = book.worksheet("Tüm U23")
    old = master.get_all_values()
    past = {str(r[0]).strip():r for r in old[1:] if r and str(r[0]).strip()}
    rows = []
    for x in all_rows[1:]:
        if not x or not x[0].strip():
            continue
        pid = x[0].strip()
        row = (past.get(pid) or [""]*len(SOURCE_HEADERS)).copy()
        row = (row+[""]*len(SOURCE_HEADERS))[:len(SOURCE_HEADERS)]
        row[0] = pid
        row[1] = x[1] if len(x)>1 else row[1]
        row[2] = x[2] if len(x)>2 else row[2]
        row[4] = x[3] if len(x)>3 else row[4]
        row[20] = ("Yabancı" if "yabancı" in x[4].lower() else "Yerli") if len(x)>4 else row[20]
        row[13] = x[5] if len(x)>5 else row[13]
        row[14] = x[6] if len(x)>6 else row[14]
        row[18] = x[7] if len(x)>7 else row[18]
        row[16] = x[8] if len(x)>8 else row[16]
        rows.append(row)
    players = get_player_stats() # Fail closed before writing.
    output = build_output(rows,players)
    if not output:
        raise RuntimeError("No usable roster entries; refusing to overwrite")
    targets = {
        "Tüm U23":output,
        "U23 Yabancı":[r for r in output if str(r[20]).strip() == "Yabancı"],
        "U23 Türk":[r for r in output if str(r[20]).strip() == "Yerli"]
    }
    for tab, records in targets.items():
        ws = book.worksheet(tab)
        # Clear only the used rectangle, preserve formatting/filter controls.
        ws.batch_clear(["A2:U1000"])
        if records:
            records.sort(key=lambda r: (float(r[5]) if isinstance(r[5], (int,float)) else -1),reverse=True)
            ws.update(range_name=f"A2:U{len(records)+1}",values=records,value_input_option="USER_ENTERED")
    print(f"Updated {len(output)} players from {len(players)} SofaScore records.")

if __name__=="__main__":
    main()
