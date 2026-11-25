import json, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
JST=timezone(timedelta(hours=9))
URL="https://itunes.apple.com/jp/rss/topgrossingapplications/limit=100/genre=6014/json"
def read(p, default):
    p=Path(p)
    return json.loads(p.read_text()) if p.exists() else default
def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(v,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8"); tmp.replace(p)
def fetch():
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"H1G-iOS-Salesrank/1.0"}),timeout=30) as r:
                f=json.load(r)["feed"]
            rows=[]
            for n,e in enumerate(f["entry"],1):
                rows.append(dict(rank=n,appid=str(e["id"]["attributes"]["im:id"]),name=e["im:name"]["label"],artist=e["im:artist"]["label"],icon=e["im:image"][-1]["label"]))
            if len(rows)!=100 or len({r["appid"] for r in rows})!=100: raise ValueError("Incomplete ranking")
            return f["updated"]["label"],rows
        except Exception:
            if i==2: raise
            time.sleep(5*(i+1))
def main():
    source,rows=fetch()
    now=datetime.now(JST); stamp=now.isoformat(timespec="seconds")
    mapping=read("mapping.json",{})
    previous=read("data/latest.json",{})
    old={r["appid"]:r["rank"] for r in previous.get("ranking",[])}
    ranks={r["appid"]:r["rank"] for r in rows}
    for r in rows:
        r.update(previous_rank=old.get(r["appid"]),change=old[r["appid"]]-r["rank"] if r["appid"] in old else None,wiki=mapping.get(r["appid"]))
    for appid in sorted(set(mapping)|set(ranks)):
        p=f"data/apps/{appid}.json"; history=read(p,[])
        if not history or history[-1]["t"]!=stamp:
            history.append({"t":stamp,"rank":ranks.get(appid)})
        write(p,history)
        groups=defaultdict(list)
        for r in history:
            month=datetime.fromisoformat(r["t"]).astimezone(JST).strftime("%Y-%m")
            if month<now.strftime("%Y-%m"): groups[month].append(r["rank"])
        summaries=[]
        for month,values in sorted(groups.items()):
            ranked=[v for v in values if v is not None]
            summaries.append(dict(month=month,best=min(ranked) if ranked else None,average=round(sum(ranked)/len(ranked),2) if ranked else None,top100_rate=round(100*len(ranked)/len(values),2),samples=len(values),ranked_samples=len(ranked)))
        if summaries: write(f"data/monthly/{appid}.json",summaries)
    latest=dict(t=stamp,source_updated=source,ranking=rows)
    daily=Path(f"data/daily/{now.date()}.json")
    if not daily.exists(): write(daily,latest)
    write("data/latest.json",latest)
    print("Collected",len(rows),"apps; tracked",len(mapping))
if __name__=="__main__": main()
