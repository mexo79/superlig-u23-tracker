"""Optional direct writeback for users who have connected a Google service account.
Never required for publishing public CSV updates to GitHub.
"""
import csv
from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"data"
TABS=("Tüm U23","U23 Yabancı","U23 Türk")
SHEET_ID=os.environ.get("GOOGLE_SHEET_ID","1eyhOf-1Vv3LmYCRmodFMBsxAflYIRH7l3iUThRHdVuM")
def records(name):
    with open(BASE/name,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def numeric(v):
    if v is None or v=="":
        return ""
    try:
        v=float(v)
        return int(v) if v.is_integer() else v
    except (TypeError,ValueError):
        return ""

def main():
    raw=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON missing; direct Google Sheets sync disabled.")
    cred=Credentials.from_service_account_info(json.loads(raw),scopes=["https://www.googleapis.com/auth/spreadsheets"])
    book=gspread.authorize(cred).open_by_key(SHEET_ID)
    totals={r["key"]:r for r in records("official_totals.csv")}
    comps=records("competitions.csv")
    coverage=records("coverage.csv")
    snapshots={}
    for name in TABS:
        ws=book.worksheet(name)
        rows=ws.get_all_values()
        if not rows or len(rows)<50 or rows[0][1]!="Oyuncu" or rows[0][20]!="Yerli / Yabancı":
            raise RuntimeError(f"Unexpected spreadsheet schema {name}; no data modified.")
        if any((r[1]+"|"+r[2]) not in totals for r in rows[1:] if len(r)>=3 and r[1]):
            raise RuntimeError(f"Missing source players for {name}.")
        snapshots[name]=(ws,rows)
    merged={}
    for name,(ws,rows) in snapshots.items():
        out=[];status=[]
        for r in rows[1:]:
            key=r[1]+"|"+r[2]
            v=totals[key]
            out.append([numeric(v.get(k)) for k in ("minutes","matches","starts","rating","goals","assists","yellow","red")])
            status.append(["GOAL API — mevcut resmî müsabaka verileri; eksik turnuvalar olabilir; kaynak: GitHub data/coverage.csv"])
        merged[name]=(ws,out,status)
    # All rows and schemas validated, now begin edits.
    for name,(ws,out,st) in merged.items():
        ws.update(range_name=f"F2:M{len(out)+1}",values=out,value_input_option="RAW")
        ws.update(range_name=f"T2:T{len(st)+1}",values=st,value_input_option="RAW")
    roster_lookup={(r[1]+"|"+r[2]):r for r in snapshots["Tüm U23"][1][1:] if len(r)>20}
    details=[["API Oyuncu ID","Oyuncu","Kulüp","Mevki","Yerli / Yabancı","Müsabaka",
              "Kulüp / Millî takım","Kulvar","Grup","Dakika","Maç","İlk 11",
              "Ortalama reyting","Gol","Asist","Sarı kart","Kırmızı kart","Kapsam"]]
    for c in comps:
        roster=roster_lookup.get(c["key"])
        if not roster:continue
        kind=c["category"]
        details.append([c["api_id"],c["player"],c["club"],roster[3],roster[20],
                        c["competition"],c["club_or_national_team"],kind,
                        "Millî" if kind=="Millî takım" else ("Süper Lig" if c["competition"]=="Süper Lig" else "Kupa"),
                        *[numeric(c.get(k)) for k in ("minutes","matches","starts","rating","goals","assists","yellow","red")],
                        c["coverage"]])
    ws=book.worksheet("Turnuva Bazında")
    ws.batch_clear(["A2:R1000"])
    ws.update(range_name=f"A1:R{len(details)}",values=details,value_input_option="RAW")
    cv=[["Turnuva","Dönem","Kategori","Tamamlanan maç","Oyuncu verili maç","Oyuncu verisi eksik maç","Durum"]]
    cv.extend([[x["competition"],"01.07.2026–güncel",("Millî" if x["type"]=="national" else "Kulüp"),
                 numeric(x["games"]),numeric(x["stats_available"]),numeric(x["stats_missing"]),
                 "Kısmi" if int(x["stats_missing"]) else "Veri mevcut"] for x in coverage])
    book.worksheet("Veri Kapsamı").update(range_name=f"A1:G{len(cv)}",values=cv,value_input_option="RAW")
    book.worksheet("İşlem Günlüğü").append_row([
        datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(),"GOAL API / GitHub",
        "Tüm resmî maç toplamlarının yenilenmesi","Kısmi (API kapsamına göre)",
        f"Takip edilen oyuncu: {len(totals)}, turnuva satırı: {len(details)-1}"],value_input_option="RAW")
    print(f"GOOGLE_SHEETS_SYNCED: {len(totals)} candidate players, {len(details)-1} competition rows")
if __name__=="__main__":main()
