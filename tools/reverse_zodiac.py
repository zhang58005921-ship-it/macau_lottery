"""Reverse-engineer Macau lottery zodiac mapping from data"""
import json
from collections import Counter, defaultdict

data_file = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\macaujc_data.json"
with open(data_file, "r", encoding="utf-8") as f:
    data = json.load(f)

ZODIAC_MAP = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]

# For each zodiac year, build number->zodiac mapping from data
year_mappings = defaultdict(lambda: defaultdict(Counter))

for r in data:
    dt = r.get("openTime","")
    code = r.get("openCode","")
    dz = r.get("zodiac","")
    if not code or not dz: continue
    
    nums = [int(x) for x in code.split(",") if x.strip()]
    zods = [z.strip() for z in dz.split(",")]
    
    # Determine zodiac year: use month-based boundaries
    # Jan-Feb before LNY = previous zodiac year
    if dt and len(dt) >= 10:
        month = int(dt[5:7])
        day = int(dt[8:10])
        year = int(dt[:4])
    
    for n, z in zip(nums, zods):
        if 1 <= n <= 49 and z in ZODIAC_MAP:
            year_mappings[dt[:7]][n][z] += 1  # Group by year-month

# Check consistency: for the current period (2026 馬 year), what's the mapping?
print("=== Current Period (2026-03 onward, 馬 year) ===")
recent = defaultdict(Counter)
for r in data:
    dt = r.get("openTime","")
    if dt and dt >= "2026-03":
        code = r.get("openCode","")
        dz = r.get("zodiac","")
        if code and dz:
            nums = [int(x) for x in code.split(",") if x.strip()]
            zods = [z.strip() for z in dz.split(",")]
            for n, z in zip(nums, zods):
                recent[n][z] += 1

# Show mapping for all 49 numbers
print("Number -> Zodiac (most common in recent data):")
consistent = 0
inconsistent = 0
mapping_2026 = {}
for n in range(1, 50):
    if n in recent and recent[n]:
        top_z, top_c = recent[n].most_common(1)[0]
        total = sum(recent[n].values())
        if top_c == total:
            consistent += 1
        else:
            inconsistent += 1
        mapping_2026[n] = top_z
        if inconsistent > 0 or n <= 12:
            others = [(z,c) for z,c in recent[n].most_common() if z != top_z]
            extra = f" (others: {others})" if others else ""
            print(f"  {n:2d} -> {top_z} ({top_c}/{total}){extra}")
    else:
        print(f"  {n:2d} -> ? (no data)")

print(f"\nConsistent: {consistent}, Inconsistent: {inconsistent}")

# Compare with our calculation
print("\n=== Comparison: Our calc vs Data ===")
_LNY = {"2022-02-01":"虎","2023-01-22":"兔","2024-02-10":"龍","2025-01-29":"蛇","2026-02-17":"馬"}
def our_z(n):
    yz = "馬"; zi = ZODIAC_MAP.index(yz)
    return ZODIAC_MAP[(zi + n - 1) % 12]

mismatches = 0
for n in range(1, 50):
    our = our_z(n)
    data_z = mapping_2026.get(n, "?")
    match = "✓" if our == data_z else "✗"
    if our != data_z: mismatches += 1
    if n <= 12:
        print(f"  {n:2d}: our={our} data={data_z} {match}")

print(f"\nMismatches: {mismatches}/49")

# Try to figure out the formula
print("\n=== Reverse Engineering ===")
# For our formula: (year_idx + n - 1) % 12
# Data result: different mapping
# Let's find what year_idx makes the most matches
for test_yi in range(12):
    test_yz = ZODIAC_MAP[test_yi]
    matches = 0
    for n in range(1, 50):
        z = ZODIAC_MAP[(test_yi + n - 1) % 12]
        if z == mapping_2026.get(n, ""):
            matches += 1
    print(f"  Year {test_yz}: {matches}/49 matches")

# Maybe the data uses a different zodiac ordering?
print("\n=== Try all 12! possible orderings (first few) ===")
# Just try: what if ZODIAC_MAP order is different?
# For n=1, data says some zodiac. Let's find the ordering.
if 1 in mapping_2026:
    z1 = mapping_2026[1]
    zi1 = ZODIAC_MAP.index(z1)
    print(f"Number 1 -> {z1} (index {zi1})")
    # If data uses (year_idx + n - 1) % 12 and n=1 gives zi1:
    # year_idx must equal zi1
    # So year_idx = zi1
    # Let's check if this works for all numbers
    matches = 0
    for n in range(1, 50):
        z = ZODIAC_MAP[(zi1 + n - 1) % 12]
        if z == mapping_2026.get(n, ""):
            matches += 1
    print(f"  With year={ZODIAC_MAP[zi1]}: {matches}/49 matches")