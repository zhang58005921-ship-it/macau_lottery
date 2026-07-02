import json
from collections import Counter

data_file = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\macaujc_data.json"
with open(data_file, "r", encoding="utf-8") as f:
    data = json.load(f)

_LNY = {"2022-02-01":"虎","2023-01-22":"兔","2024-02-10":"龍","2025-01-29":"蛇","2026-02-17":"馬"}
ZM = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]

def yz(d):
    if not d or len(d)<10: return "?"
    z="馬"
    for dt,z2 in sorted(_LNY.items()):
        if d[:10]>=dt: z=z2
    return z

# Sample records
print("=== SAMPLE RECORDS ===")
for i in [0, 50, 200, 400, 600, 800, 910]:
    if i >= len(data): continue
    r = data[i]
    dt = r.get("openTime","")
    code = r.get("openCode","")
    dz = r.get("zodiac","")
    nums = [int(x) for x in code.split(",") if x.strip()] if code else []
    yr_z = yz(dt)
    zi = ZM.index(yr_z)
    our_zods = [ZM[(zi+(n-1))%12] for n in nums]
    print(f"#{r.get('expect','?')} {dt[:10]} year={yr_z}")
    print(f"  nums={nums}")
    print(f"  data_zod={dz}")
    print(f"  our_zod={our_zods}")
    if dz:
        data_zods = [z.strip() for z in dz.split(",")]
        match = [1 if our_zods[j]==data_zods[j] else 0 for j in range(min(7,len(data_zods)))]
        print(f"  match={match} ({sum(match)}/7)")
    print()

# Year distribution
yc = Counter()
for r in data:
    yc[yz(r.get("openTime",""))] += 1
print("Zodiac year distribution:")
for k in ["虎","兔","龍","蛇","馬"]:
    c = yc.get(k,0)
    if c > 0:
        yr_data = [r for r in data if yz(r.get("openTime",""))==k]
        dates = sorted([r.get("openTime","")[:10] for r in yr_data if r.get("openTime","")])
        print(f"  {k}年: {c}期, {dates[0] if dates else '?'} ~ {dates[-1] if dates else '?'}")

# Root cause: does data use Jan 1 as zodiac year boundary?
print()
print("=== ZODIAC BOUNDARY CHECK ===")
for r in data:
    dt = r.get("openTime","")
    if dt and "2024-01" <= dt[:10] <= "2024-02-15":
        code = r.get("openCode","")
        dz = r.get("zodiac","")
        nums = [int(x) for x in code.split(",") if x.strip()] if code else []
        # Our calc: rabbit year
        zi_rabbit = ZM.index("兔")
        our_rabbit = [ZM[(zi_rabbit+(n-1))%12] for n in nums]
        # Alt: dragon year (Jan 1 boundary)
        zi_dragon = ZM.index("龍")
        alt_dragon = [ZM[(zi_dragon+(n-1))%12] for n in nums]
        data_zods = [z.strip() for z in dz.split(",")] if dz else []
        match_rabbit = sum(1 for j in range(min(7,len(data_zods))) if our_rabbit[j]==data_zods[j])
        match_dragon = sum(1 for j in range(min(7,len(data_zods))) if alt_dragon[j]==data_zods[j])
        print(f"  #{r.get('expect')} {dt[:10]}: match(rabbit)={match_rabbit}/7 match(dragon)={match_dragon}/7")
        if match_rabbit > match_dragon:
            print(f"    -> Data uses RABBIT year (matches our mapping)")
        else:
            print(f"    -> Data uses DRAGON year (Jan 1 boundary, NOT lunar)")
        break
