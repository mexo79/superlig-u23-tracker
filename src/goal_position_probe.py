"""Read GOAL API club roster positions and 2026/27 starting lineup tactical slots."""
import json, os, collections
from goal_api import GoalAPI
ID="cmr77dw0q00eprx06rqew3m48"
with GoalAPI(os.environ["GOAL_API_KEY"],timeout=25,max_retries=1) as api:
    teams=api.leagues.teams(ID,season="2026/2027",limit=100)["data"]
    print("TEAMS_FOUND",len(teams))
    players={}
    team_counts={}
    for t in teams:
        name=t["name"]
        page=api.teams.players(t["id"],limit=100)
        arr=page.get("data",[])
        print("CLUB_ROSTER",json.dumps({"club":name,"rows":len(arr),"example":arr[:1]},ensure_ascii=False)[:1800])
        team_counts[name]=len(arr)
        for p in arr:
            row={"id":str(p.get("id") or ""),"apiId":str(p.get("apiId") or ""),"name":p.get("name"),"club":name,"type":p.get("type"),"slots":[],"formations":[]}
            if row["id"] or row["apiId"]:
                players[(name,row["id"] or row["apiId"])]=row
    res=api.leagues.results(ID,**{"from":"2026-08-01","to":"2026-10-29","limit":100})
    games=res["data"];print("RESULTS",len(games))
    lineup_ok=0
    for m in games:
        try:
            d=api.fixtures.lineups(m["id"]).get("data",{})
            found=0
            for side in ("home","away"):
                block=d.get(side) or {}
                club=m.get("homeTeamName") if side=="home" else m.get("awayTeamName")
                formation=m.get("homeTeamSystem") if side=="home" else m.get("awayTeamSystem")
                starts=block.get("startingLineups") or []
                if not isinstance(starts,list):continue
                for entry in starts:
                    pid=str(entry.get("playerId") or "")
                    name=entry.get("lineupPlayer")
                    slot=entry.get("lineupPosition")
                    if not pid:continue
                    for obj in players.values():
                        if obj["id"]==pid:
                            obj["slots"].append(slot);obj["formations"].append(formation)
                            found+=1;break
            if found:lineup_ok+=1
        except Exception as err:
            print("LINEUP_WARN",m.get("id"),type(err).__name__,str(err)[:75])
    print("LINEUPS_READ",lineup_ok)
    for p in players.values():
        pairs=collections.Counter(zip(p.pop("slots"),p.pop("formations")))
        p["tactics"]=[[slot,formation,num] for (slot,formation),num in pairs.most_common()]
        print("POSITION_ROW",json.dumps(p,ensure_ascii=False,separators=(",",":")))
    print("POSITION_EXPORT_DONE",json.dumps({"teams":len(teams),"players":len(players),"games":len(games),"lineup_games":lineup_ok}))
