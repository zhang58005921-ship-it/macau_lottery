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
print(f"Loaded {len(data)} unique records")

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
    def predict_triple_zodiac(self, last_n=60):
        recent = self.data[-last_n:]
        pair_count = Counter()
        for r in recent:
            nums = self.get_numbers(r)
            zodiacs = [num_to_zodiac(n, r.get("openTime","")) for n in nums]
            for i in range(len(zodiacs)):
                for j in range(i+1, len(zodiacs)):
                    for k in range(j+1, len(zodiacs)):
                        pair_count[tuple(sorted([zodiacs[i],zodiacs[j],zodiacs[k]]))] += 1
        if pair_count:
            top = pair_count.most_common(1)[0][0]
            return list(top)
        return ZODIAC_MAP[:3]
    def predict_quad_zodiac(self, last_n=60):
        recent = self.data[-last_n:]
        pair_count = Counter()
        for r in recent:
            nums = self.get_numbers(r)
            zodiacs = [num_to_zodiac(n, r.get("openTime","")) for n in nums]
            for i in range(len(zodiacs)):
                for j in range(i+1, len(zodiacs)):
                    for k in range(j+1, len(zodiacs)):
                        for l in range(k+1, len(zodiacs)):
                            pair_count[tuple(sorted([zodiacs[i],zodiacs[j],zodiacs[k],zodiacs[l]]))] += 1
        if pair_count:
            top = pair_count.most_common(1)[0][0]
            return list(top)
        return ZODIAC_MAP[:4]
    def predict_special_codes(self, count=8):
        sc = self.special_frequency(100)
        return [n for n, _ in Counter(sc).most_common(count)]

