#!/usr/bin/env python3
"""Collect public Google News RSS search results. News volume is not verified incident count."""
import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, datetime, email.utils, re
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
    out["categories"][key]={"status":"error" if error else "ok","error":error,"articles":entries,"count":len(entries),"count_is_sample":len(entries)>=100}
Path("data").mkdir(exist_ok=True)
Path("data/news.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("Collected", {k:v["count"] for k,v in out["categories"].items()})
