"""Incremental Süper Lig statistics sync via a RapidAPI provider.

Provider: https://football-api.yuvron.online/leagues/super-lig
This provider is NOT TFF. TFF eligibility remains manually verified and separate.
Fails closed when data/API credentials/response format are missing.
"""
import datetime as dt
import difflib
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

import gspread
from google.oauth2.service_account import Credentials

BASE = "https://super-lig.p.rapidapi.com"
HOST = "super-lig.p.rapidapi.com"
SEASON = os.getenv("LEAGUE_SEASON", "2026-27")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
PLAYER_COLUMNS = 21
MATCH_TAB = "API Maçları"
PLAYER_TAB = "API Oyuncu Maçları"
METRIC_KEYS = ("minutes", "matches", "starts", "rating", "goals", "assists", "yellow", "red")
SOURCE = "Super Lig RapidAPI (Yuvron)"

def number(value):
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        value = value.get("total", value.get("value"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def first_available(obj, *keys):
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k] is not None:
            return obj[k]
    return None

def normalize(value):
    value = str(value or "").lower().replace("ı", "i").replace("İ", "i")
    value = unicodedata.normalize("NFKD", value)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in value if not unicodedata.combining(c)))

def team_score(a, b):
    aa, bb = normalize(a), normalize(b)
    if not aa or not bb:
        return 0
    if aa == bb:
        return 1
    common = ["spor", "footballclub", "futbolkulubu", "sk", "fk"]
    for suffix in common:
        if aa.endswith(suffix): aa=aa[:-len(suffix)]
        if bb.endswith(suffix): bb=bb[:-len(suffix)]
    if aa == bb:
        return 1
    if len(aa) >= 5 and len(bb) >= 5 and (aa in bb or bb in aa):
        return .92
    return difflib.SequenceMatcher(None, aa, bb).ratio()

