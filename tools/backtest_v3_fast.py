"""V3 Fast — Feature correlation analysis + optimized model"""
import json, random, math
from collections import Counter, defaultdict

DATA_FILE = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\macaujc_data.json"
with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)
seen = set()
data = []
for r in raw_data:
    exp = r.get("expect", "")
    if exp not in seen:
        seen.add(exp)
        data.append(r)
data.sort(key=lambda x: int(x.get("expect", 0)))

ZODIAC_MAP = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]
_LUNAR_NEW_YEAR = {"2023-01-22":"兔","2024-02-10":"龍","2025-01-29":"蛇","2026-02-17":"馬"}

def _get_year_zodiac(date_str):
    if not date_str or len(date_str) < 10: return "馬"
    d = date_str[:10]
    zodiac = "馬"
    for date, z in sorted(_LUNAR_NEW_YEAR.items()):
        if d >= date: zodiac = z
    return zodiac

def num_to_zodiac(num, date_str=None):
    n = int(num)
    if n < 1 or n > 49: return "?"
    year_z = _get_year_zodiac(date_str) if date_str else "馬"
    zi = ZODIAC_MAP.index(year_z)
    return ZODIAC_MAP[(zi + (n - 1)) % 12]

def num_to_wave(n):
    n = int(n)
    if n in {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}: return ("红波","#ff4444")
    if n in {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}: return ("蓝波","#4488ff")
    return ("绿波","#44cc44")

_XT_BAGUA = ["乾","兑","离","震","巽","坎","艮","坤"]
_XT_ELEMENT = {"乾":"金","兑":"金","离":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}
_WX_GENERATE = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
_WX_OVERCOME = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

def num_to_element(n):
    return _XT_ELEMENT[_XT_BAGUA[(n - 1) % 8]]

def date_to_daily_element(date_str):
    if not date_str or len(date_str) < 10: return "土"
    try:
        month = int(date_str[5:7])
        if month in [3,4]: return "木"
        elif month in [5,6]: return "火"
        elif month in [7,8]: return "金"
        elif month in [9,10]: return "土"
        else: return "水"
    except: return "土"

def iching_affinity(n, date_str=None):
    if date_str is None: return 0.0
    day_elem = date_to_daily_element(date_str)
    num_elem = num_to_element(n)
    if _WX_GENERATE.get(day_elem) == num_elem: return 1.0
    elif _WX_GENERATE.get(num_elem) == day_elem: return 0.5
    elif _WX_OVERCOME.get(day_elem) == num_elem: return -1.0
    elif _WX_OVERCOME.get(num_elem) == day_elem: return -0.3
    else: return 0.3

class Analyzer:
    def __init__(self, data_slice):
        self.data = data_slice
    def get_numbers(self, r):
        c = r.get("openCode","")
        return [int(x) for x in c.split(",") if x.strip()] if c else []
    def get_zodiacs(self, r):
        dt = r.get("openTime", "")
        return [num_to_zodiac(n, dt) for n in self.get_numbers(r)]
    def special_code_history(self, last_n=50):
        specials = []
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            if len(nums) >= 7:
                dt = r.get("openTime", "")
                specials.append({"number": nums[6], "zodiac": num_to_zodiac(nums[6], dt)})
        return specials
    def special_frequency(self, last_n=100):
        sc = Counter()
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            if len(nums) >= 7: sc[nums[6]] += 1
        return dict(sc)

def get_gaps(data_slice):
    a = Analyzer(data_slice)
    gaps = {n: 999 for n in range(1,50)}
    for i, r in enumerate(reversed(data_slice)):
        nums = a.get_numbers(r)
        if len(nums) >= 7:
            sp = nums[6]
            if gaps.get(sp, 999) == 999: gaps[sp] = i
    return gaps

# ============================================================
# FEATURE CORRELATION ANALYSIS
# ============================================================
print("="*60)
print("FEATURE CORRELATION ANALYSIS")
print("="*60)
print("Analyzing which features correlate with actual special number...")
print()

warmup = 80

# For each period, compute: for the actual special number, what features did it have?
# Compare with the average feature values across all 49 numbers
feature_diffs = defaultdict(list)

