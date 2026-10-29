"""Publish all available official 2026/27 competition statistics as CSV files.

Free-plan friendly: reuses GOAL API's official Python SDK; GitHub Actions commits
the resulting public CSV. Sheets can IMPORTDATA after the owner approves the
external URL once. Does not require a Google service-account JSON key.
"""
import csv
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
import json
import os
from pathlib import Path
import re
import unicodedata
from zoneinfo import ZoneInfo

import goal_season_export
import goal_all_official_export

BASE=Path(__file__).resolve().parents[1]
PLAYERS=BASE/"data"/"players.json"
TOTALS=BASE/"data"/"official_totals.csv"
DETAIL=BASE/"data"/"competitions.csv"
COVERAGE=BASE/"data"/"coverage.csv"
START="2026-07-01"
KEYS=("minutes","games","starts","rating","goals","assists","yellow","red")

def norm(v):
    v=str(v or "").replace("ı","i").replace("İ","i").lower()
    v=unicodedata.normalize("NFKD",v)
    return re.sub(r"[^a-z0-9]","", "".join(ch for ch in v if not unicodedata.combining(ch)))

def club(v):
    s=norm(v)
    return {"basaksehir":"istanbulbasaksehir","corumfk":"corum",
            "erzurumspor":"erzurumsporfk","amedspor":"amed"}.get(s,s)

def collect(method,prefixes):
    buffer=StringIO()
    with redirect_stdout(buffer):
        method()
    parsed={p:[] for p in prefixes}
    for line in buffer.getvalue().splitlines():
        for p in prefixes:
            if line.startswith(p+" "):
                parsed[p].append(json.loads(line[len(p)+1:]))
    return parsed

def fl(v):
    if v is None or v=="" or v=="N/A":return None
    try:return float(str(v).replace(",","."))
    except (TypeError,ValueError):return None

def csvwrite(path,header,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def match_player(player,byid,byname):
    pid=str(player.get("api_id") or "")
    if pid and pid in byid:return byid[pid]
    # Strong exact name + current club match only, never ambiguous fuzzy IDs
    q=(norm(player["name"]),club(player["club"]))
    matches=byname.get(q,[])
    return matches[0] if len(matches)==1 else None

def merge(p, lg, extras):
    if not lg and not extras:
        return [""]*8
    out=[]
    for field in KEYS:
        if field=="rating":
            samples=[]
            if lg and fl(lg.get("rating")) is not None and lg.get("rating_sample",0):
                samples.append((fl(lg["rating"]),int(lg["rating_sample"])))
            samples.extend((fl(x["rating"]),int(x["rating_count"])) for x in extras
                           if fl(x.get("rating")) is not None and x.get("rating_count"))
            if samples:
                out.append(round(sum(v*n for v,n in samples)/sum(n for _,n in samples),2))
            else:out.append("")
            continue
        source=[lg] if lg else []
        source+=extras
        # Null in any participating source means incomplete for that metric.
        if any(field in x.get("null_fields",x.get("unknown_fields",[])) for x in source):
            out.append("")
            continue
        numbers=[fl(x.get(field)) for x in source]
        if not numbers or all(v is None for v in numbers):
            out.append("")
        else:
            out.append(int(sum(v for v in numbers if v is not None)))
    return out

def main():
    if not os.getenv("GOAL_API_KEY"):
        raise RuntimeError("GOAL_API_KEY not configured; unchanged data retained.")
    with open(PLAYERS,encoding="utf-8") as f:
        roster=json.load(f)["players"]
    if len(roster)<200:raise RuntimeError("Roster unexpectedly small")
    le=collect(goal_season_export.main,("DATA_ROW","EXPORT_COMPLETE"))
    me=collect(goal_all_official_export.main,("OFFICIAL_ROW","OFFICIAL_EXPORT_COMPLETE"))
    lg=le["DATA_ROW"]
    meta=le["EXPORT_COMPLETE"][-1] if le["EXPORT_COMPLETE"] else None
    official=me["OFFICIAL_ROW"]
    ometa=me["OFFICIAL_EXPORT_COMPLETE"][-1] if me["OFFICIAL_EXPORT_COMPLETE"] else None
    if not meta or not ometa or len(lg)<300 or meta.get("loaded",0)<70 or len(official)<1000:
        raise RuntimeError("Unreliable GOAL API coverage; CSV files left untouched.")
    by_league_id={str(p["api_id"]):p for p in lg}
    by_name={}
    for p in lg:
        by_name.setdefault((norm(p["name"]),club(p["club"])),[]).append(p)
    by_official_id={}
    for q in official:
        by_official_id.setdefault(str(q["api_id"]),[]).append(q)
    stamp=datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d %H:%M TRT")
    total_rows=[]
    comp_rows=[]
    extras_found=0
    for row in roster:
        lgrow=match_player(row,by_league_id,by_name)
        pid=str(row.get("api_id") or "")
        if not pid and lgrow:pid=str(lgrow["api_id"])
        extras=by_official_id.get(pid,[]) if pid else []
        extras_found+=int(bool(extras))
        metrics=merge(row,lgrow,extras)
        key=row["name"]+"|"+row["club"]
        safe_metrics=[("N/A" if v == "" else (int(round(v * 100)) if i == 3 else v)) for i,v in enumerate(metrics)]
        total_rows.append([key,pid,*safe_metrics,stamp])
        if lgrow:
            line=[key,pid,row["name"],row["club"],"Süper Lig",row["club"],"Kulüp",*[
                lgrow.get(k) if k not in lgrow.get("null_fields",[]) else "" for k in KEYS],
                f"{meta['loaded']}/{meta['games']} maç (kısmi)"]
            comp_rows.append(line)
        for q in extras:
            comp_rows.append([key,pid,row["name"],row["club"],q["competition"],
                             q["club_or_country"],"Millî takım" if q["category"]=="national" else "Kulüp",
                             *[q.get(k) if k not in q.get("unknown_fields",[]) else "" for k in KEYS],
                             "GOAL API — veri bulunan maçlar"])
    if extras_found<15:
        raise RuntimeError("Suspicious external-competition player coverage; previous CSV retained")
    csvwrite(TOTALS,["key","api_id","minutes","matches","starts","rating_x100","goals","assists","yellow","red","updated_at"],total_rows)
    csvwrite(DETAIL,["key","api_id","player","club","competition","club_or_national_team","category",
                     "minutes","matches","starts","rating","goals","assists","yellow","red","coverage"],comp_rows)
    stats=[("Süper Lig",meta["games"],meta["loaded"],"Kulüp")]
    stats.extend((name,c["fixtures"],c["loaded"],c["type"]) for name,c in ometa["summary"].items())
    csvwrite(COVERAGE,["competition","games","stats_available","stats_missing","type","updated_at"],
             [[name,total,ok,total-ok,typ,stamp] for name,total,ok,typ in stats])
    print(f"Updated public CSV for {len(roster)} players, {extras_found} with other official competitions; Süper Lig {meta['loaded']}/{meta['games']}.")
    if ometa["errors"]:
        print(f"WARNING: {ometa['errors']} official fixtures unavailable; totals are partial.")
if __name__=="__main__":main()
