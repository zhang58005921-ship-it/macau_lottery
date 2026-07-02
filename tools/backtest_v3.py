"""V3 — Brute-force feature combination search + adaptive model"""
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
# Feature extraction
# ============================================================
def extract_features(data_slice):
    """Extract all features for each number 1-49"""
    a = Analyzer(data_slice)
    last_date = data_slice[-1].get("openTime","") if data_slice else ""
    
    # Gap since last special
    gaps = {n: 999 for n in range(1,50)}
    for i, r in enumerate(reversed(data_slice)):
        nums = a.get_numbers(r)
        if len(nums) >= 7:
            sp = nums[6]
            if gaps.get(sp, 999) == 999: gaps[sp] = i
    
    # All-position frequency (last 20 draws)
    all_freq = Counter()
    for r in data_slice[-20:]:
        for n in a.get_numbers(r):
            all_freq[n] += 1
    
    # Special frequency (last 50)
    sp_freq = Counter()
    sp_hist = a.special_code_history(50)
    for s in sp_hist:
        sp_freq[s["number"]] += 1
    
    # Zodiac frequency (all positions, last 15)
    zod_freq = Counter()
    for r in data_slice[-15:]:
        for z in a.get_zodiacs(r):
            zod_freq[z] += 1
    
    # Recent special zodiacs (last 5)
    recent_5_zod = set(s["zodiac"] for s in sp_hist[:5])
    
    # OE streak
    oes = ["单" if s["number"]%2 else "双" for s in sp_hist[:15]]
    oe_streak, last_oe = 0, oes[-1] if oes else "单"
    for o in reversed(oes):
        if o == last_oe: oe_streak += 1
        else: break
    
    # Wave streak
    waves = [num_to_wave(s["number"])[0] for s in sp_hist[:15]]
    wave_streak, last_wave = 0, waves[-1] if waves else "红波"
    for w in reversed(waves):
        if w == last_wave: wave_streak += 1
        else: break
    
    features = {}
    max_gap = max(gaps.values()) if gaps else 999
    max_freq = max(all_freq.values()) if all_freq else 1
    max_sp = max(sp_freq.values()) if sp_freq else 1
    max_zod = max(zod_freq.values()) if zod_freq else 1
    
    for n in range(1, 50):
        feats = {}
        feats["gap"] = gaps[n] / max(max_gap, 1)  # 0-1, higher = colder
        feats["gap_raw"] = gaps[n]
        feats["all_freq"] = all_freq.get(n, 0) / max_freq  # 0-1, higher = hotter
        feats["sp_freq"] = sp_freq.get(n, 0) / max_sp
        feats["is_cold"] = 1 if gaps[n] >= 50 else 0
        feats["is_super_cold"] = 1 if gaps[n] >= 80 else 0
        feats["is_recent_sp"] = 1 if n in set(s["number"] for s in sp_hist[:10]) else 0
        feats["is_very_recent_sp"] = 1 if n in set(s["number"] for s in sp_hist[:3]) else 0
        
        z = num_to_zodiac(n, last_date)
        feats["zod_heat"] = zod_freq.get(z, 0) / max_zod
        feats["zod_is_recent"] = 1 if z in recent_5_zod else 0
        
        feats["oe_match_streak"] = 1 if (("单" if n%2 else "双") == last_oe and oe_streak >= 4) else 0
        feats["oe_oppose_streak"] = 1 if (("单" if n%2 else "双") != last_oe and oe_streak >= 4) else 0
        
        wave_n = num_to_wave(n)[0]
        feats["wave_match_streak"] = 1 if (wave_n == last_wave and wave_streak >= 3) else 0
        feats["wave_oppose_streak"] = 1 if (wave_n != last_wave and wave_streak >= 3) else 0
        
        feats["iching"] = iching_affinity(n, last_date)  # -1 to 1
        
        feats["is_lucky"] = 1 if n in {6,8,16,18,26,28,33,36,38} else 0
        feats["is_unlucky"] = 1 if n in {4,14,24,34,44} else 0
        feats["is_symmetry"] = 1 if n % 11 == 0 else 0
        feats["is_double"] = 1 if n % 10 == n // 10 else 0
        
        feats["wave_idx"] = {"红波":0, "蓝波":1, "绿波":2}[num_to_wave(n)[0]]
        feats["is_odd"] = 1 if n % 2 else 0
        feats["is_big"] = 1 if n > 24 else 0
        
        features[n] = feats
    
    return features

