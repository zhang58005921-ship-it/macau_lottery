"""V2 Backtest — 聚焦有效信号, 庄家利润函数重构"""
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
    return ZODIAC_MAP[(zi - (n - 1)) % 12]

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

# ============================================================
# V2 策略1: 冷号猎手V2 — 严格冷号 (从未作为正特 / 间隔>80期)
# ============================================================
class ColdHunterV2:
    def __init__(self, a): self.a = a
    def predict_specials(self, count=8):
        intervals = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999: intervals[sp] = i
        # 选间隔最大的count个
        return sorted(range(1,50), key=lambda n: intervals[n], reverse=True)[:count]

# ============================================================
# V2 策略2: 庄家利润引擎V2 — 重写, 去Markov/MonteCarlo噪音
# 核心逻辑: 
#   BONUS (house wants to open):
#     - 冷号: 无人押注 → +score
#     - 远离近期正特: 避免重复 → +score
#     - 周易相生: 五行有利 → +score
#   PENALTY (house avoids):
#     - 热号(所有7位高频出现): 大众追 → -score
#     - 迷信号码: 大众心理锚定 → -score
#     - 单双/波色连势超4期: 赌反转的太多 → 庄家继续 → 微调
# ============================================================
class AdversarialV2:
    def __init__(self, a): self.a = a
    
    def _get_intervals(self):
        """每个号码距上次正特的间隔"""
        intervals = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999: intervals[sp] = i
        return intervals
    
    def _get_all_freq(self, window=20):
        """所有7个号码的频率(不只是正特)"""
        c = Counter()
        for r in self.a.data[-window:]:
            for n in self.a.get_numbers(r):
                c[n] += 1
        return c
    
    def _superstition_penalty(self, n):
        """迷信号码罚分"""
        p = 0
        if n in {6,8,16,18,26,28,33,36,38}: p += 8   # 吉利数字
        if n in {4,14,24,34,44}: p += 5                # 4=死
        if n % 11 == 0: p += 4                          # 对称号
        if n % 10 == n // 10: p += 3                     # 叠号
        return p
    
    def predict_specials(self, count=8):
        intervals = self._get_intervals()
        all_freq = self._get_all_freq(20)
        sp = self.a.special_code_history(30)
        last_date = self.a.data[-1].get("openTime", "") if self.a.data else ""
        
        # 正特惩罚: 最近期正特严重扣分
        sp_recent = set()
        for i, s in enumerate(sp):
            if i < 10: sp_recent.add(s["number"])
        
        # 生肖热度
        recent_zod = Counter()
        for r in self.a.data[-15:]:
            for z in self.a.get_zodiacs(r):
                recent_zod[z] += 1
        
        # 单双连势
        oes = ["单" if s["number"]%2 else "双" for s in sp[-15:]]
        oe_streak, last_oe = 0, oes[-1]
        for o in reversed(oes):
            if o == last_oe: oe_streak += 1
            else: break
        
        # 波色连势
        waves = [num_to_wave(s["number"])[0] for s in sp[-15:]]
        wave_streak, last_wave = 0, waves[-1]
        for w in reversed(waves):
            if w == last_wave: wave_streak += 1
            else: break
        
        scores = {}
        max_freq = max(all_freq.values()) if all_freq else 1
        max_gap = max(intervals.values()) if intervals else 999
        
        for n in range(1, 50):
            score = 0.0
            
            # === COLD BONUS (核心优势) ===
            gap = intervals[n]
            if gap >= 80: score += 40       # 极度冷号
            elif gap >= 50: score += 25     # 很冷
            elif gap >= 30: score += 12     # 偏冷
            elif gap >= 20: score += 5      # 微冷
            
            # === ALL-FREQ PENALTY (庄家避开热门) ===
            freq = all_freq.get(n, 0)
            score -= (freq / max_freq) * 35  # 大众热度越高, 庄家越避开
            
            # === RECENT SPECIAL PENALTY ===
            if n in sp_recent:
                # 越近期越罚
                for i, s in enumerate(sp):
                    if s["number"] == n:
                        if i < 3: score -= 40
                        elif i < 6: score -= 25
                        elif i < 10: score -= 10
                        break
            
            # === SUPERSTITION PENALTY ===
            score -= self._superstition_penalty(n)
            
            # === ZODIAC HEAT PENALTY ===
            z = num_to_zodiac(n, last_date)
            z_heat = recent_zod.get(z, 0)
            if z_heat >= 5: score -= 15
            elif z_heat >= 3: score -= 8
            
            # === OE STREAK (庄家继续同向, 杀反转赌徒) ===
            oe_n = "单" if n%2 else "双"
            if oe_streak >= 4:
                if oe_n == last_oe: score += 8     # 庄家继续
                else: score -= 12                   # 赌反转的大众 → 庄家避开
            
            # === WAVE STREAK ===
            wave_n = num_to_wave(n)[0]
            if wave_streak >= 3:
                if wave_n == last_wave: score += 5
                else: score -= 8
            
            # === I CHING AFFINITY ===
            score += iching_affinity(n, last_date) * 10
            
            scores[n] = score
        
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]