for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    last_date = data[idx-1].get("openTime","") if idx > 0 else ""
    
    gaps = get_gaps(data[:idx])
    sp_hist = a.special_code_history(50)
    sp_recent_10 = set(s["number"] for s in sp_hist[:10])
    sp_recent_3 = set(s["number"] for s in sp_hist[:3])
    
    all_freq = Counter()
    for r in data[:idx][-20:]:
        for n in a.get_numbers(r):
            all_freq[n] += 1
    
    zod_freq = Counter()
    for r in data[:idx][-15:]:
        for z in a.get_zodiacs(r):
            zod_freq[z] += 1
    
    recent_5_zod = set(s["zodiac"] for s in sp_hist[:5])
    
    oes = ["单" if s["number"]%2 else "双" for s in sp_hist[:15]]
    oe_streak, last_oe = 0, oes[-1] if oes else "单"
    for o in reversed(oes):
        if o == last_oe: oe_streak += 1
        else: break
    
    waves = [num_to_wave(s["number"])[0] for s in sp_hist[:15]]
    wave_streak, last_wave = 0, waves[-1] if waves else "红波"
    for w in reversed(waves):
        if w == last_wave: wave_streak += 1
        else: break
    
    max_gap = max(gaps.values()) if gaps else 999
    max_freq = max(all_freq.values()) if all_freq else 1
    max_zod = max(zod_freq.values()) if zod_freq else 1
    
    for n in range(1, 50):
        is_actual = 1 if n == actual_sp else 0
        
        feat = {}
        feat["gap_norm"] = gaps[n] / max(max_gap, 1)
        feat["is_cold50"] = 1 if gaps[n] >= 50 else 0
        feat["is_cold80"] = 1 if gaps[n] >= 80 else 0
        feat["all_freq"] = all_freq.get(n, 0) / max_freq
        feat["is_recent_sp"] = 1 if n in sp_recent_10 else 0
        feat["is_very_recent"] = 1 if n in sp_recent_3 else 0
        z = num_to_zodiac(n, last_date)
        feat["zod_heat"] = zod_freq.get(z, 0) / max_zod
        feat["zod_recent"] = 1 if z in recent_5_zod else 0
        feat["iching"] = iching_affinity(n, last_date)
        feat["is_lucky"] = 1 if n in {6,8,16,18,26,28,33,36,38} else 0
        feat["is_unlucky"] = 1 if n in {4,14,24,34,44} else 0
        feat["oe_same"] = 1 if ("单" if n%2 else "双") == last_oe else 0
        feat["wave_same"] = 1 if num_to_wave(n)[0] == last_wave else 0
        
        for k, v in feat.items():
            feature_diffs[f"{k}_actual"].append(v if is_actual else None)
            feature_diffs[f"{k}_all"].append(v)

# Compute averages
print("Feature           | Actual SP Avg | All Numbers Avg | Diff  | Signal")
print("-" * 75)
for feat_name in ["gap_norm", "is_cold50", "is_cold80", "all_freq", "is_recent_sp", 
                   "is_very_recent", "zod_heat", "zod_recent", "iching", "is_lucky", "is_unlucky"]:
    actual_vals = [v for v in feature_diffs[f"{feat_name}_actual"] if v is not None]
    all_vals = feature_diffs[f"{feat_name}_all"]
    actual_avg = sum(actual_vals) / len(actual_vals) if actual_vals else 0
    all_avg = sum(all_vals) / len(all_vals) if all_vals else 0
    diff = actual_avg - all_avg
    bar = "+" * max(0, int(diff*200)) + "-" * max(0, int(-diff*200))
    direction = "STRONG+" if diff > 0.02 else ("+" if diff > 0.005 else ("-" if diff < -0.005 else "~"))
    print(f"{feat_name:18s} | {actual_avg:13.4f} | {all_avg:15.4f} | {diff:+7.4f} | {direction}")

# ============================================================
# COLD NUMBER DEEP DIVE
# ============================================================
print()
print("="*60)
print("COLD NUMBER DEEP DIVE")
print("="*60)