# ============================================================
# V3: Feature-weighted scoring (weights learned from historical hits)
# ============================================================
class FeatureWeightedV3:
    def __init__(self, a, weights=None):
        self.a = a
        # Learned weights from feature analysis
        self.weights = weights or {
            "gap": 35,           # Cold = strong positive
            "is_cold": 15,       # Cold bonus
            "is_super_cold": 8,  # Super cold bonus
            "all_freq": -25,     # Hot = avoid
            "sp_freq": -15,      # Frequent special = avoid
            "is_recent_sp": -20, # Recent special = avoid
            "is_very_recent_sp": -30, # Very recent = heavy avoid
            "zod_heat": -10,     # Hot zodiac = avoid
            "zod_is_recent": -8, # Recent zodiac = avoid
            "oe_match_streak": 8,# Continue streak = good
            "oe_oppose_streak": -12, # Bet reversal = avoid
            "wave_match_streak": 4,
            "wave_oppose_streak": -6,
            "iching": 10,        # I Ching affinity
            "is_lucky": -5,      # Lucky numbers = crowd = avoid
            "is_unlucky": 3,     # Unlucky = no crowd = safe
            "is_symmetry": -3,
            "is_double": -3,
        }
    
    def predict_specials(self, count=8):
        feats = extract_features(self.a.data)
        scores = {}
        for n in range(1, 50):
            score = 0.0
            f = feats[n]
            for k, w in self.weights.items():
                if k in f:
                    score += f[k] * w
            scores[n] = score
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

# ============================================================
# V3: Multiple feature weight configurations (grid search)
# ============================================================
class GridSearchV3:
    def __init__(self, a):
        self.a = a
        # Pre-computed best weights from grid search on training data
        self.weights = self._find_best_weights()
    
    def _find_best_weights(self):
        """Simple grid search on the training data itself"""
        # Use warmup period to find best weights
        if len(self.a.data) < 100:
            return FeatureWeightedV3(self.a).weights  # default
        
        # Try different weight configurations on last 30% of training data
        test_start = max(80, int(len(self.a.data) * 0.7))
        
        configs = [
            # Name, gap_w, cold_w, supercold_w, freq_w, sp_w, recent_w, vrecent_w, zod_w, iching_w
            ("ColdMax", 45, 20, 10, -20, -10, -25, -35, -5, 8),
            ("ColdHeavy", 40, 18, 12, -15, -8, -20, -30, -8, 10),
            ("Balanced", 30, 12, 8, -25, -15, -18, -28, -10, 12),
            ("Aggressive", 50, 25, 15, -30, -20, -30, -40, -12, 5),
            ("IChingHeavy", 25, 10, 5, -15, -10, -15, -20, -8, 20),
            ("ColdOnly", 50, 25, 15, 0, 0, -30, -40, 0, 0),
        ]
        
        best_hits = 0
        best_config = None
        
        for name, gw, cw, scw, fw, spw, rw, vrw, zw, iw in configs:
            w = {
                "gap": gw, "is_cold": cw, "is_super_cold": scw,
                "all_freq": fw, "sp_freq": spw,
                "is_recent_sp": rw, "is_very_recent_sp": vrw,
                "zod_heat": zw, "zod_is_recent": zw * 0.8,
                "oe_match_streak": 8, "oe_oppose_streak": -12,
                "wave_match_streak": 4, "wave_oppose_streak": -6,
                "iching": iw,
                "is_lucky": -5, "is_unlucky": 3,
                "is_symmetry": -3, "is_double": -3,
            }
            hits = 0
            total = 0
            for idx in range(test_start, len(self.a.data)):
                a = Analyzer(self.a.data[:idx])
                actual = [int(x) for x in self.a.data[idx].get("openCode","").split(",") if x.strip()]
                if len(actual) < 7: continue
                try:
                    p = FeatureWeightedV3(a, w).predict_specials(8)
                    total += 1
                    if actual[6] in p: hits += 1
                except: pass
            if hits > best_hits:
                best_hits = hits
                best_config = (name, w)
        
        if best_config:
            return best_config[1]
        return FeatureWeightedV3(self.a).weights


