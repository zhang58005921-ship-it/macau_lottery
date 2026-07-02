"""Final backtest: zodiac-year-aware with fixed code"""
import json, random, math, sys
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
_LUNAR_NEW_YEAR = {"2022-02-01":"虎","2023-01-22":"兔","2024-02-10":"龍","2025-01-29":"蛇","2026-02-17":"馬"}

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
                specials.append({"number": nums[6], "zodiac": num_to_zodiac(nums[6], dt), "date": dt})
        return specials

class ZodiacYearPredictor:
    """生肖年独立: 只在同年数据内提取庄家规律"""
    def predict_specials(self, count=8):
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        current_yz = _get_year_zodiac(last_date)
        
        # 只取当前生肖年的数据
        same_year = [r for r in self.a.data if _get_year_zodiac(r.get("openTime","")) == current_yz]
        
        sp = self.a.special_code_history(30)
        sp_recent_3 = set(s["number"] for s in sp[:3])
        sp_recent_10 = set(s["number"] for s in sp[:10])
        last_zod = sp[0]["zodiac"] if sp else ""
        recent_5_zod = set(s["zodiac"] for s in sp[:5])
        
        # 同年内生肖频率
        zod_freq = Counter()
        for r in same_year[-20:]:
            for z in Analyzer(same_year).get_zodiacs(r):
                zod_freq[z] += 1
        
        # 跨年不变: 所有位置号码频率 (number-based)
        all_freq = Counter()
        for r in self.a.data[-20:]:
            for n in self.a.get_numbers(r):
                all_freq[n] += 1
        
        max_freq = max(all_freq.values()) if all_freq else 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        
        scores = {}
        for n in range(1, 50):
            s = 0.0
            
            # 周易 (基于当前日期)
            s += iching_affinity(n, last_date) * 18
            
            # 避开近期正特号码 (跨年不变规律)
            if n in sp_recent_3: s -= 35
            elif n in sp_recent_10: s -= 15
            
            # 生肖 (同年内独立计算)
            z = num_to_zodiac(n, last_date)
            s -= (zod_freq.get(z, 0) / max_zod) * 12
            if z == last_zod: s -= 10
            if z in recent_5_zod: s -= 6
            
            # 号码热度 (跨年不变)
            s -= (all_freq.get(n, 0) / max_freq) * 20
            
            # 迷信号
            if n in {6,8,16,18,26,28,33,36,38}: s -= 6
            if n in {4,14,24,34,44}: s += 4
            
            scores[n] = s
        
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

# Run
print("="*60)
print("ZODIAC-YEAR-AWARE BACKTEST")
print("="*60)
warmup = 60

h, t = 0, 0
per_year = defaultdict(lambda: {"hits":0, "total":0})
for idx in range(warmup, len(data)):
    train = data[:idx]
    test = data[idx]
    actual = [int(x) for x in test.get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    test_date = test.get("openTime","")
    
    try:
        a = Analyzer(train)
        pred = ZodiacYearPredictor()
        pred.a = a
        result = pred.predict_specials(8)
        t += 1
        if actual_sp in result: h += 1
        
        yz = _get_year_zodiac(test_date)
        per_year[yz]["total"] += 1
        if actual_sp in result: per_year[yz]["hits"] += 1
    except Exception as e:
        pass

print(f"Overall: {h}/{t} = {h/t*100:.1f}%")
for yz in ["兔","龍","蛇","馬"]:
    s = per_year[yz]
    if s["total"] > 0:
        print(f"  {yz}年: {s['hits']}/{s['total']} = {s['hits']/s['total']*100:.1f}%")

# Random
random.seed(99)
hr, tr = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    tr += 1
    if actual[6] in random.sample(range(1,50), 8): hr += 1
print(f"Random: {hr}/{tr} = {hr/tr*100:.1f}%")

print("="*60)
print("DONE")