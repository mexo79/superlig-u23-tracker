"""2026/27 official non-league match player statistics, GOAL API.
Exclude friendlies, preseason and exhibition fixtures.
Match-level rows aggregated per stable player API key and competition.
"""
from datetime import datetime, timezone
from collections import defaultdict
import json, os, re, unicodedata
from goal_api import GoalAPI

WINDOW_FROM = "2026-07-01"
LEAGUES=[
 ("Türkiye Kupası","cmr77dw0q00eurx06c255xi6w","club"),
 ("Şampiyonlar Ligi","cmr77dw3900f5rx06j05wgzv4","club"),
 ("Avrupa Ligi","cmr77dw3900f6rx06tuqwft2d","club"),
 ("Konferans Ligi","cmr77dw3900f9rx06laad8onf","club"),
 ("UEFA Uluslar Ligi","cmr77dw4800fgrx06rwmig2h8","national"),
 ("2026 Dünya Kupası","cmr77dw4s00fmrx069yvhf8ce","national"),
 ("Afrika Uluslar Kupası Elemeleri","cmr77dvhg001srx060axumqos","national"),
 ("UEFA U21 Elemeleri","cmr77dvi9004orx06u3p565x4","national"),
 ("UEFA U19 Elemeleri","cmr77dw4800fjrx06pe28dd0b","national"),
 ("UEFA U17 Elemeleri","cmr77dvi9004mrx065nk08sup","national"),
 ("UEFA Dünya Kupası Elemeleri","cmr77dw3900f7rx06p5hrzt3h","national"),
 ("2027 Avrupa Şampiyonası Elemeleri","cmr77dw4800ffrx06n12x8vzf","national"),
 ("Afrika Dünya Kupası Elemeleri","cmr77dw4s00fprx06b0lzlakq","national"),
 ("Asya Dünya Kupası Elemeleri","cmr77dw4s00forx06xmv9cyt2","national"),
 ("Güney Amerika Dünya Kupası Elemeleri","cmr77dvmv006erx06bv7j5r71","national"),
 ("Kuzey Amerika Dünya Kupası Elemeleri","cmr77dw4s00fqrx0685wnnxun","national"),
 ("Asya Kupası Elemeleri","cmr77dvhg0027rx06g53djm8w","national"),
 ("2026 FIFA U17 Dünya Kupası","cmr77dw4s00frrx06072phd0g","national"),
 ("FIFA U20 Dünya Kupası","cmr77dw4s00fsrx06b9i3064z","national"),
 ("UEFA U19 Şampiyonası","cmr77dw3900farx06cjgu8fbb","national"),
 ("Afrika U20 Uluslar Kupası","cmr77dvhg001trx06zhcl84in","national"),
 ("Afrika U23 Uluslar Kupası","cmr77dvhg002erx06yvrv81x9","national"),
 ("Türkiye Süper Kupa","cmr77dw0q00evrx06wu2978jk","club"),
 ("UEFA Süper Kupa","cmr77dw4800fhrx065oy5co7g","club"),
 ("UEFA Gençlik Ligi","cmr77dw4800fkrx061y0e0vxw","youthclub"),
]
CLUBS={
 "fenerbahce","istanbulbasaksehir","basaksehir","alanyaspor",
 "besiktas","genclerbirligi","gaziantepfk","kocaelispor","galatasaray",
 "erzurumsporfk","erzurumspor","amed","amedspor","kasimpasa","goztepe",
 "corum","corumfk","trabzonspor","eyupspor","rizespor","samsunspor",
 "konyaspor"
}
END=datetime.now(timezone.utc).strftime("%Y-%m-%d")
def norm(s):
 s=str(s or "").replace("ı","i").replace("İ","i").lower()
 s=unicodedata.normalize("NFKD",s)
 return re.sub(r"[^a-z0-9]","", "".join(c for c in s if not unicodedata.combining(c)))
def f(v):
 try:
  if v is None or str(v).strip() in ("","N/A"):return None
  return float(v)
 except (ValueError,TypeError):return None
def paged_results(c,lid):
 rows=[]
 for off in range(0,1000,100):
  response=c.leagues.results(lid,**{"from":WINDOW_FROM,"to":END,"limit":100,"offset":off})
  batch=response.get("data",[])
  if not isinstance(batch,list):raise RuntimeError("Unexpected results list")
  rows.extend(batch)
  if not response.get("pagination",{}).get("hasMore"):return rows
 raise RuntimeError("Result pagination > 1000: refused")
