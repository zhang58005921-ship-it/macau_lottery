"""按生肖年独立回测 — 提取跨年不变的庄家操作规律"""
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
_LUNAR_NEW_YEAR = {
    "2022-02-01":"虎","2023-01-22":"兔","2024-02-10":"龍",
    "2025-01-29":"蛇","2026-02-17":"馬",
}

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

# ============================================================
# 1. SPLIT DATA BY ZODIAC YEAR
# ============================================================
print("="*60)
print("1. DATA SPLIT BY ZODIAC YEAR")
print("="*60)

zodiac_year_groups = defaultdict(list)
for r in data:
    dt = r.get("openTime","")
    yz = _get_year_zodiac(dt)
    zodiac_year_groups[yz].append(r)

for yz in ["兔","龍","蛇","馬"]:
    group = zodiac_year_groups.get(yz, [])
    if group:
        dates = [r.get("openTime","")[:10] for r in group if r.get("openTime","")]
        print(f"  {yz}年: {len(group)}期  {dates[0] if dates else '?'} ~ {dates[-1] if dates else '?'}")

# ============================================================
# 2. PER-YEAR FEATURE CORRELATION
# ============================================================
print()
print("="*60)
print("2. PER-YEAR SIGNAL VALIDATION")
print("="*60)

warmup = 30