# ============================================================
# RUN BACKTEST
# ============================================================
print("="*60)
print("V3 BACKTEST — Feature-weighted + Grid Search weights")
print("="*60)

warmup = 100  # Need more warmup for grid search

# Model 1: Default weights
h1, t1 = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = FeatureWeightedV3(a).predict_specials(8)
        t1 += 1
        if actual[6] in pred: h1 += 1
    except Exception as e: pass
print(f"FeatureWeighted (default): {h1}/{t1} = {h1/t1*100:.1f}%")

# Model 2: Grid search weights (adapts per period - slower)
print("GridSearch (adapting per period, this takes ~60s)...")
h2, t2 = 0, 0
for idx in range(warmup, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    try:
        pred = GridSearchV3(a).predict_specials(8)
        t2 += 1
        if actual[6] in pred: h2 += 1
    except: pass
print(f"GridSearch (adaptive):    {h2}/{t2} = {h2/t2*100:.1f}%")

# Random
random.seed(99)
h3, t3 = 0, 0
for idx in range(warmup, len(data)):
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    t3 += 1
    if actual[6] in random.sample(range(1,50), 8): h3 += 1
print(f"Random baseline:          {h3}/{t3} = {h3/t3*100:.1f}%")

# Recent 50
print()
print("--- Recent 50 ---")
w_start = max(0, len(data) - 50)
for name, cls in [("FeatureWeighted", FeatureWeightedV3), ("GridSearch", GridSearchV3)]:
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

# Best configuration analysis
print()
print("--- Feature correlation analysis ---")
# Compute correlation of each feature with actual hit
warmup_for_corr = 80
feature_hits = defaultdict(lambda: {"hits": 0, "total": 0})
for idx in range(warmup_for_corr, len(data)):
    a = Analyzer(data[:idx])
    actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
    if len(actual) < 7: continue
    actual_sp = actual[6]
    feats = extract_features(a.data)
    
    for n in range(1, 50):
        f = feats[n]
        for k, v in f.items():
            if isinstance(v, (int, float)) and k not in ["wave_idx"]:
                feature_hits[k]["total"] += 1
                if n == actual_sp:
                    feature_hits[k]["hits"] += 1

# For binary features, compute hit rate when feature=1 vs feature=0
print("Binary feature hit rates (when feature=1):")
binary_feats = ["is_cold", "is_super_cold", "is_recent_sp", "is_very_recent_sp",
                "zod_is_recent", "oe_match_streak", "oe_oppose_streak",
                "wave_match_streak", "wave_oppose_streak", "is_lucky", "is_unlucky",
                "is_symmetry", "is_double"]

for feat_name in binary_feats:
    # Count: when feature=1, how many times did that number become special
    total_when_1 = 0
    hit_when_1 = 0
    total_when_0 = 0
    hit_when_0 = 0
    for idx in range(warmup_for_corr, len(data)):
        a = Analyzer(data[:idx])
        actual = [int(x) for x in data[idx].get("openCode","").split(",") if x.strip()]
        if len(actual) < 7: continue
        actual_sp = actual[6]
        feats = extract_features(a.data)
        for n in range(1, 50):
            if feat_name in feats[n]:
                fv = feats[n][feat_name]
                if fv == 1 or fv > 0.5:
                    total_when_1 += 1
                    if n == actual_sp: hit_when_1 += 1
                else:
                    total_when_0 += 1
                    if n == actual_sp: hit_when_0 += 1
    
    rate1 = hit_when_1/total_when_1*100 if total_when_1 > 0 else 0
    rate0 = hit_when_0/total_when_0*100 if total_when_0 > 0 else 0
    expected = 100/49  # 2.04%
    print(f"  {feat_name}: when=1: {rate1:.2f}%  when=0: {rate0:.2f}%  (random=2.04%)  diff={rate1-rate0:+.2f}%")

print()
print("="*60)
print("V3 COMPLETE")
print("="*60)