# ============================================================
# V2 策略3: 冷热混合 — 4冷+2非近特+2生肖轮动
# ============================================================
class HybridV2:
    def __init__(self, a): self.a = a
    
    def predict_specials(self, count=8):
        intervals = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999: intervals[sp] = i
        
        sp_hist = self.a.special_code_history(30)
        sp_recent_15 = set(s["number"] for s in sp_hist[:15])
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        
        picks = []
        
        # 4个冷号
        cold = sorted(range(1,50), key=lambda n: intervals[n], reverse=True)
        for n in cold:
            if n not in picks:
                picks.append(n)
            if len(picks) >= 4: break
        
        # 2个非近特+周易有利
        candidates = []
        for n in range(1,50):
            if n in picks: continue
            if n not in sp_recent_15:
                score = intervals.get(n, 0) * 0.5 + iching_affinity(n, last_date) * 10
                if intervals[n] > 10:
                    candidates.append((n, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        for n, _ in candidates:
            if n not in picks:
                picks.append(n)
            if len(picks) >= 6: break
        
        # 2个生肖轮动(避开最近3期正特生肖)
        recent_3_zod = set()
        for s in sp_hist[:3]:
            recent_3_zod.add(s["zodiac"])
        
        zod_candidates = []
        for n in range(1,50):
            if n in picks: continue
            z = num_to_zodiac(n, last_date)
            if z not in recent_3_zod:
                zod_candidates.append((n, iching_affinity(n, last_date), intervals.get(n, 999)))
        zod_candidates.sort(key=lambda x: x[1]*3 + x[2]*0.3, reverse=True)
        for n, _, _ in zod_candidates:
            if n not in picks:
                picks.append(n)
            if len(picks) >= 8: break
        
        # 补齐
        for n in range(1,50):
            if n not in picks:
                picks.append(n)
            if len(picks) >= count: break
        
        return picks[:count]


# ============================================================
# V2 策略4: 8线策略 — 每条线独立选1个, 确保8个不同
# 重写每条线, 只用经过验证的有效信号
# ============================================================
class EightLineV2:
    def __init__(self, a): self.a = a
    
    def _intervals(self):
        iv = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if iv.get(sp, 999) == 999: iv[sp] = i
        return iv
    
    def line1_cold(self):
        """冷号: 间隔最大"""
        iv = self._intervals()
        return max(range(1,50), key=lambda n: iv[n])
    
    def line2_super_cold(self):
        """极冷号: 间隔>=80 或 从未出现"""
        iv = self._intervals()
        super_cold = [n for n in range(1,50) if iv[n] >= 80]
        if super_cold:
            return max(super_cold, key=lambda n: iv[n])
        return max(range(1,50), key=lambda n: iv[n])
    
    def line3_non_recent(self):
        """避开所有近期正特"""
        sp_hist = self.a.special_code_history(20)
        sp_nums = set(s["number"] for s in sp_hist)
        iv = self._intervals()
        candidates = [n for n in range(1,50) if n not in sp_nums]
        if candidates:
            return max(candidates, key=lambda n: iv[n])
        return 25
    
    def line4_cold_zodiac(self):
        """冷号且生肖五行相生"""
        iv = self._intervals()
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        sp_hist = self.a.special_code_history(5)
        recent_zod = set(s["zodiac"] for s in sp_hist)
        candidates = [(n, iv[n] + iching_affinity(n, last_date) * 5) 
                     for n in range(1,50) if num_to_zodiac(n, last_date) not in recent_zod]
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]
        return max(range(1,50), key=lambda n: iv[n])
    
    def line5_crowd_avoid(self):
        """避开所有位置高频号"""
        all_freq = Counter()
        for r in self.a.data[-20:]:
            for n in self.a.get_numbers(r):
                all_freq[n] += 1
        iv = self._intervals()
        # 低频+冷
        candidates = [(n, -all_freq.get(n,0)*3 + iv[n]*0.5) for n in range(1,50)]
        return max(candidates, key=lambda x: x[1])[0]
    
    def line6_iching_pure(self):
        """纯周易: 五行最有利+避开近5期正特生肖"""
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        sp_hist = self.a.special_code_history(5)
        recent_zod = set(s["zodiac"] for s in sp_hist)
        candidates = [(n, iching_affinity(n, last_date)) for n in range(1,50)
                     if num_to_zodiac(n, last_date) not in recent_zod]
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]
        return max(range(1,50), key=lambda n: iching_affinity(n, last_date))
    
    def line7_oe_house(self):
        """单双庄家策略: 连势超4→继续; 连势=2→反转"""
        sp_hist = self.a.special_code_history(10)
        oes = ["单" if s["number"]%2 else "双" for s in sp_hist]
        streak, last = 0, oes[-1]
        for o in reversed(oes):
            if o == last: streak += 1
            else: break
        if streak >= 4:
            target = last  # 继续
        else:
            target = "双" if last == "单" else "单"  # 反转
        iv = self._intervals()
        candidates = [n for n in range(1,50) if ("单" if n%2 else "双") == target]
        if candidates:
            return max(candidates, key=lambda n: iv[n])
        return 25
    
    def line8_wave_house(self):
        """波色庄家策略: 跟单双逻辑"""
        sp_hist = self.a.special_code_history(10)
        waves = [num_to_wave(s["number"])[0] for s in sp_hist]
        streak, last = 0, waves[-1]
        for w in reversed(waves):
            if w == last: streak += 1
            else: break
        if streak >= 3:
            target = last
        else:
            all_w = ["红波","蓝波","绿波"]
            all_w.remove(last)
            c = Counter(waves[-10:])
            target = min(all_w, key=lambda w: c.get(w, 0))
        iv = self._intervals()
        candidates = [n for n in range(1,50) if num_to_wave(n)[0] == target]
        if candidates:
            return max(candidates, key=lambda n: iv[n])
        return 25
    
    def predict_specials(self, count=8):
        lines = [self.line1_cold, self.line2_super_cold, self.line3_non_recent,
                 self.line4_cold_zodiac, self.line5_crowd_avoid, self.line6_iching_pure,
                 self.line7_oe_house, self.line8_wave_house]
        picks = []
        for fn in lines[:count]:
            try:
                n = fn()
                if n not in picks:
                    picks.append(n)
                else:
                    # 冲突: 选次优
                    iv = self._intervals()
                    for alt in sorted(range(1,50), key=lambda x: iv[x], reverse=True):
                        if alt not in picks:
                            picks.append(alt)
                            break
            except:
                for alt in range(1,50):
                    if alt not in picks:
                        picks.append(alt)
                        break
        return picks[:count]