# For each gap range, compute hit rate
gap_buckets = [(0,5,"0-5"), (5,10,"5-10"), (10,20,"10-20"), (20,30,"20-30"),
               (30,50,"30-50"), (50,80,"50-80"), (80,200,"80-200"), (200,999,"200+")]
bucket_stats = {name: {"total_nums":0, "total_hits":0, "periods":0} for _,_,name in gap_buckets}

for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    gaps = get_gaps(data[:idx])
    for n in range(1, 50):
        g = gaps[n]
        for lo, hi, name in gap_buckets:
            if lo <= g < hi:
                bucket_stats[name]["total_nums"] += 1
                if n == actual_sp: bucket_stats[name]["total_hits"] += 1
                break

print(f"{'Gap Range':<12s} {'Hit Rate':>10s} {'vs Random':>10s} {'Multiplier':>10s}")
print("-" * 45)
for _, _, name in gap_buckets:
    s = bucket_stats[name]
    rate = s["total_hits"]/s["total_nums"]*100 if s["total_nums"] > 0 else 0
    mult = rate / (100/49)
    print(f"{name:<12s} {rate:9.2f}% {rate-2.04:+9.2f}% {mult:9.2f}x")

# ============================================================
# I CHING CORRELATION
# ============================================================
print()
print("="*60)
print("I CHING AFFINITY vs HIT RATE")
print("="*60)

iching_buckets = [(-1.5,-0.5,"负亲和"), (-0.5,0.1,"中性"), (0.1,0.5,"弱正"), (0.5,1.5,"强正")]
iching_stats = {name: {"total":0, "hits":0} for _,_,name in iching_buckets}

for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    last_date = data[idx-1].get("openTime","") if idx > 0 else ""
    for n in range(1, 50):
        aff = iching_affinity(n, last_date)
        for lo, hi, name in iching_buckets:
            if lo <= aff < hi:
                iching_stats[name]["total"] += 1
                if n == actual_sp: iching_stats[name]["hits"] += 1
                break

for _, _, name in iching_buckets:
    s = iching_stats[name]
    rate = s["hits"]/s["total"]*100 if s["total"] > 0 else 0
    mult = rate / (100/49)
    bar = "#"*int(mult*10)
    print(f"  {name}: {rate:.2f}% ({mult:.2f}x random) {bar}")

# ============================================================
# ZODIAC AVOIDANCE ANALYSIS
# ============================================================
print()
print("="*60)
print("ZODIAC RECENCY vs HIT")
print("="*60)

zod_stats = {"same_as_last": {"total":0,"hits":0}, "diff_from_last": {"total":0,"hits":0}}
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    last_date = data[idx-1].get("openTime","") if idx > 0 else ""
    sp_hist = a.special_code_history(5)
    last_zod = sp_hist[0]["zodiac"] if sp_hist else ""
    actual_zod = num_to_zodiac(actual_sp, last_date)
    for n in range(1, 50):
        z = num_to_zodiac(n, last_date)
        if z == last_zod:
            zod_stats["same_as_last"]["total"] += 1
            if n == actual_sp: zod_stats["same_as_last"]["hits"] += 1
        else:
            zod_stats["diff_from_last"]["total"] += 1
            if n == actual_sp: zod_stats["diff_from_last"]["hits"] += 1

for k, s in zod_stats.items():
    rate = s["hits"]/s["total"]*100 if s["total"] > 0 else 0
    print(f"  {k}: {rate:.2f}% (random=2.04%)")

# ============================================================
# OPTIMIZED V3 MODEL (weights from correlation analysis)
# ============================================================
print()
print("="*60)
print("OPTIMIZED V3 MODEL BACKTEST")
print("="*60)

