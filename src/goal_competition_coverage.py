"""Probe official competition completed fixtures in season window and sample player statistics."""
import os,json
from goal_api import GoalAPI
LEAGUES=[
("Türkiye Kupası","cmr77dw0q00eurx06c255xi6w","cup"),
("Şampiyonlar Ligi","cmr77dw3900f5rx06j05wgzv4","club"),
("Avrupa Ligi","cmr77dw3900f6rx06tuqwft2d","club"),
("Konferans Ligi","cmr77dw3900f9rx06laad8onf","club"),
("Uluslar Ligi","cmr77dw4800fgrx06rwmig2h8","national"),
("UEFA Dünya Kupası Elemeleri","cmr77dw3900f7rx06p5hrzt3h","national"),
("Dünya Kupası","cmr77dw4s00fmrx069yvhf8ce","national"),
("UEFA U21 Elemeleri","cmr77dvi9004orx06u3p565x4","national"),
("UEFA U19 Elemeleri","cmr77dw4800fjrx06pe28dd0b","national"),
("UEFA U17 Elemeleri","cmr77dvi9004mrx065nk08sup","national"),
("Afrika Uluslar Kupası Elemeleri","cmr77dvhg001srx060axumqos","national"),
("Asya Kupası Elemeleri","cmr77dvhg0027rx06g53djm8w","national"),
("2026 FIFA U17 Dünya Kupası","cmr77dw4s00frrx06072phd0g","national"),
("UEFA Avrupa Şampiyonası Eleme","cmr77dw4800ffrx06n12x8vzf","national"),
("AFC Dünya Kupası Elemeleri","cmr77dw4s00forx06xmv9cyt2","national"),
("CAF Dünya Kupası Elemeleri","cmr77dw4s00fprx06b0lzlakq","national"),
("CONMEBOL Dünya Kupası Elemeleri","cmr77dvmv006erx06bv7j5r71","national"),
]
with GoalAPI(os.environ["GOAL_API_KEY"],timeout=25,max_retries=0) as g:
 for name,lid,typ in LEAGUES:
  try:
   r=g.leagues.results(lid,**{"from":"2026-07-01","to":"2026-10-29","limit":100})
   games=r.get("data",[])
   count=r.get("pagination",{}).get("total")
   sample=[{"id":x.get("id"),"date":x.get("matchDate"),"league":x.get("leagueName"),"season":x.get("leagueYear"),"home":x.get("homeTeamName"),"away":x.get("awayTeamName"),"status":x.get("matchStatus")} for x in games[:2]]
   info={"competition":name,"type":typ,"id":lid,"total":count,"hasMore":r.get("pagination",{}).get("hasMore"),"examples":sample}
   if games:
    mid=games[0]["id"]
    try:
     d=g.fixtures.statistics(mid)["data"]
     block=d.get("players",{}) if isinstance(d,dict) else {}
     info["sample_player_counts"]={side:len(block.get(side,[]) or []) for side in ("home","away")} if isinstance(block,dict) else {"unexpected":type(block).__name__}
     info["sample_player_fields"]=list((block.get("home") or block.get("away") or [{}])[0].keys())[:15] if isinstance(block,dict) else []
    except Exception as e:info["sample_error"]=str(e)[:140]
   print("COMP_COUNT "+json.dumps(info,ensure_ascii=False,separators=(",",":")))
  except Exception as e:print("COMP_ERROR",name,type(e).__name__,str(e)[:200])
