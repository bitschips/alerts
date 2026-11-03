#!/usr/bin/env python3
"""Collect public Google News RSS search results. News volume is not verified incident count."""
import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, datetime, email.utils, re, unicodedata
from pathlib import Path
QUERIES={
 "accident":'"train crash" OR "plane crash" OR "major accident" OR "accidente ferroviario" OR "accidente grave"',
 "civil":'"civil protection" OR "evacuation order" OR "alerta protección civil"',
 "terror":'"terror attack" OR "ataque terrorista"',
 "nuclear":'"nuclear emergency" OR "nuclear threat" OR "amenaza nuclear"',
 "nato":'NATO threat OR "ataque OTAN"',
 "cyber":'"cyberattack" OR "ciberataque"',
 "weather":'"severe weather warning" OR "alerta meteorológica"'
}

STOPWORDS=set("""the a an and or of in on at to for from with after as is are was were has have had by about latest breaking news update live report reports says say what know how why this that these those amid near over into de del la las los el en un una y por para con tras sobre que se al lo su sus new deadly killed kills death deaths people officials official at least more than""".split())
TYPES={
 "air":r"\\b(plane|aircraft|airplane|aviation|jet|avion|aereo)\\b",
 "rail":r"\\b(train|rail|railway|tren|ferroviario)\\b",
 "flood":r"\\b(flood|flooding|inundacion)\\b",
 "quake":r"\\b(earthquake|terremoto|sismo)\\b",
 "fire":r"\\b(fire|wildfire|incendio)\\b",
 "cyber":r"\\b(ransomware|cyberattack|ciberataque|hack)\\b",
}
def title_words(title):
    title=unicodedata.normalize("NFKD",title.lower())
    title="".join(c for c in title if not unicodedata.combining(c))
    title=re.sub(r"\\s+[-–|]\\s+[^–|]+$","",title)
    words=re.findall(r"[a-z0-9]+",title)
    return {w for w in words if len(w)>2 and w not in STOPWORDS and not w.isdigit()}

def event_type(title):
    t=" ".join(title_words(title))
    return next((name for name,pattern in TYPES.items() if re.search(pattern,t)),"")

def deduplicate(entries):
    """Conserva un representante por suceso probable; evita unir noticias de días distintos."""
    groups=[]
    for entry in entries:
        words=title_words(entry["title"])
        kind=event_type(entry["title"])
        when=datetime.datetime.fromisoformat(entry["published"])
        match=None
        for group in groups:
            if kind and group["kind"] and kind!=group["kind"]: continue
            if abs((when-group["when"]).total_seconds())>72*3600: continue
            other=group["words"]
            overlap=len(words & other)
            similarity=overlap/min(len(words),len(other)) if words and other else 0
            # Exige varios términos comunes: no basta con "plane crash".
            if overlap>=3 and similarity>=0.72:
                match=group
                break
        if match:
            match["article"]["related_articles"]+=1
            source=entry["source"]
            if source not in match["article"]["sources"]:
                match["article"]["sources"].append(source)
        else:
            article=dict(entry,related_articles=1,sources=[entry["source"]])
            groups.append({"article":article,"words":words,"kind":kind,"when":when})
    return [g["article"] for g in groups]

now=datetime.datetime.now(datetime.timezone.utc)
out={"updated_at":now.isoformat(),"source":"Google News RSS search","window_hours":24,"categories":{}}
for key,q in QUERIES.items():
    entries=[];error=None
    try:
        url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q+" when:1d","hl":"en","gl":"US","ceid":"US:en"})
        req=urllib.request.Request(url,headers={"User-Agent":"AlertsObservatory/0.1 (+https://github.com/bitschips/alerts)"})
        with urllib.request.urlopen(req,timeout=25) as resp: root=ET.fromstring(resp.read(1500000))
        for item in root.findall(".//channel/item"):
            title=item.findtext("title","").strip()
            link=item.findtext("link","").strip()
            pub=item.findtext("pubDate","")
            try: dt=email.utils.parsedate_to_datetime(pub).astimezone(datetime.timezone.utc)
            except Exception: continue
            if dt<now-datetime.timedelta(hours=24) or not link or not title: continue
            source=item.find("source")
            entries.append({"title":title[:350],"url":link,"published":dt.isoformat(),"source":source.text if source is not None else "Google News"})
        entries=entries[:100]
    except Exception as exc: error=str(exc)[:200]
    raw_count=len(entries)
    entries=deduplicate(entries)
    out["categories"][key]={"status":"error" if error else "ok","error":error,"articles":entries,"count":len(entries),"raw_article_count":raw_count,"count_is_sample":raw_count>=100}
Path("data").mkdir(exist_ok=True)
Path("data/news.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("Collected", {k:v["count"] for k,v in out["categories"].items()})
