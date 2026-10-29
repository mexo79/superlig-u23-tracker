"""One-shot verified 2026-27 Super Lig fixture-level player-stat export.
Prints public DATA_ROW JSON records to GitHub Actions logs for connector import.
No credentials are written or printed. No Google Sheets writes occur here.
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
import re
import unicodedata
from goal_api import GoalAPI

LEAGUE="cmr77dw0q00eprx06rqew3m48"

def n(v):
    if v is None or str(v).strip() in ("","N/A","null","None"):
        return None
    try:
        return float(v)
    except (TypeError,ValueError):
        return None

def normalized(name):
    s=str(name or "").replace("ı","i").replace("İ","i").lower()
    s=unicodedata.normalize("NFKD",s)
    return re.sub(r"[^a-z0-9]","", "".join(x for x in s if not unicodedata.combining(x)))

def main():
    now=datetime.now(timezone.utc)
    if not os.environ.get("GOAL_API_KEY"):
        raise RuntimeError("GOAL_API_KEY missing")
    with GoalAPI(os.environ["GOAL_API_KEY"],timeout=30,max_retries=1) as c:
        tr=c.leagues.teams(LEAGUE,season="2026/2027",limit=100)["data"]
        print("CLUB_SET "+json.dumps(sorted(t["name"] for t in tr),ensure_ascii=False))
        games=[]
        for offset in range(0,600,100):
            result=c.leagues.results(LEAGUE,**{"from":"2026-08-01","to":now.strftime("%Y-%m-%d"),"limit":100,"offset":offset})
            page=result.get("data",[])
            if not isinstance(page,list):
                raise RuntimeError("Unexpected league results page")
            games.extend(page)
            if not result.get("pagination",{}).get("hasMore"):
                break
        else:
            raise RuntimeError("Season fixture pagination exceeded 600 matches")
        games=[x for x in games if x.get("matchStatus") in ("FINISHED","AFTER_ET","AFTER_PEN") and x.get("leagueYear")=="2026/2027"]
        if len(games)<40:
            raise RuntimeError(f"Suspicious season coverage: {len(games)} fixtures")
        print(f"SEASON_GAMES {len(games)}")
        unique=set()
        people={}
        loaded=0
        errors=0
        for idx,g in enumerate(games,1):
            mid=str(g["id"])
            try:
                data=c.fixtures.statistics(mid)["data"]
                both=data.get("players",{})
                if not isinstance(both,dict):
                    raise ValueError("No players block")
                read_any=0
                for side in ("home","away"):
                    club=g.get("homeTeamName") if side=="home" else g.get("awayTeamName")
                    for p in both.get(side,[]) or []:
                        if not isinstance(p,dict):
                            continue
                        mins=n(p.get("minutesPlayed"))
                        if mins is None or mins<=0:
                            continue
                        pid=str(p.get("playerKey") or p.get("playerId") or "")
                        if not pid:
                            continue
                        nested=p.get("player") or {}
                        internal_id=str(nested.get("id") or "")
                        name=str(p.get("playerName") or nested.get("name") or "").strip()
                        if not name:
                            continue
                        key=(pid,normalized(club))
                        if (mid,key) in unique:
                            continue
                        unique.add((mid,key))
                        q=people.setdefault(key,{"api_id":pid,"internal_id":internal_id,"name":name,"club":club,"minutes":0,"games":0,"starts":0,"ratings":[],"goals":0,"assists":0,"yellow":0,"red":0,"null_fields":set(),"match_ids":[]})
                        q["games"]+=1
                        q["minutes"]+=int(mins)
                        q["starts"]+=int(p.get("isSubstitute") is False)
                        r=n(p.get("rating"))
                        if r and r>0:q["ratings"].append(r)
                        for field,raw in (("goals","goals"),("assists","assists"),("yellow","yellowCards"),("red","redCards")):
                            v=n(p.get(raw))
                            if v is None:
                                q["null_fields"].add(field)
                            else:
                                q[field]+=int(v)
                        q["match_ids"].append(mid)
                        read_any+=1
                if read_any<10:raise ValueError("Insufficient usable player rows")
                loaded+=1
            except Exception as err:
                errors+=1
                print(f"MATCH_ERROR {mid}: {type(err).__name__} {str(err)[:120]}")
            if idx%12==0:print(f"PROGRESS {idx}/{len(games)} good={loaded} bad={errors}")
        print(f"MATCH_COVERAGE {loaded}/{len(games)} ERRORS {errors} PLAYERS {len(people)}")
        if loaded<len(games)*.9:
            raise RuntimeError("Incomplete dataset: refuse exporting partial season")
        for q in sorted(people.values(),key=lambda v:(normalized(v["club"]),normalized(v["name"]))):
            q["rating"]=round(sum(q["ratings"])/len(q["ratings"]),2) if q["ratings"] else None
            q["rating_sample"]=len(q.pop("ratings"))
            q["null_fields"]=sorted(q["null_fields"])
            q["match_count"]=len(q.pop("match_ids"))
            print("DATA_ROW "+json.dumps(q,ensure_ascii=False,separators=(",",":")))
        print("EXPORT_COMPLETE "+json.dumps({"games":len(games),"loaded":loaded,"players":len(people),"timestamp":now.isoformat()}))

if __name__=="__main__":
    main()