def api_get(path, params=None):
    key = os.environ["RAPIDAPI_KEY"]
    if params:
        path += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        BASE + path, headers={"X-RapidAPI-Key":key,"X-RapidAPI-Host":HOST,
                              "Accept":"application/json","User-Agent":"SuperLigU23Tracker/0.2"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or payload.get("error") or "data" not in payload:
        raise RuntimeError(f"API returned an error/incompatible payload for {path}: {str(payload)[:200]}")
    return payload

def all_matches():
    matches = []
    for page in range(1, 15):
        payload = api_get("/matches", {"season": SEASON, "page": page, "limit": 100})
        records = payload["data"]
        if not isinstance(records, list):
            raise RuntimeError("Expected list of matches")
        if not records: break
        matches.extend(records)
        meta = payload.get("meta") or {}
        pages = first_available(meta, "totalPages", "pages")
        if isinstance(pages, int) and page >= pages: break
        total = first_available(meta, "total", "count")
        if isinstance(total, int) and len(matches) >= total: break
        if len(records) < 100 and not (isinstance(total,int) and len(matches) < total):
            break
        time.sleep(.25)
    if not matches:
        raise RuntimeError("Empty match list: refusing any sheet update")
    return matches

def completed(fixture):
    status = fixture.get("status")
    if isinstance(status, dict): status = status.get("type") or status.get("short") or status.get("name")
    return normalize(status) in {"finished","ft","aet","pen","fulltime"}

def stats_from_entry(entry, group):
    p = entry.get("player")
    if not isinstance(p, dict):
        p = entry
    pid = first_available(p, "id") or first_available(entry, "playerId")
    name = first_available(p, "name", "shortName")
    if pid is None or not name:
        return None
    stats = entry.get("stats") or entry.get("statistics") or {}
    if isinstance(stats, list):
        stats = {str(s.get("type")):s.get("value") for s in stats if isinstance(s, dict)}
    metrics = []
    metrics.append(number(first_available(stats,"minutes","minutesPlayed","playedMinutes")) if stats else None)
    if metrics[0] is None:
        metrics[0] = number(first_available(entry,"minutes","minutesPlayed","playedMinutes"))
    if metrics[0] is None or metrics[0] <= 0:
        return None  # bench unused or missing minutes: never invent appearances
    metrics.append(1)
    metrics.append(1 if group == "starting" else 0)
    metrics.append(number(first_available(stats,"rating","avgRating") if stats else None))
    if metrics[3] is None:
        metrics[3] = number(first_available(entry,"rating","avgRating"))
    for names in [("goals","goalsScored"),("assists","goalAssists"),("yellowCards","yellow"),
                  ("redCards","red")]:
        value = first_available(stats, *names) if stats else None
        if value is None:
            value = first_available(entry, *names)
        metrics.append(number(value))
    return str(pid), str(name), metrics

def parse_fixture(payload):
    fixture = payload["data"]
    if not isinstance(fixture, dict):
        raise RuntimeError("Match detail response is not an object")
    fixture_id = fixture.get("id")
    lineups = fixture.get("lineups") or {}
    if not fixture_id or not isinstance(lineups, dict):
        raise RuntimeError("Missing match id/lineups")
    output = []
    for side in ("home","away"):
        block = lineups.get(side) or {}
        if not isinstance(block, dict): continue
        team = fixture.get("homeTeam" if side == "home" else "awayTeam") or {}
        team_name = str(team.get("name") or "")
        for group in ("starting","bench"):
            entries = block.get(group) or []
            if not isinstance(entries,list): continue
            for entry in entries:
                if not isinstance(entry,dict): continue
                parsed = stats_from_entry(entry,group)
                if parsed:
                    pid,name,metrics = parsed
                    output.append([str(fixture_id),pid,name,team_name,*[x if x is not None else "" for x in metrics]])
    # A tiny/empty set would lead to false zeroes and missed players.
    if len(output) < 10:
        raise RuntimeError(f"Match {fixture_id} contains fewer than 10 usable player statistic rows")
    return output

def connect_sheet():
    account = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return gspread.authorize(Credentials.from_service_account_info(account, scopes=scopes)).open_by_key(SHEET_ID)

def read_ledger(sheet):
    values=sheet.worksheet(PLAYER_TAB).get_all_values()
    rows={}
    for r in values[1:]:
        if len(r)>=12 and r[0].strip() and r[1].strip():
            rows[(r[0].strip(),r[1].strip())] = r[:12]
    return rows

def summarize(rows):
    by_id={}
    for r in rows.values():
        pid = r[1]
        info=by_id.setdefault(pid,{"name":r[2],"teams":set(),"matches":[]})
        info["teams"].add(r[3])
        info["matches"].append([number(v) for v in r[4:12]])
    return by_id

def choose_player(name,club,by_id,current_id):
    if current_id and str(current_id) in by_id:
        return str(current_id)
    candidates=[]
    for pid,p in by_id.items():
        name_fit=difflib.SequenceMatcher(None,normalize(name),normalize(p["name"])).ratio()
        if normalize(name)==normalize(p["name"]): name_fit=1
        club_fit=max((team_score(club,t) for t in p["teams"]),default=0)
        if name_fit>=.91 and club_fit>=.78:
            candidates.append((name_fit+club_fit,pid))
    candidates.sort(reverse=True)
    if len(candidates)==1 or (len(candidates)>1 and candidates[0][0]-candidates[1][0]>.15):
        return candidates[0][1]
    return None

def totals(p):
    rows=p["matches"]
    results=[]
    for i in range(8):
        values=[r[i] for r in rows if r[i] is not None]
        if not values or len(values)!=len(rows):
            results.append("")  # incomplete provider coverage; never assert zero
        elif i==3:
            results.append(round(sum(values)/len(values),2))
        else:
            results.append(int(sum(values)))
    return results

def run():
    for field in ("GOOGLE_SERVICE_ACCOUNT_JSON","GOOGLE_SHEET_ID","RAPIDAPI_KEY"):
        if not os.getenv(field):
            raise RuntimeError(f"Required setup missing: {field}. No data was changed.")
    sheet=connect_sheet()
    roster_ws=sheet.worksheet("Tüm U23")
    roster=roster_ws.get_all_values()
    if len(roster)<2: raise RuntimeError("Roster is empty")
    ledger_ws=sheet.worksheet(PLAYER_TAB)
    matches_ws=sheet.worksheet(MATCH_TAB)
    ledger=read_ledger(sheet)
    fetched={r[0] for r in matches_ws.get_all_values()[1:] if r and r[0]}
    fixtures=all_matches()
    candidates=[f for f in fixtures if completed(f) and str(f.get("id") or "") not in fetched]
    fixture_rows=[]
    for f in candidates:
        fixture_id=str(f.get("id") or "")
        if not fixture_id: continue
        try:
            detail=api_get("/matches/"+urllib.parse.quote(fixture_id))
            matchrows=parse_fixture(detail)
            for r in matchrows: ledger[(r[0],r[1])] = r
            fixture_rows.append([fixture_id,str(f.get("kickoff") or ""),str(f.get("status") or "finished"),
                                 dt.datetime.now(dt.timezone.utc).isoformat(),len(matchrows)])
            print(f"Loaded fixture {fixture_id}: {len(matchrows)} players")
        except Exception as err:
            print(f"WARNING {fixture_id}: {err}")
        time.sleep(.35)
    if not ledger:
        raise RuntimeError("No confirmed player-match data, refusing to write")
    grouped=summarize(ledger)
    if not grouped:
        raise RuntimeError("No players in aggregate")
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_output=[]
    matched=0
    for original in roster[1:]:
        if not original or len(original)<2 or not original[1].strip(): continue
        row=(original+[""]*PLAYER_COLUMNS)[:PLAYER_COLUMNS]
        pid=choose_player(row[1],row[2],grouped,row[0])
        if pid:
            matched+=1
            row[0]=pid
            row[5:13]=totals(grouped[pid])
            row[15]=stamp
            row[17]=BASE+"/players/"+pid
            row[19]=SOURCE+" | 2026-27 | "+("tam" if all(x!="" for x in row[5:13]) else "kısmi")
        else:
            row[19]=row[19] or "API kimlik eşleştirmesi bekliyor"
        all_output.append(row)
    if matched==0:
        raise RuntimeError("No roster members matched provider IDs; refusing to overwrite the sheet")
    all_output.sort(key=lambda r: float(r[5]) if isinstance(r[5],(int,float)) else -1,reverse=True)
    # Persist match ledger first: next run can resume safely after partial failure.
    if fixture_rows:
        matches_ws.append_rows(fixture_rows,value_input_option="USER_ENTERED")
        all_ledger=[ledger[k] for k in sorted(ledger)]
        ledger_ws.clear()
        ledger_ws.update(range_name=f"A1:L{len(all_ledger)+1}",
                         values=[["Maç ID","API Oyuncu ID","Oyuncu","Kulüp","Dakika","Maç","İlk 11","Reyting","Gol","Asist","Sarı","Kırmızı"],*all_ledger],
                         value_input_option="USER_ENTERED")
    for name,subset in [
        ("Tüm U23",all_output),
        ("U23 Yabancı",[r for r in all_output if normalize(r[20])=="yabanci"]),
        ("U23 Türk",[r for r in all_output if normalize(r[20])=="yerli"]),
    ]:
        ws=sheet.worksheet(name)
        ws.batch_clear(["A2:U1000"])
        if subset:
            ws.update(range_name=f"A2:U{len(subset)+1}",values=subset,value_input_option="USER_ENTERED")
    sheet.worksheet("İşlem Günlüğü").append_row([stamp,SOURCE,"Performans kontrolü","Başarılı",
                                f"Yeni maç: {len(fixture_rows)}, eşleşen: {matched}/{len(all_output)}"],value_input_option="USER_ENTERED")
    print(f"OK: {len(fixture_rows)} new matches, {matched}/{len(all_output)} players matched")

if __name__ == "__main__":
    run()
