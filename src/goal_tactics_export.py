"""Aggregate tactical positions across current-season fixtures for every player in starting lineups."""
import json, os, collections
from goal_api import GoalAPI
ID="cmr77dw0q00eprx06rqew3m48"
with GoalAPI(os.environ["GOAL_API_KEY"],timeout=30,max_retries=1) as api:
  g=api.leagues.results(ID,**{"from":"2026-08-01","to":"2026-10-29","limit":100})["data"]
  bykey={}
  errors=[]
  for fixture in g:
    try:
      d=api.fixtures.lineups(fixture["id"])["data"]
      for side in ("home","away"):
        block=d.get(side) or {}
        club=fixture.get("homeTeamName") if side=="home" else fixture.get("awayTeamName")
        formation=fixture.get("homeTeamSystem") if side=="home" else fixture.get("awayTeamSystem")
        for entry in block.get("startingLineups") or []:
          pid=str(entry.get("playerKey") or "")
          if not pid:continue
          key=(pid,club)
          obj=bykey.setdefault(key,{"key":pid,"club":club,"name":entry.get("lineupPlayer"),"position":entry.get("playerPosition"),"tactics":collections.Counter()})
          if not obj["position"]:obj["position"]=entry.get("playerPosition")
          slot=entry.get("lineupPosition")
          if str(slot).isdigit() and int(slot)>=1 and formation:
            obj["tactics"][(str(slot),formation)]+=1
    except Exception as e:
      errors.append((fixture["id"],str(e)[:90]))
  for q in bykey.values():
    q["tactics"]=[[a,b,count] for (a,b),count in q["tactics"].most_common()]
    print("TACTIC_ROW",json.dumps(q,ensure_ascii=False,separators=(",",":")))
  print("TACTIC_EXPORT_DONE",json.dumps({"fixtures":len(g),"players":len(bykey),"errors":errors[:10]},ensure_ascii=False))