def main():
 if not os.getenv("GOAL_API_KEY"):raise RuntimeError("Missing GOAL_API_KEY")
 processed,failures=[],[]
 agg={}
 summary={}
 with GoalAPI(os.environ["GOAL_API_KEY"],timeout=25,max_retries=1) as c:
  for name,lid,category in LEAGUES:
   games=paged_results(c,lid)
   games=[g for g in games if g.get("matchStatus") in ("FINISHED","AFTER_ET","AFTER_PEN") and not any(x in norm(g.get("leagueName")) for x in ["friendly","preseason","exhibition","testmatch"])]
   if category in ("club","youthclub"):
    def is_turkish_club(team_name):
     slug=norm(team_name)
     if category=="youthclub":
      for end in ("u19","u21","u17","youth"):
       if slug.endswith(end):slug=slug[:-len(end)]
     return slug in CLUBS
    games=[g for g in games if is_turkish_club(g.get("homeTeamName")) or is_turkish_club(g.get("awayTeamName"))]
   attempted=0;good=0;incomplete=0
   for game in games:
    attempted+=1
    try:
     result=c.fixtures.statistics(game["id"]).get("data",{})
     both=result.get("players",{})
     if not isinstance(both,dict):raise ValueError("Missing players")
     usable=0
     for side in ("home","away"):
      club=game.get("homeTeamName") if side=="home" else game.get("awayTeamName")
      if category in ("club","youthclub") and not is_turkish_club(club):continue
      for p in both.get(side,[]) or []:
       minutes=f(p.get("minutesPlayed"))
       if minutes is None or minutes<=0:continue
       pid=str(p.get("playerKey") or p.get("playerId") or "")
       if not pid:continue
       usable+=1
       key=(pid,name,club)
       a=agg.setdefault(key,{"api_id":pid,"name":p.get("playerName") or "",
        "club_or_country":club,"competition":name,"category":category,
        "games":0,"starts":0,"minutes":0,"ratings":[],"goals":0,
        "assists":0,"yellow":0,"red":0,"unknown_fields":set(),"fixture_ids":[]})
       # Dedup per player, competition and fixture
       if game["id"] in a["fixture_ids"]:continue
       a["fixture_ids"].append(game["id"]);a["games"]+=1;a["minutes"]+=int(minutes)
       if p.get("isSubstitute") is False:a["starts"]+=1
       rating=f(p.get("rating"))
       if rating is not None and rating>0:a["ratings"].append(rating)
       for field,actual in (("goals","goals"),("assists","assists"),("yellow","yellowCards"),("red","redCards")):
        val=f(p.get(actual))
        if val is None:a["unknown_fields"].add(field)
        else:a[field]+=int(val)
     if usable<3:
      incomplete+=1
      raise ValueError("Insufficient player data")
     good+=1
     processed.append({"id":game["id"],"name":name,"class":category,"date":game.get("matchDate"),"home":game.get("homeTeamName"),"away":game.get("awayTeamName"),"players":usable})
    except Exception as e:
     failures.append({"fixture":game.get("id"),"competition":name,"error":str(e)[:100]})
   summary[name]={"fixtures":len(games),"loaded":good,"failed":len(games)-good,"type":category}
   print("COMP_SUMMARY "+json.dumps({"name":name,**summary[name]},ensure_ascii=False))
   if c.rate_limit.remaining is not None:print("RATE_LIMIT_REMAINING",c.rate_limit.remaining)
  for x in agg.values():
   x["rating"]=round(sum(x["ratings"])/len(x["ratings"]),2) if x["ratings"] else None
   x["rating_count"]=len(x.pop("ratings"))
   x["unknown_fields"]=sorted(x["unknown_fields"])
   x["fixture_count"]=len(x.pop("fixture_ids"))
   print("OFFICIAL_ROW "+json.dumps(x,ensure_ascii=False,separators=(",",":")))
  for x in processed:print("FIXTURE_ROW "+json.dumps(x,ensure_ascii=False,separators=(",",":")))
  for x in failures:print("ERROR_ROW "+json.dumps(x,ensure_ascii=False,separators=(",",":")))
  print("OFFICIAL_EXPORT_COMPLETE "+json.dumps({"stats_rows":len(agg),"fixtures":len(processed),"errors":len(failures),"summary":summary,"date":END},ensure_ascii=False))
if __name__=="__main__":main()