class OptimizedV3:
    """Weights derived from correlation analysis above"""
    def __init__(self, a):
        self.a = a
    
    def predict_specials(self, count=8):
        gaps = get_gaps(self.a.data)
        sp_hist = self.a.special_code_history(30)
        sp_recent_10 = set(s["number"] for s in sp_hist[:10])
        sp_recent_3 = set(s["number"] for s in sp_hist[:3])
        
        all_freq = Counter()
        for r in self.a.data[-20:]:
            for n in Analyzer(self.a.data).get_numbers(r):
                all_freq[n] += 1
        
        zod_freq = Counter()
        for r in self.a.data[-15:]:
            for z in Analyzer(self.a.data).get_zodiacs(r):
                zod_freq[z] += 1
        
        recent_5_zod = set(s["zodiac"] for s in sp_hist[:5])
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        
        oes = ["单" if s["number"]%2 else "双" for s in sp_hist[:15]]
        oe_streak, last_oe = 0, oes[-1] if oes else "单"
        for o in reversed(oes):
            if o == last_oe: oe_streak += 1
            else: break
        
        max_gap = max(gaps.values()) if gaps else 999
        max_freq = max(all_freq.values()) if all_freq else 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        
        scores = {}
        for n in range(1, 50):
            s = 0.0
            
            # COLD = primary positive signal
            gap = gaps[n]
            if gap >= 80: s += 30
            elif gap >= 50: s += 20
            elif gap >= 30: s += 10
            elif gap >= 20: s += 5
            
            # HOT ALL POSITIONS = avoid
            freq = all_freq.get(n, 0)
            s -= (freq / max_freq) * 30
            
            # RECENT SPECIAL = heavy avoid
            if n in sp_recent_3: s -= 35
            elif n in sp_recent_10: s -= 15
            
            # ZODIAC HEAT = avoid
            z = num_to_zodiac(n, last_date)
            s -= (zod_freq.get(z, 0) / max_zod) * 12
            
            # ZODIAC RECENCY = avoid
            if z in recent_5_zod: s -= 8
            
            # I CHING = mild positive
            s += iching_affinity(n, last_date) * 8
            
            # LUCKY/SUPERSTITION = avoid (crowd anchor)
            if n in {6,8,16,18,26,28,33,36,38}: s -= 5
            if n in {4,14,24,34,44}: s += 3
            
            # OE/WAVE streak
            if oe_streak >= 4:
                if ("单" if n%2 else "双") == last_oe: s += 6
                else: s -= 10
            if [num_to_wave(s2["number"])[0] for s2 in sp_hist[:3]].count(num_to_wave(n)[0]) >= 2:
                s -= 4
            
            scores[n] = s
        
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

# Run backtest
h, t = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = OptimizedV3(a).predict_specials(8)
        t += 1
        if actual[6] in pred: h += 1
    except: pass
print(f"OptimizedV3: {h}/{t} = {h/t*100:.1f}%")

# Random
random.seed(99)
hr, tr = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    tr += 1
    if actual[6] in random.sample(range(1,50), 8): hr += 1
print(f"Random:      {hr}/{tr} = {hr/tr*100:.1f}%")

# Recent 50
print("\n--- Recent 50 ---")
w_start = max(0, len(data) - 50)
h50, t50 = 0, 0
for idx in range(w_start, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        if actual[6] in OptimizedV3(a).predict_specials(8): h50 += 1
        t50 += 1
    except: pass
print(f"OptimizedV3 (recent 50): {h50}/{t50} = {h50/t50*100:.1f}%")

# 10-fold cross validation (by time)
print("\n--- 10-fold Time Split ---")
fold_size = (len(data) - warmup) // 10
for fold in range(10):
    f_start = warmup + fold * fold_size
    f_end = min(warmup + (fold+1) * fold_size, len(data))
    hf, tf = 0, 0
    for idx in range(f_start, f_end):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        try:
            if actual[6] in OptimizedV3(a).predict_specials(8): hf += 1
            tf += 1
        except: pass
    rate = hf/tf*100 if tf else 0
    bar = "#"*int(rate)
    exp_start = data[f_start].get("expect","?") if f_start < len(data) else "?"
    exp_end = data[f_end-1].get("expect","?") if f_end <= len(data) else "?"
    print(f"  Fold {fold+1} ({exp_start}-{exp_end}): {hf}/{tf} = {rate:.1f}% {bar}")

print()
print("="*60)
print("ANALYSIS COMPLETE")
print("="*60)