class AdversarialPredictor:
    def __init__(self, a):
        self.a = a
    def _signal_markov(self):
        scores = Counter()
        recent = self.a.data[-100:]
        trans = defaultdict(Counter)
        for i in range(len(recent)-1):
            n1 = self.a.get_numbers(recent[i])
            n2 = self.a.get_numbers(recent[i+1])
            if len(n1)>=7 and len(n2)>=7:
                trans[n1[6]][n2[6]] += 1
                oe1 = "单" if n1[6]%2 else "双"
                trans[oe1][n2[6]] += 0.5
                w1 = num_to_wave(n1[6])[0]
                trans["W:"+w1][n2[6]] += 0.5
        ln = self.a.get_numbers(self.a.data[-1]) if self.a.data else []
        if len(ln)>=7:
            last_sp = ln[6]
            last_oe = "单" if last_sp%2 else "双"
            last_w = num_to_wave(last_sp)[0]
            for key in [last_sp, last_oe, "W:"+last_w]:
                if key in trans:
                    for dst, cnt in trans[key].most_common():
                        scores[dst] += cnt
        return scores
    def _signal_ema(self):
        sc = Counter()
        recent = self.a.data[-80:]
        for i, r in enumerate(reversed(recent)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7: sc[nums[6]] += 0.90 ** i
        return sc
    def _signal_montecarlo(self, sims=2000):
        sc = self.a.special_frequency(80)
        if not sc: return Counter()
        items = list(sc.keys())
        weights = [sc[x] for x in items]
        total = sum(weights)
        probs = [w/total for w in weights]
        results = Counter()
        random.seed(42)
        for _ in range(sims):
            sampled = set()
            while len(sampled) < min(8, len(items)):
                sampled.add(random.choices(items, weights=probs)[0])
            for n in sampled: results[n] += 1
        return results
    def _signal_cold_hot(self):
        intervals = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999:
                    intervals[sp] = i
        return intervals
    def _crowd_heatmap(self, window=15):
        c = Counter()
        for r in self.a.data[-window:]:
            for n in self.a.get_numbers(r):
                c["num:"+str(n)] += 1
        for r in self.a.data[-window:]:
            for z in set(self.a.get_zodiacs(r)):
                c["zod:"+z] += 1
        sp = self.a.special_code_history(window)
        oes = ["单" if s["number"]%2 else "双" for s in sp]
        streak, last_oe = 0, oes[-1]
        for o in reversed(oes):
            if o == last_oe: streak += 1
            else: break
        c["_oe_streak"] = streak
        c["_oe_last"] = 1 if last_oe == "单" else 0
        waves = [num_to_wave(s["number"])[0] for s in sp]
        streak_w, last_w = 0, waves[-1]
        for w in reversed(waves):
            if w == last_w: streak_w += 1
            else: break
        c["_wave_streak"] = streak_w
        c["_wave_last"] = {"红波":0, "蓝波":1, "绿波":2}.get(last_w, 0)
        sizes = ["小" if s["number"]<=24 else "大" for s in sp]
        c["_size_small"] = sizes[-10:].count("小")
        c["_size_big"] = sizes[-10:].count("大")
        return c
    def _crowd_superstition(self, n):
        s = 0
        if n in {6,8,16,18,26,28,33,36,38}: s += 3
        if n % 11 == 0: s += 2
        if n % 10 == n // 10: s += 1
        return s
    def predict_specials(self, count=8):
        sig_markov = self._signal_markov()
        sig_monte = self._signal_montecarlo()
        sig_ema = self._signal_ema()
        sig_intervals = self._signal_cold_hot()
        crowd = self._crowd_heatmap(15)
        sp = self.a.special_code_history(20)
        sp_penalty = {}
        for i, s in enumerate(sp):
            n = s["number"]
            if i <= 2: sp_penalty[n] = -50
            elif i <= 5: sp_penalty[n] = -30
            elif i <= 10: sp_penalty[n] = -15
            elif i <= 15: sp_penalty[n] = -5
        def norm(c, default=0.0):
            if not c: return lambda x: default
            mx = max(c.values()) if c else 1
            return lambda x: c.get(x, 0) / mx
        n_markov = norm(sig_markov)
        n_monte = norm(sig_monte)
        n_ema = norm(sig_ema)
        scores = {}
        last_date = self.a.data[-1].get("openTime", "") if self.a.data else ""
        for n in range(1, 50):
            risk = 0.0
            risk -= n_markov(n) * 12
            risk -= n_monte(n) * 10
            risk -= n_ema(n) * 8
            gap = sig_intervals.get(n, 999)
            if gap > 50: risk += 20
            elif gap > 30: risk += 12
            elif gap > 15: risk += 5
            crowd_n = crowd.get("num:"+str(n), 0) / max(1, max(crowd.get("num:"+str(x), 0) for x in range(1,50)))
            risk -= crowd_n * 25
            z = num_to_zodiac(n, last_date)
            crowd_zod = crowd.get("zod:"+z, 0)
            if crowd_zod >= 4: risk -= 10
            elif crowd_zod >= 2: risk -= 5
            oe_n = "单" if n%2 else "双"
            oe_is_last = (1 if oe_n=="单" else 0) == crowd.get("_oe_last", 0)
            oe_streak = crowd.get("_oe_streak", 0)
            if oe_streak >= 4 and oe_is_last: risk += 6
            elif oe_streak >= 4 and not oe_is_last: risk -= 10
            wave_idx = {"红波":0, "蓝波":1, "绿波":2}.get(num_to_wave(n)[0], 0)
            wave_is_last = wave_idx == crowd.get("_wave_last", 0)
            wave_streak = crowd.get("_wave_streak", 0)
            if wave_streak >= 3 and wave_is_last: risk += 4
            elif wave_streak >= 3 and not wave_is_last: risk -= 6
            small = crowd.get("_size_small", 5)
            big = crowd.get("_size_big", 5)
            if n <= 24 and small >= 7: risk -= 5
            elif n > 24 and big >= 7: risk -= 5
            risk -= self._crowd_superstition(n) * 3
            risk += sp_penalty.get(n, 0)
            risk += iching_affinity(n, last_date) * 8
            scores[n] = risk
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

class EightLinePredictor:
    def __init__(self, a):
        self.a = a
    def line1_cold_hunter(self):
        intervals = {n: 999 for n in range(1,50)}
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999: intervals[sp] = i
        return max(range(1,50), key=lambda n: intervals[n])
    def line2_crowd_killer(self):
        c = Counter()
        for r in self.a.data[-15:]:
            for n in self.a.get_numbers(r): c[n] += 1
        appeared = set(n for n in c if c[n] > 0)
        recent3_all = set()
        for r in self.a.data[-3:]:
            for n in self.a.get_numbers(r): recent3_all.add(n)
        candidates = [n for n in appeared if c[n] <= 2 and n not in recent3_all]
        if candidates: return min(candidates, key=lambda n: c[n])
        return min(appeared, key=lambda n: c[n]) if appeared else 25
    def line3_special_killer(self):
        sp_20 = self.a.special_code_history(20)
        sp_nums = set(s["number"] for s in sp_20)
        candidates = [n for n in range(1,50) if n not in sp_nums]
        if candidates: return random.choice(candidates)
        return random.randint(1,49)
    def line4_markov_surprise(self):
        recent = self.a.data[-100:]
        trans = Counter()
        for i in range(len(recent)-1):
            n1 = self.a.get_numbers(recent[i])
            n2 = self.a.get_numbers(recent[i+1])
            if len(n1)>=7 and len(n2)>=7: trans[(n1[6], n2[6])] += 1
        ln = self.a.get_numbers(self.a.data[-1])
        if len(ln)>=7:
            last = ln[6]
            all_trans = {n: trans.get((last,n),0) for n in range(1,50)}
            return min(range(1,50), key=lambda n: all_trans.get(n, 99))
        return 25
    def line5_zodiac_rotator(self):
        sp = self.a.special_code_history(5)
        last_date = self.a.data[-1].get("openTime","") if self.a.data else ""
        if sp:
            last_z = sp[-1]["zodiac"]
            candidates = [(n, iching_affinity(n, last_date)) for n in range(1,50) 
                         if num_to_zodiac(n, last_date) != last_z and iching_affinity(n, last_date) > 0]
            if candidates: return max(candidates, key=lambda x: x[1])[0]
        return random.randint(1,49)
    def line6_wave_reverser(self):
        sp = self.a.special_code_history(10)
        waves = [num_to_wave(s["number"])[0] for s in sp]
        c = Counter(waves)
        least = min(["红波","蓝波","绿波"], key=lambda w: c.get(w,0))
        candidates = [n for n in range(1,50) if num_to_wave(n)[0] == least]
        return random.choice(candidates) if candidates else 25
    def line7_oe_breaker(self):
        sp = self.a.special_code_history(10)
        oe = ["单" if s["number"]%2 else "双" for s in sp]
        streak, last = 0, oe[-1]
        for o in reversed(oe):
            if o == last: streak += 1
            else: break
        target = ("双" if last == "单" else "单") if streak >= 3 else last
        candidates = [n for n in range(1,50) if ("单" if n%2 else "双") == target]
        return random.choice(candidates) if candidates else 25
    def line8_gap_closer(self):
        intervals = {}
        last_positions = {}
        for n in range(1,50): intervals[n] = []
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if sp not in last_positions: last_positions[sp] = i
                else:
                    intervals[sp].append(i - last_positions[sp])
                    last_positions[sp] = i
        best_n, best_diff = 25, 999
        for n in range(1,50):
            if intervals[n]:
                avg = sum(intervals[n]) / len(intervals[n])
                current = last_positions.get(n, 999)
                diff = abs(current - avg)
                if diff < best_diff:
                    best_diff = diff
                    best_n = n
        return best_n
    def predict_specials(self, count=8):
        lines = [self.line1_cold_hunter, self.line2_crowd_killer, self.line3_special_killer,
                 self.line4_markov_surprise, self.line5_zodiac_rotator, self.line6_wave_reverser,
                 self.line7_oe_breaker, self.line8_gap_closer]
        picks = []
        for fn in lines[:count]:
            try:
                n = fn()
                if n not in picks: picks.append(n)
                else: picks.append(random.randint(1,49))
            except: picks.append(random.randint(1,49))
        return picks[:count]

# ===== BACKTEST =====
print()
print("="*60)
print("HONEST SLIDING WINDOW BACKTEST (no data leakage)")
print("="*60)

warmup = 80

# Adversarial
h1, t1 = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = AdversarialPredictor(a).predict_specials(8)
        t1 += 1
        if actual[6] in pred: h1 += 1
    except: pass
print(f"Adversarial (House+IChing): {h1}/{t1} = {h1/t1*100:.1f}%")

# EightLine
h2, t2 = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = EightLinePredictor(a).predict_specials(8)
        t2 += 1
        if actual[6] in pred: h2 += 1
    except: pass
print(f"EightLine:               {h2}/{t2} = {h2/t2*100:.1f}%")

# Random
random.seed(99)
h3, t3 = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    t3 += 1
    if actual[6] in random.sample(range(1,50), 8): h3 += 1
print(f"Random baseline:         {h3}/{t3} = {h3/t3*100:.1f}% (theory 16.3%)")

# Recent 50
print()
print("--- Recent 50 Window ---")
w_start = max(0, len(data) - 50)
h_adv, t_adv = 0, 0
h_8l, t_8l = 0, 0
for idx in range(w_start, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        if actual[6] in AdversarialPredictor(a).predict_specials(8): h_adv += 1
        t_adv += 1
        if actual[6] in EightLinePredictor(a).predict_specials(8): h_8l += 1
        t_8l += 1
    except: pass
print(f"Adversarial (recent 50): {h_adv}/{t_adv} = {h_adv/t_adv*100:.1f}%")
print(f"EightLine (recent 50):   {h_8l}/{t_8l} = {h_8l/t_8l*100:.1f}%")

# Per-line breakdown
print()
print("--- Per-Line Hit Rate ---")
line_names = ["L1_ColdHunter","L2_CrowdKiller","L3_SpecialKiller","L4_MarkovSurprise",
              "L5_ZodiacRotator","L6_WaveReverser","L7_OE_Breaker","L8_GapCloser"]
line_hits = [0]*8
line_total = 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    elp = EightLinePredictor(a)
    line_total += 1
    for li, fn in enumerate([elp.line1_cold_hunter, elp.line2_crowd_killer, elp.line3_special_killer,
                              elp.line4_markov_surprise, elp.line5_zodiac_rotator, elp.line6_wave_reverser,
                              elp.line7_oe_breaker, elp.line8_gap_closer]):
        try:
            if actual[6] == fn(): line_hits[li] += 1
        except: pass
for i, name in enumerate(line_names):
    rate = line_hits[i]/line_total*100 if line_total else 0
    bar = "#"*int(rate)
    print(f"  {name}: {line_hits[i]}/{line_total} = {rate:.1f}% {bar}")

# Wave/OE auxiliary
wh, wt = 0, 0
oh, ot = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    sp = actual[6]
    sp_hist = a.special_code_history(30)
    waves = [num_to_wave(s["number"])[0] for s in sp_hist]
    wc = Counter(waves)
    least_w = min(["红波","蓝波","绿波"], key=lambda w: wc.get(w,0))
    wt += 1
    if num_to_wave(sp)[0] == least_w: wh += 1
    oe = ["单" if s["number"]%2 else "双" for s in sp_hist]
    oc = Counter(oe)
    least_o = min(["单","双"], key=lambda o: oc.get(o,0))
    ot += 1
    if ("单" if sp%2 else "双") == least_o: oh += 1
print(f"\nWave reversal: {wh}/{wt} = {wh/wt*100:.1f}%")
print(f"OE reversal:   {oh}/{ot} = {oh/ot*100:.1f}%")

print()
print("="*60)
print("BACKTEST COMPLETE")
print("="*60)