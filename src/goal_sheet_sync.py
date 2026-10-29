"""Nightly GOAL API -> existing Google Sheets import, preserving TFF information.
Requires: GOAL_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SHEET_ID.
"""
from contextlib import redirect_stdout
from datetime import datetime
from difflib import SequenceMatcher
from io import StringIO
import json
import os
import unicodedata
import re
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

import goal_season_export

TABS=("Tüm U23","U23 Yabancı","U23 Türk")
REQUIRED=("GOAL_API_KEY","GOOGLE_SERVICE_ACCOUNT_JSON","GOOGLE_SHEET_ID")

def norm(v):
    s=str(v or "").replace("ı","i").replace("İ","i").lower()
    s=unicodedata.normalize("NFKD",s)
    return re.sub(r"[^a-z0-9]","", "".join(c for c in s if not unicodedata.combining(c)))

def club(v):
    v=norm(v)
    return {"istanbulbasaksehir":"basaksehir","corumfk":"corum",
            "erzurumsporfk":"erzurumspor","amedspor":"amed",
            "caykurrizespor":"rizespor"}.get(v,v)

def name_tokens(v):
    s=str(v or "").replace("ı","i").replace("İ","i").lower()
    s=unicodedata.normalize("NFKD",s)
    return [norm(x) for x in re.split(r"[\s-]+",s) if norm(x)]

def identify(name,team,people):
    arr=people.get(club(team),[])
    target=norm(name)
    exact=[p for p in arr if norm(p["name"])==target]
    if len(exact)==1:
        return exact[0]
    if exact:
        return None
    ts=name_tokens(name)
    aliases=[]
    for p in arr:
        pn=norm(p["name"])
        tokens=name_tokens(p["name"])
        if len(target)>=4 and (pn.startswith(target) or pn.endswith(target)):
            aliases.append(p)
        elif len(ts)>=2 and all(t in tokens for t in ts):
            aliases.append(p)
    return aliases[0] if len(aliases)==1 else None

def live_export():
    capture=StringIO()
    with redirect_stdout(capture):
        goal_season_export.main()
    output=capture.getvalue()
    rows=[]; finished=None
    for line in output.splitlines():
        if line.startswith("DATA_ROW "):
            rows.append(json.loads(line.removeprefix("DATA_ROW ")))
        elif line.startswith("EXPORT_COMPLETE "):
            finished=json.loads(line.removeprefix("EXPORT_COMPLETE "))
    if not finished or finished.get("loaded",0)<70 or len(rows)<300:
        raise RuntimeError("Incomplete GOAL API season data; no spreadsheet edits")
    return rows,finished

def main():
    missing=[k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError("Missing required credentials: "+", ".join(missing))
    creds=Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    book=gspread.authorize(creds).open_by_key(os.environ["GOOGLE_SHEET_ID"])
    # Read all input lists BEFORE making network calls or edits.
    original={}
    for tab in TABS:
        ws=book.worksheet(tab)
        vals=ws.get_all_values()
        if len(vals)<2 or len(vals[0])<21 or vals[0][1]!="Oyuncu" or vals[0][20]!="Yerli / Yabancı":
            raise RuntimeError("Unexpected spreadsheet schema in "+tab)
        original[tab]=(ws,vals)
    players,meta=live_export()
    groups={}
    for p in players:
        groups.setdefault(club(p["club"]),[]).append(p)
    changes={}
    now=datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M TRT")
    for tab,(ws,vals) in original.items():
        entries=[]
        matched=0
        for source in vals[1:]:
            if len(source)<2 or not source[1]:
                continue
            r=(source+[""]*21)[:21]
            p=identify(r[1],r[2],groups)
            if p:
                matched+=1
                r[0]=str(p["api_id"])
                for i,key in enumerate(("minutes","games","starts","rating","goals","assists","yellow","red")):
                    val=p.get(key)
                    if key=="rating" and not p.get("rating_sample"):
                        val=None
                    if key in p.get("null_fields",()):
                        val=None
                    r[i+5]=val if val is not None else ""
                r[15]=now
                r[19]=("GOAL API - Süper Lig 2026/27, "+
                       str(meta["loaded"])+"/"+str(meta["games"])+" maç"+
                       (" (reyting kısmi)" if p.get("rating_sample",0)<p["games"] else ""))
            # An absent player is NOT assumed to have zero appearances.
            entries.append(r)
        entries.sort(key=lambda x:(-(float(x[5]) if str(x[5]).replace(".","",1).isdigit() else -1),norm(x[1])))
        changes[tab]={"ws":ws,"rows":entries,"matched":matched}
    if changes["Tüm U23"]["matched"]<60:
        raise RuntimeError("Too few reliable player matches; no spreadsheet edits")
    # No data mutation until every input/output has been validated.
    for tab,c in changes.items():
        records=c["rows"]
        c["ws"].update(range_name="A2:U"+str(len(records)+1),
                        values=records,value_input_option="RAW")
    stamp=datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M TRT")
    book.worksheet("İşlem Günlüğü").append_row(
        [stamp,"GOAL API","2026-27 Süper Lig performans güncellemesi","Kısmi" if meta["loaded"]<meta["games"] else "Başarılı",
         f"Maç {meta['loaded']}/{meta['games']}; eşleşen oyuncu {changes['Tüm U23']['matched']}; yabancı {changes['U23 Yabancı']['matched']}; yerli {changes['U23 Türk']['matched']}"],
        value_input_option="RAW")
    print(f"Completed: {meta['loaded']}/{meta['games']} fixtures; {changes['Tüm U23']['matched']} U23 candidates updated.")

if __name__=="__main__":
    main()
