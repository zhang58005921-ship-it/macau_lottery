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
    d = date_str[:10]; zodiac = "馬"
    for date, z in sorted(_LUNAR_NEW_YEAR.items()):
        if d >= date: zodiac = z
    return zodiac

def num_to_zodiac(num, date_str=None):
    n = int(num)
    if n < 1 or n > 49: return "?"
    year_z = _get_year_zodiac(date_str) if date_str else "馬"
    return ZODIAC_MAP[(ZODIAC_MAP.index(year_z) - (n - 1)) % 12]

def num_to_wave(n):
    n = int(n)
    if n in {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}: return ("红波","#ff4444")
    if n in {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}: return ("蓝波","#4488ff")
    return ("绿波","#44cc44")

_XT_BAGUA = ["乾","兑","离","震","巽","坎","艮","坤"]
_XT_ELEMENT = {"乾":"金","兑":"金","离":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}
_WX_GENERATE = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
_WX_OVERCOME = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

def num_to_element(n): return _XT_ELEMENT[_XT_BAGUA[(n - 1) % 8]]

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
    def __init__(self, data_slice): self.data = data_slice
    def get_numbers(self, r):
        c = r.get("openCode",""); return [int(x) for x in c.split(",") if x.strip()] if c else []
    def get_zodiacs(self, r):
        dt = r.get("openTime", ""); return [num_to_zodiac(n, dt) for n in self.get_numbers(r)]
    def special_code_history(self, last_n=50):
        specials = []
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            if len(nums) >= 7:
                dt = r.get("openTime", "")
                specials.append({"number": nums[6], "zodiac": num_to_zodiac(nums[6], dt)})
        return specials

def get_gaps(data_slice):
    a = Analyzer(data_slice)
    gaps = {n: 999 for n in range(1,50)}
    for i, r in enumerate(reversed(data_slice)):
        nums = a.get_numbers(r)
        if len(nums) >= 7:
            sp = nums[6]
            if gaps.get(sp, 999) == 999: gaps[sp] = i
    return gaps

class RegimePredictorV4:
    def __init__(self, a): self.a = a
    def _detect_regime(self):
        sp_hist = self.a.special_code_history(30)
        if len(sp_hist) < 20: return "neutral"
        half = len(sp_hist) // 2
        first = sp_hist[:half]; second = sp_hist[half:]
        all_data = self.a.data
        gaps_all = get_gaps(all_data)
        first_gaps = [gaps_all[s["number"]] for s in first if s["number"] in gaps_all]
        second_gaps = [gaps_all[s["number"]] for s in second if s["number"] in gaps_all]
        if not first_gaps or not second_gaps: return "neutral"
        avg_first = sum(first_gaps) / len(first_gaps)
        avg_second = sum(second_gaps) / len(second_gaps)
        if avg_second > avg_first * 1.3: return "cold"
        elif avg_second < avg_first * 0.7: return "hot"
        else: return "neutral"
    
    def predict_specials(self, count=8):
        sp_hist = self.a.special_code_history(30)
        sp_recent_5 = set(s["number"] for s in sp_hist[:5])
        sp_recent_10 = set(s["number"] for s in sp_hist[:10])
        sp_recent_20 = set(s["number"] for s in sp_hist[:20])
        sp_recent_3_zod = set(s["zodiac"] for s in sp_hist[:3])
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        last_zod = sp_hist[0]["zodiac"] if sp_hist else ""
        regime = self._detect_regime()
        
        all_freq = Counter()
        for r in self.a.data[-15:]:
            for n in Analyzer(self.a.data).get_numbers(r):
                all_freq[n] += 1
        max_freq = max(all_freq.values()) if all_freq else 1
        
        zod_freq = Counter()
        for r in self.a.data[-15:]:
            for z in Analyzer(self.a.data).get_zodiacs(r):
                zod_freq[z] += 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        
        scores = {}
        for n in range(1, 50):
            s = 0.0
            s += iching_affinity(n, last_date) * 25
            if n in sp_recent_5: s -= 50
            elif n in sp_recent_10: s -= 25
            elif n in sp_recent_20: s -= 10
            z = num_to_zodiac(n, last_date)
            s -= (zod_freq.get(z, 0) / max_zod) * 15
            if z == last_zod: s -= 12
            if z in sp_recent_3_zod: s -= 8
            s -= (all_freq.get(n, 0) / max_freq) * 18
            if n in {6,8,16,18,26,28,33,36,38}: s -= 6
            if n in {4,14,24,34,44}: s += 4
            scores[n] = s
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