for yz_name, yz_data in [("兔", zodiac_year_groups.get("兔",[])), 
                          ("龍", zodiac_year_groups.get("龍",[])),
                          ("蛇", zodiac_year_groups.get("蛇",[])),
                          ("馬", zodiac_year_groups.get("馬",[]))]:
    if len(yz_data) < warmup + 10: continue
    
    yz_sorted = sorted(yz_data, key=lambda x: int(x.get("expect", 0)))
    
    # Compute: for each period, check if I Ching affinity predicts special
    iching_hits = {"neg":0, "neu":0, "pos_weak":0, "pos_strong":0}
    iching_total = {"neg":0, "neu":0, "pos_weak":0, "pos_strong":0}
    
    recent_sp_avoid_hits = 0
    recent_sp_avoid_total = 0
    
    zod_avoid_hits = 0
    zod_avoid_total = 0
    
    for idx in range(warmup, len(yz_sorted)):
        train = yz_sorted[:idx]
        test = yz_sorted[idx]
        actual = [int(x) for x in test.get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        actual_sp = actual[6]
        last_date = yz_sorted[idx-1].get("openTime","") if idx > 0 else ""
        
        a = Analyzer(train)
        sp_hist = a.special_code_history(30)
        sp_recent_5 = set(s["number"] for s in sp_hist[:5])
        last_zod = sp_hist[0]["zodiac"] if sp_hist else ""
        recent_5_zod = set(s["zodiac"] for s in sp_hist[:5])
        
        for n in range(1, 50):
            # I Ching
            aff = iching_affinity(n, last_date)
            if aff < -0.1: bucket = "neg"
            elif aff < 0.1: bucket = "neu"
            elif aff < 0.5: bucket = "pos_weak"
            else: bucket = "pos_strong"
            iching_total[bucket] += 1
            if n == actual_sp: iching_hits[bucket] += 1
            
            # Recent special avoidance
            if n not in sp_recent_5:
                recent_sp_avoid_total += 1
                if n == actual_sp: recent_sp_avoid_hits += 1
            
            # Zodiac avoidance
            z = num_to_zodiac(n, last_date)
            if z != last_zod and z not in recent_5_zod:
                zod_avoid_total += 1
                if n == actual_sp: zod_avoid_hits += 1
    
    print(f"\n  [{yz_name}年] {len(yz_sorted)}期:")
    
    # I Ching
    expected = 1/49*100
    for bucket in ["neg","neu","pos_weak","pos_strong"]:
        rate = iching_hits[bucket]/iching_total[bucket]*100 if iching_total[bucket] > 0 else 0
        diff = rate - expected
        bar = "+"*max(0,int(diff*50)) + "-"*max(0,int(-diff*50))
        labels = {"neg":"负亲和","neu":"中性","pos_weak":"弱正","pos_strong":"强正"}
        print(f"    IChing {labels[bucket]:4s}: {rate:.2f}% (diff {diff:+.2f}%) {bar}")
    
    # Recent SP avoidance
    rate_sp = recent_sp_avoid_hits/recent_sp_avoid_total*100 if recent_sp_avoid_total > 0 else 0
    print(f"    避开近5期正特:    {rate_sp:.2f}% (base=2.04%)")
    
    # Zodiac avoidance
    rate_zod = zod_avoid_hits/zod_avoid_total*100 if zod_avoid_total > 0 else 0
    print(f"    避开近5期生肖:    {rate_zod:.2f}% (base=2.04%)")

# ============================================================
# 3. CROSS-YEAR INVARIANT PATTERNS
# ============================================================
print()
print("="*60)
print("3. CROSS-YEAR INVARIANT HOUSE PATTERNS")
print("="*60)

# Test: Does "avoid number that was special in last 3 draws" work across years?
# This is number-based, not zodiac-based, so should be year-invariant
print("\n  [跨年不变信号] 基于号码(非生肖):")

warmup = 50
recent_sp_hit = 0
recent_sp_total = 0
not_recent_sp_hit = 0
not_recent_sp_total = 0

for idx in range(warmup, len(data)):
    train = data[:idx]
    test = data[idx]
    actual = [int(x) for x in test.get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    
    a = Analyzer(train)
    sp_hist = a.special_code_history(20)
    sp_recent_3 = set(s["number"] for s in sp_hist[:3])
    sp_recent_5 = set(s["number"] for s in sp_hist[:5])
    sp_recent_10 = set(s["number"] for s in sp_hist[:10])
    
    for n in range(1, 50):
        if n in sp_recent_3:
            recent_sp_total += 1
            if n == actual_sp: recent_sp_hit += 1
        elif n in sp_recent_5:
            recent_sp_total += 1
            if n == actual_sp: recent_sp_hit += 1
        elif n in sp_recent_10:
            recent_sp_total += 1
            if n == actual_sp: recent_sp_hit += 1
        else:
            not_recent_sp_total += 1
            if n == actual_sp: not_recent_sp_hit += 1

rate_rec = recent_sp_hit/recent_sp_total*100 if recent_sp_total > 0 else 0
rate_not = not_recent_sp_hit/not_recent_sp_total*100 if not_recent_sp_total > 0 else 0
print(f"  最近10期正特号码:  {rate_rec:.2f}%")
print(f"  非近10期正特号码:  {rate_not:.2f}%")
print(f"  差异: {rate_not-rate_rec:+.2f}% (正值=庄家避开近期正特)")

# Test: Hot number avoidance (all 7 positions, not just special)
print("\n  [跨年不变信号] 7位综合热度:")
all_freq_hit_bins = {f"freq_{i}": {"hits":0, "total":0} for i in range(5)}

for idx in range(warmup, len(data)):
    train = data[:idx]
    test = data[idx]
    actual = [int(x) for x in test.get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    
    a = Analyzer(train)
    all_freq = Counter()
    for r in train[-20:]:
        for n in a.get_numbers(r):
            all_freq[n] += 1
    max_f = max(all_freq.values()) if all_freq else 1
    
    for n in range(1, 50):
        f = all_freq.get(n, 0)
        if f == 0: bin_idx = 0
        elif f <= max_f*0.25: bin_idx = 1
        elif f <= max_f*0.5: bin_idx = 2
        elif f <= max_f*0.75: bin_idx = 3
        else: bin_idx = 4
        all_freq_hit_bins[f"freq_{bin_idx}"]["total"] += 1
        if n == actual_sp: all_freq_hit_bins[f"freq_{bin_idx}"]["hits"] += 1

for i in range(5):
    b = all_freq_hit_bins[f"freq_{i}"]
    rate = b["hits"]/b["total"]*100 if b["total"] > 0 else 0
    labels = ["从未出现","低频","中低频","中高频","高频"]
    bar = "+" if rate > 2.04 else "-"
    print(f"  {labels[i]:6s}: {rate:.2f}% {bar}")

# Test: Wave color streak (number-independent, should be invariant)
print("\n  [跨年不变信号] 波色连势:")
for streak_len in [2, 3, 4]:
    same_hit, same_total = 0, 0
    diff_hit, diff_total = 0, 0
    for idx in range(warmup, len(data)):
        train = data[:idx]
        test = data[idx]
        actual = [int(x) for x in test.get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        actual_sp = actual[6]
        
        a = Analyzer(train)
        sp_hist = a.special_code_history(max(15, streak_len))
        waves = [num_to_wave(s["number"])[0] for s in sp_hist]
        streak, last_w = 0, waves[-1] if waves else "红波"
        for w in reversed(waves):
            if w == last_w: streak += 1
            else: break
        
        actual_w = num_to_wave(actual_sp)[0]
        for n in range(1, 50):
            w = num_to_wave(n)[0]
            if w == last_w:
                same_total += 1
                if n == actual_sp: same_hit += 1
            else:
                diff_total += 1
                if n == actual_sp: diff_hit += 1
    
    if streak_len == 3:  # Only print for streak=3
        rate_same = same_hit/same_total*100 if same_total > 0 else 0
        rate_diff = diff_hit/diff_total*100 if diff_total > 0 else 0
        print(f"  同波色(连{streak_len}期): {rate_same:.2f}%")
        print(f"  异波色(连{streak_len}期): {rate_diff:.2f}%")
        print(f"  差异: {rate_diff-rate_same:+.2f}%")

# ============================================================
# 4. ZODIAC-YEAR-AWARE MODEL
# ============================================================
print()
print("="*60)
print("4. ZODIAC-YEAR-AWARE BACKTEST")
print("="*60)

class ZodiacYearAwarePredictor:
    """按生肖年独立计算+跨年不变规律参考"""
    def __init__(self, a):
        self.a = a
    
    def _get_year_patterns(self):
        """从当前生肖年的历史数据中提取庄家模式"""
        if len(self.a.data) < 30:
            return {"recent_avoid": 15, "zod_avoid": 10, "iching_w": 12, "freq_avoid": 15}
        
        # 使用当前生肖年内数据做简单回测来校准权重
        data_slice = self.a.data
        last_date = data_slice[-1].get("openTime","") if data_slice else ""
        current_yz = _get_year_zodiac(last_date)
        
        # 只取当前生肖年的数据
        same_year_data = [r for r in data_slice if _get_year_zodiac(r.get("openTime","")) == current_yz]
        
        if len(same_year_data) < 30:
            # 当前年数据不足，使用默认权重（基于跨年分析）
            return {"recent_avoid": 18, "zod_avoid": 10, "iching_w": 15, "freq_avoid": 15}
        
        # 在当前年内回测不同权重组合
        best_hits = 0
        best_w = {"recent_avoid": 18, "zod_avoid": 10, "iching_w": 15, "freq_avoid": 15}
        
        for ra in [12, 15, 18, 22]:
            for iw in [10, 15, 18, 22]:
                for za in [5, 8, 10, 15]:
                    hits = 0
                    total = 0
                    test_start = max(20, len(same_year_data) // 3)
                    for ti in range(test_start, len(same_year_data)):
                        if ti < 2: continue
                        sub_train = same_year_data[:ti]
                        sub_test = same_year_data[ti]
                        actual = [int(x) for x in sub_test.get("openCode","").split(",") if x.strip()]
                        if len(actual) < 7: continue
                        actual_sp = actual[6]
                        sub_date = same_year_data[ti-1].get("openTime","")
                        
                        sub_a = Analyzer(sub_train)
                        sp = sub_a.special_code_history(20)
                        sp_3 = set(s["number"] for s in sp[:3])
                        sp_10 = set(s["number"] for s in sp[:10])
                        last_z = sp[0]["zodiac"] if sp else ""
                        
                        all_f = Counter()
                        zod_f = Counter()
                        for r in sub_train[-15:]:
                            for n2 in sub_a.get_numbers(r): all_f[n2] += 1
                            for z2 in sub_a.get_zodiacs(r): zod_f[z2] += 1
                        mxf = max(all_f.values()) if all_f else 1
                        mxz = max(zod_f.values()) if zod_f else 1
                        
                        scores = {}
                        for n in range(1, 50):
                            s = 0.0
                            s += iching_affinity(n, sub_date) * iw
                            if n in sp_3: s -= ra * 2
                            elif n in sp_10: s -= ra
                            z = num_to_zodiac(n, sub_date)
                            if z == last_z: s -= za
                            s -= (all_f.get(n,0)/mxf) * 15
                            scores[n] = s
                        
                        pred = sorted(range(1,50), key=lambda x: scores.get(x,0), reverse=True)[:8]
                        total += 1
                        if actual_sp in pred: hits += 1
                    
                    if hits > best_hits:
                        best_hits = hits
                        best_w = {"recent_avoid": ra, "zod_avoid": za, "iching_w": iw, "freq_avoid": 15}
        
        return best_w
    
    def predict_specials(self, count=8):
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        current_yz = _get_year_zodiac(last_date)
        
        sp = self.a.special_code_history(30)
        sp_recent_3 = set(s["number"] for s in sp[:3])
        sp_recent_10 = set(s["number"] for s in sp[:10])
        last_zod = sp[0]["zodiac"] if sp else ""
        recent_5_zod = set(s["zodiac"] for s in sp[:5])
        
        all_freq = Counter()
        zod_freq = Counter()
        for r in self.a.data[-15:]:
            for n in self.a.get_numbers(r):
                all_freq[n] += 1
            for z in self.a.get_zodiacs(r):
                zod_freq[z] += 1
        max_freq = max(all_freq.values()) if all_freq else 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        
        # 获取当前年生肖年内校准的权重
        w = self._get_year_patterns()
        
        scores = {}
        for n in range(1, 50):
            s = 0.0
            
            # 周易五行亲和 (基于当前年生肖年映射)
            s += iching_affinity(n, last_date) * w["iching_w"]
            
            # 避开近期正特号码 (跨年不变规律)
            if n in sp_recent_3: s -= w["recent_avoid"] * 2
            elif n in sp_recent_10: s -= w["recent_avoid"]
            
            # 避开热门生肖 (同年内)
            z = num_to_zodiac(n, last_date)
            if z == last_zod: s -= w["zod_avoid"]
            if z in recent_5_zod: s -= w["zod_avoid"] * 0.6
            s -= (zod_freq.get(z, 0) / max_zod) * 8
            
            # 避开高频号码 (跨年不变)
            s -= (all_freq.get(n, 0) / max_freq) * w["freq_avoid"]
            
            # 迷信号码
            if n in {6,8,16,18,26,28,33,36,38}: s -= 5
            
            scores[n] = s
        
        return sorted(range(1, 50), key=lambda x: scores.get(x, 0), reverse=True)[:count]

# Run backtest
warmup = 60
h, t = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = ZodiacYearAwarePredictor(a).predict_specials(8)
        t += 1
        if actual[6] in pred: h += 1
    except Exception as e: pass

print(f"ZodiacYearAware: {h}/{t} = {h/t*100:.1f}%")

# Random
random.seed(99)
hr, tr = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    tr += 1
    if actual[6] in random.sample(range(1,50), 8): hr += 1
print(f"Random:          {hr}/{tr} = {hr/tr*100:.1f}%")

# Per-Zodiac-Year breakdown
print("\n--- Per Zodiac Year ---")
for yz_name in ["兔","龍","蛇","馬"]:
    yz_data_all = [r for r in data if _get_year_zodiac(r.get("openTime","")) == yz_name]
    if len(yz_data_all) < warmup + 5: continue
    yz_data = sorted(yz_data_all, key=lambda x: int(x.get("expect",0)))
    
    hy, ty = 0, 0
    for idx in range(warmup, len(yz_data)):
        # Train on all data before this record (can include prior years)
        test_record = yz_data[idx]
        test_date = test_record.get("openTime","")
        train = [r for r in data if int(r.get("expect",0)) < int(test_record.get("expect",0))]
        train.sort(key=lambda x: int(x.get("expect",0)))
        
        actual = [int(x) for x in test_record.get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        
        try:
            a = Analyzer(train)
            pred = ZodiacYearAwarePredictor(a).predict_specials(8)
            ty += 1
            if actual[6] in pred: hy += 1
        except: pass
    
    rate = hy/ty*100 if ty > 0 else 0
    bar = "#"*int(rate)
    print(f"  {yz_name}年 ({ty}期): {hy}/{ty} = {rate:.1f}% {bar}")

print()
print("="*60)
print("ZODIAC YEAR ANALYSIS COMPLETE")
print("="*60)