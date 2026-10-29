"""Probe supported official competitions (no key printed)."""
import os, json
from goal_api import GoalAPI
searches=("Super Cup","Youth League","U21 Championship","U19 Championship","Under-21","U20 World Cup","Champions","Europa","Conference","Nations")
with GoalAPI(os.environ["GOAL_API_KEY"],timeout=22,max_retries=0) as g:
  for text in searches:
    try:
      res=g.leagues.list(search=text,limit=100)
      items=res.get("data") or []
      print("COMPETITIONS",json.dumps({"query":text,"total":res.get("pagination",{}).get("total"),"list":[{"id":x.get("id"),"name":x.get("name"),"country":x.get("countryName"),"season":x.get("season"),"active":x.get("isActive")} for x in items]},ensure_ascii=False,separators=(",",":")))
    except Exception as err:
      print("COMP_ERROR",text,type(err).__name__,str(err)[:150])