class MinimalV4:
    def __init__(self, a): self.a = a
    def predict_specials(self, count=8):
        sp_hist = self.a.special_code_history(20)
        sp_recent_5 = set(s["number"] for s in sp_hist[:5])
        sp_recent_3_zod = set(s["zodiac"] for s in sp_hist[:3])
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        last_zod = sp_hist[0]["zodiac"] if sp_hist else ""
        all_freq = Counter()
        for r in self.a.data[-10:]:
            for n in Analyzer(self.a.data).get_numbers(r):
                all_freq[n] += 1
        max_freq = max(all_freq.values()) if all_freq else 1
        scores = {}
        for n in range(1, 50):
            s = 0.0
            s += iching_affinity(n, last_date) * 20
            if n in sp_recent_5: s -= 40
            z = num_to_zodiac(n, last_date)
            if z == last_zod: s -= 15
            if z in sp_recent_3_zod: s -= 10
            s -= (all_freq.get(n, 0) / max_freq) * 15
            scores[n] = s
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

print("="*60)
print("V4 BACKTEST -- Signal-validated + Regime Detection")
print("="*60)

warmup = 80

h1, t1 = 0, 0
regimes_seen = Counter()
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = RegimePredictorV4(a)
        regime = pred._detect_regime()
        regimes_seen[regime] += 1
        result = pred.predict_specials(8)
        t1 += 1
        if actual[6] in result: h1 += 1
    except: pass
print(f"RegimePredictorV4: {h1}/{t1} = {h1/t1*100:.1f}%")
print(f"  Regimes: {dict(regimes_seen)}")

h2, t2 = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = MinimalV4(a).predict_specials(8)
        t2 += 1
        if actual[6] in pred: h2 += 1
    except: pass
print(f"MinimalV4:          {h2}/{t2} = {h2/t2*100:.1f}%")

random.seed(99)
h3, t3 = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    t3 += 1
    if actual[6] in random.sample(range(1,50), 8): h3 += 1
print(f"Random baseline:    {h3}/{t3} = {h3/t3*100:.1f}%")

print("\n--- Recent 50 ---")
w_start = max(0, len(data) - 50)
for name, cls in [("RegimeV4", RegimePredictorV4), ("MinimalV4", MinimalV4)]:
    h, t = 0, 0
    for idx in range(w_start, len(data)):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        try:
            if actual[6] in cls(a).predict_specials(8): h += 1
            t += 1
        except: pass
    print(f"  {name}: {h}/{t} = {h/t*100:.1f}%")

print("\n--- Rolling 50-window hit rate ---")
window = 50
for start in range(0, len(data) - window, 100):
    end = start + window
    if end > len(data): end = len(data)
    h, t = 0, 0
    for idx in range(max(start, warmup), end):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        try:
            if actual[6] in RegimePredictorV4(a).predict_specials(8): h += 1
            t += 1
        except: pass
    rate = h/t*100 if t else 0
    bar = "#"*int(rate)
    label = f"Period {data[start].get('expect','?')}-{data[min(end-1,len(data)-1)].get('expect','?')}" if start < len(data) else ""
    print(f"  {label}: {h}/{t} = {rate:.1f}% {bar}")

print("\n--- Ensemble (RegimeV4 + MinimalV4 combined) ---")
h_ens, t_ens = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        r1 = RegimePredictorV4(a).predict_specials(8)
        r2 = MinimalV4(a).predict_specials(8)
        combined = list(dict.fromkeys(r1[:4] + r2[:4]))
        for r in r1 + r2:
            if r not in combined: combined.append(r)
            if len(combined) >= 8: break
        t_ens += 1
        if actual[6] in combined[:8]: h_ens += 1
    except: pass
print(f"Ensemble: {h_ens}/{t_ens} = {h_ens/t_ens*100:.1f}%")

print()
print("="*60)
print("V4 COMPLETE")
print("="*60)