# ===== RUN BACKTEST =====
print("="*60)
print("V2 BACKTEST — 聚焦有效信号, 去Markov/MonteCarlo噪音")
print("="*60)

warmup = 80
models = {
    "ColdHunterV2": ColdHunterV2,
    "AdversarialV2 (House)": AdversarialV2,
    "HybridV2 (冷+周易+生肖)": HybridV2,
    "EightLineV2": EightLineV2,
}

for name, cls in models.items():
    h, t = 0, 0
    for idx in range(warmup, len(data)):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        try:
            pred = cls(a).predict_specials(8)
            t += 1
            if actual[6] in pred: h += 1
        except: pass
    rate = h/t*100 if t else 0
    bar = "#"*int(rate)
    print(f"  {name}: {h}/{t} = {rate:.1f}% {bar}")

# Random
random.seed(99)
h3, t3 = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    t3 += 1
    if actual[6] in random.sample(range(1,50), 8): h3 += 1
print(f"  Random baseline:       {h3}/{t3} = {h3/t3*100:.1f}%")

# Recent 50
print()
print("--- Recent 50 Window ---")
w_start = max(0, len(data) - 50)
for name, cls in models.items():
    h, t = 0, 0
    for idx in range(w_start, len(data)):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        try:
            if actual[6] in cls(a).predict_specials(8): h += 1
            t += 1
        except: pass
    rate = h/t*100 if t else 0
    print(f"  {name}: {h}/{t} = {rate:.1f}%")

# 8线各线单独
print()
print("--- EightLineV2 Per-Line ---")
line_names = ["L1_Cold","L2_SuperCold","L3_NonRecent","L4_ColdZodiac",
              "L5_CrowdAvoid","L6_IChingPure","L7_OE_House","L8_Wave_House"]
line_hits = [0]*8
line_total = 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    elp = EightLineV2(a)
    line_total += 1
    for li, fn in enumerate([elp.line1_cold, elp.line2_super_cold, elp.line3_non_recent,
                              elp.line4_cold_zodiac, elp.line5_crowd_avoid, elp.line6_iching_pure,
                              elp.line7_oe_house, elp.line8_wave_house]):
        try:
            if actual[6] == fn(): line_hits[li] += 1
        except: pass
for i, name in enumerate(line_names):
    rate = line_hits[i]/line_total*100 if line_total else 0
    print(f"  {name}: {line_hits[i]}/{line_total} = {rate:.1f}% (random=2.0%)")

print()
print("="*60)
print("V2 BACKTEST COMPLETE")
print("="*60)