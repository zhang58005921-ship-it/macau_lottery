"""MacauLottery Prediction Engine v4PRO
Pure prediction logic — no GUI dependencies.
Suitable for Android (Flet), Web, or CLI use.
"""
import sys, json, os, ssl, random, math, itertools
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
import threading
from . import macaujc_api

ssl._create_default_https_context = ssl._create_unverified_context

# Data file path
if getattr(sys, "frozen", False):
    _appdata = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "macau_lottery")
    os.makedirs(_appdata, exist_ok=True)
    DATA_FILE = os.path.join(_appdata, "macaujc_data.json")
else:
    DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "macaujc_data.json")

#!/usr/bin/env python3

import sys, json, os, ssl, random, math, itertools
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
import threading
import macaujc_api

ssl._create_default_https_context = ssl._create_unverified_context

# 数据文件路径: 开发模式用本地，EXE 模式用 AppData
if getattr(sys, 'frozen', False):
    _appdata = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'macau_lottery')
    os.makedirs(_appdata, exist_ok=True)
    DATA_FILE = os.path.join(_appdata, 'macaujc_data.json')
else:
    DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'macaujc_data.json')

# UI color constants
BG  = "#1a1a2e"
CARD= "#16213e"
BDR = "#0f3460"
TXT = "#e0e0e0"
SUB = "#8899aa"
ACC = "#e94560"
GLD = "#f5c518"
GRN = "#4ecca3"
RED = "#e94560"
ORG = "#f77f00"
PUR = "#7b2ff7"

ZODIAC_MAP = ['鼠','牛','虎','兔','龍','蛇','馬','羊','猴','雞','狗','豬']

# 农历新年日期 (生肖年切换点)
_LUNAR_NEW_YEAR = {
    "2023-01-22": "兔",
    "2024-02-10": "龍",
    "2025-01-29": "蛇",
    "2026-02-17": "馬"
}

ZODIAC_YEAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zodiac_year_config.json")

def _load_zodiac_year_config():
    if os.path.exists(ZODIAC_YEAR_FILE):
        with open(ZODIAC_YEAR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"2023": "兔", "2024": "龍", "2025": "蛇", "2026": "馬"}

def _get_zodiac_mapping():
    cfg = _load_zodiac_year_config()
    years = sorted(cfg.keys())
    return {y: cfg[y] for y in years}

_DEFAULT_ZODIAC_MAP = _get_zodiac_mapping()


def _get_year_zodiac(date_str):
    """根据日期返回该年本命生肖 (格式: YYYY-MM-DD HH:MM:SS)"""
    if not date_str or len(date_str) < 10:
        return "馬"  # 默认2026马年
    d = date_str[:10]
    zodiac = "馬"
    for date, z in sorted(_LUNAR_NEW_YEAR.items()):
        if d >= date:
            zodiac = z
    return zodiac

def num_to_zodiac(num, date_str=None):
    """号码→生肖，支持按农历年自动切换
    注意: 澳门彩使用逆序生肖循环 (zi - (n-1)) % 12, 而非标准 (zi + (n-1)) % 12"""
    n = int(num)
    if n < 1 or n > 49:
        return '?'
    if date_str is None:
        # 默认使用2026马年映射
        year_z = "馬"
    else:
        year_z = _get_year_zodiac(date_str)
    zi = ZODIAC_MAP.index(year_z)
    return ZODIAC_MAP[(zi - (n - 1)) % 12]

def num_to_wuxing(n):
    """五行映射: 金木水火土"""
    m = {1:'水',2:'水',3:'木',4:'木',5:'木',6:'火',7:'火',8:'火',9:'金',10:'金',11:'金',
         12:'水',13:'水',14:'木',15:'木',16:'木',17:'火',18:'火',19:'火',20:'金',21:'金',22:'金',
         23:'水',24:'水',25:'木',26:'木',27:'木',28:'火',29:'火',30:'火',31:'金',32:'金',33:'金',
         34:'水',35:'水',36:'木',37:'木',38:'木',39:'火',40:'火',41:'火',42:'金',43:'金',44:'金',
         45:'水',46:'水',47:'木',48:'木',49:'木'}
    return m.get(n,'?')
# 红蓝绿波映射
def num_to_wave(n):
    red   = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
    blue  = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
    green = {5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49}
    n = int(n)
    if n in red:   return ("红波", "#ff4444")
    if n in blue:  return ("蓝波", "#4488ff")
    if n in green: return ("绿波", "#44cc44")
    return ("?", "#888")

# 单双映射
def num_to_odd_even(n):
    n = int(n)
    return ("单", "#ff8c00") if n % 2 == 1 else ("双", "#8888ff")


def fetch_data(year=None):
    """使用 macaujc_api 获取历史数据"""
    years = [year] if year else [2023, 2024, 2025, 2026]
    return macaujc_api.fetch_all(years)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # 去重: 按expect保留首次出现
        seen = set()
        deduped = []
        for r in raw:
            exp = r.get("expect", "")
            if exp not in seen:
                seen.add(exp)
                deduped.append(r)
        if len(deduped) < len(raw):
            save_data(deduped)  # 回写去重后的数据
        return deduped
    return fetch_data()

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)


def sync_latest():
    """增量同步: 读本地DB → API拉最新 → 合并新数据 → 回写本地
    返回 (新增条数, 总条数)
    """
    # 1. 读取本地已有数据
    local_data = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
    
    existing_expects = {r.get("expect", "") for r in local_data}
    
    # 2. 从API拉取最新数据 (只拉当前年份)
    current_year = datetime.now().year
    try:
        api_data = macaujc_api.get_history(current_year)
    except Exception as e:
        print(f"API fetch failed: {e}")
        return 0, len(local_data)
    
    # 3. 合并: 只加入本地没有的期号
    new_count = 0
    for r in api_data:
        exp = r.get("expect", "")
        if exp and exp not in existing_expects:
            local_data.append(r)
            existing_expects.add(exp)
            new_count += 1
    
    # 4. 按 expect 排序
    local_data.sort(key=lambda x: x.get("expect", ""))
    
    # 5. 回写
    if new_count > 0:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(local_data, f, ensure_ascii=False, indent=2)
    
    return new_count, len(local_data)

class LotteryAnalyzer:
    def __init__(self, data):
        self.data = sorted(data, key=lambda x: int(x.get('expect', 0)))
    def get_numbers(self, r):
        c = r.get('openCode','')
        return [int(x) for x in c.split(',') if x.strip()] if c else []
    def get_zodiacs(self, r):
        dt = r.get("openTime", "")
        return [num_to_zodiac(n, dt) for n in self.get_numbers(r)]
    def frequency_stats(self, last_n=100):
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        nc, zc = Counter(), Counter()
        for r in recent:
            for n in self.get_numbers(r): nc[n] += 1
            for z in self.get_zodiacs(r): zc[z] += 1
        return nc, zc
    def hot_cold_numbers(self, last_n=50):
        nc, _ = self.frequency_stats(last_n)
        sn = sorted(range(1,50), key=lambda x: nc.get(x,0), reverse=True)
        return sn[:12], sn[-12:], dict(nc)
    def hot_cold_zodiac(self, last_n=50):
        _, zc = self.frequency_stats(last_n)
        sz = sorted(ZODIAC_MAP, key=lambda x: zc.get(x,0), reverse=True)
        return sz[:6], sz[-6:], dict(zc)
    def special_code_history(self, last_n=50):
        specials = []
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            if len(nums) >= 7:
                dt = r.get("openTime", "")
                specials.append({'expect': r.get('expect'), 'time': dt, 'number': nums[6], 'zodiac': num_to_zodiac(nums[6], dt)})
        return specials

    def wave_stats(self, last_n=100):
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        wc = Counter()
        for r in recent:
            for n in self.get_numbers(r):
                wave_name, _ = num_to_wave(n)
                wc[wave_name] += 1
        return wc
    def odd_even_stats(self, last_n=100):
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        oc = Counter()
        for r in recent:
            for n in self.get_numbers(r):
                oe, _ = num_to_odd_even(n)
                oc[oe] += 1
        return oc
    def wave_sequence(self, last_n=50):
        seq = []
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            waves = [num_to_wave(n)[0] for n in nums]
            seq.append({"expect": r.get("expect"), "nums": nums, "waves": waves})
        return seq
    def odd_even_sequence(self, last_n=50):
        seq = []
        for r in self.data[-last_n:]:
            nums = self.get_numbers(r)
            oes = [num_to_odd_even(n)[0] for n in nums]
            seq.append({"expect": r.get("expect"), "nums": nums, "oes": oes})
        return seq
    def _zodiac_coverage_score(self, last_n=60):
        """生肖综合得分：频率 + 间隔 + 号码权重 + 近期动量"""
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        zfreq = Counter()
        zrecent_weight = Counter()  # 近期加权频率
        for i, r in enumerate(reversed(recent)):
            for z in set(self.get_zodiacs(r)):
                zfreq[z] += 1
                w = 1.0 + (last_n - i) / last_n  # 近期权重更高
                zrecent_weight[z] += w
        zgap = {z: last_n for z in ZODIAC_MAP}
        for i, r in enumerate(reversed(recent)):
            for z in set(self.get_zodiacs(r)):
                if zgap.get(z) == last_n:
                    zgap[z] = i
        num_weight = {z: 5 if z == "鼠" else 4 for z in ZODIAC_MAP}
        total = len(recent)
        scores = {}
        for z in ZODIAC_MAP:
            freq_score = zfreq.get(z, 0) / max(total, 1)
            recent_score = zrecent_weight.get(z, 0) / max(sum(zrecent_weight.values()), 1) * 12
            gap_score = min(zgap.get(z, last_n) / 20.0, 1.2)
            nw = num_weight.get(z, 4) / 5.0
            # 重平衡：频率40% + 近期动量25% + 间隔25% + 号码权重10%
            scores[z] = freq_score * 0.40 + recent_score * 0.25 + gap_score * 0.25 + nw * 0.10
        return scores

    def _zodiac_pair_affinity(self, zodiacs, last_n=300):
        """计算生肖组合的共现亲和度"""
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        pair_count = Counter()
        for r in recent:
            z_set = set(self.get_zodiacs(r))
            z_list = sorted(z_set)
            for i in range(len(z_list)):
                for j in range(i + 1, len(z_list)):
                    pair_count[(z_list[i], z_list[j])] += 1
        return pair_count

    def predict_triple_zodiac(self, last_n=60):
        """三连肖: 枚举C(12,3)=220组合，找历史上共现频率最高的3生肖组合"""
        recent_n = min(last_n * 3, len(self.data))
        draw_zodiacs = []
        for r in self.data[-recent_n:]:
            zs = set(self.get_zodiacs(r))
            if len(zs) >= 3:
                draw_zodiacs.append(zs)
        if not draw_zodiacs:
            zfreq = Counter()
            for r in self.data[-recent_n:]:
                for z in set(self.get_zodiacs(r)):
                    zfreq[z] += 1
            return [z for z, _ in zfreq.most_common(3)]
        best_combo, best_count = None, -1
        for combo in itertools.combinations(ZODIAC_MAP, 3):
            combo_set = set(combo)
            count = sum(1 for zs in draw_zodiacs if combo_set.issubset(zs))
            if count > best_count:
                best_count = count
                best_combo = combo
        return list(best_combo)

    def predict_quad_zodiac(self, last_n=60):
        """四连肖: 枚举C(12,4)=495组合，找历史上共现频率最高的4生肖组合"""
        recent_n = min(last_n * 4, len(self.data))
        draw_zodiacs = []
        for r in self.data[-recent_n:]:
            zs = set(self.get_zodiacs(r))
            if len(zs) >= 4:
                draw_zodiacs.append(zs)
        if not draw_zodiacs:
            # 回退: 三连肖 + 最优第四肖
            triple = self.predict_triple_zodiac(last_n)
            zfreq = Counter()
            for r in self.data[-recent_n:]:
                for z in set(self.get_zodiacs(r)):
                    zfreq[z] += 1
            remaining = [(z, zfreq.get(z, 0)) for z in ZODIAC_MAP if z not in triple]
            remaining.sort(key=lambda x: x[1], reverse=True)
            return triple + [remaining[0][0]]
        best_combo, best_count = None, -1
        for combo in itertools.combinations(ZODIAC_MAP, 4):
            combo_set = set(combo)
            count = sum(1 for zs in draw_zodiacs if combo_set.issubset(zs))
            if count > best_count:
                best_count = count
                best_combo = combo
        return list(best_combo)
    def special_frequency(self, last_n=100):
        """只统计特码(第7位)的频率，不包含前6位平特"""
        recent = self.data[-last_n:] if len(self.data) > last_n else self.data
        sc = Counter()
        for r in recent:
            nums = self.get_numbers(r)
            if len(nums) >= 7:
                sc[nums[6]] += 1
        return sc

    def _special_intervals(self):
        """每个号码距离上次作为正特出现的间隔期数(间隔越大越冷)"""
        intervals = {}
        for n in range(1, 50):
            intervals[n] = 999  # 从未出现过
        for i, r in enumerate(reversed(self.data)):
            nums = self.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999:
                    intervals[sp] = i
        return intervals

    def predict_special_codes(self, count=8):
        nc = self.special_frequency(100)
        sp = self.special_code_history(30)
        rsp = set(s['number'] for s in sp[-20:])
        appeared = set()
        for r in self.data[-60:]: appeared.update(self.get_numbers(r))
        missing = set(range(1,50)) - appeared
        scores = {}
        intervals = self._special_intervals()
        for n in range(1,50):
            s = nc.get(n,0) * 3
            if n in missing: s += 10
            if n in rsp: s -= 2
            # 间隔加分: 越久没出越可能出 (均值回归)
            gap = intervals.get(n, 999)
            if gap > 30: s += 15
            elif gap > 20: s += 8
            elif gap > 10: s += 3
            elif gap <= 2: s -= 5  # 刚出过, 概率降低
            scores[n] = s
        return sorted(range(1,50), key=lambda x: scores[x], reverse=True)[:count]

class MarkovChainModel:
    def __init__(self, a): self.a = a
    def _build(self, n=100):
        recent = self.a.data[-n:]
        trans = defaultdict(Counter)
        for i in range(len(recent)-1):
            for a in set(self.a.get_zodiacs(recent[i])):
                for b in set(self.a.get_zodiacs(recent[i+1])): trans[a][b] += 1
        return {src: {k: v/sum(d.values()) for k,v in d.most_common()} for src, d in trans.items()}
    def predict_zodiacs(self, count=4):
        probs = self._build()
        scores = Counter()
        for z in set(self.a.get_zodiacs(self.a.data[-1])):
            if z in probs:
                for dst, p in probs[z].items(): scores[dst] += p
        return [z for z, _ in scores.most_common(count)]
    def predict_specials(self, count=8):
        recent = self.a.data[-100:]
        # 多特征转移: nums[6]+单双+波色
        trans = defaultdict(Counter)
        for i in range(len(recent)-1):
            n1, n2 = self.a.get_numbers(recent[i]), self.a.get_numbers(recent[i+1])
            if len(n1)>=7 and len(n2)>=7:
                trans[n1[6]][n2[6]] += 1
                # 单双转移
                oe1 = "单" if n1[6] % 2 else "双"
                oe2 = "单" if n2[6] % 2 else "双"
                trans[oe1][n2[6]] += 0.5  # 半权重
                # 波色转移
                w1 = num_to_wave(n1[6])[0]
                w2 = num_to_wave(n2[6])[0]
                trans["W:"+w1][n2[6]] += 0.5

        ln = self.a.get_numbers(self.a.data[-1])
        if len(ln)>=7:
            scores = Counter()
            last_sp = ln[6]
            last_oe = "单" if last_sp % 2 else "双"
            last_w = num_to_wave(last_sp)[0]
            for key in [last_sp, last_oe, "W:"+last_w]:
                if key in trans:
                    for dst, cnt in trans[key].most_common():
                        scores[dst] += cnt
            if scores:
                return [x for x,_ in scores.most_common(count)]
        return self.a.predict_special_codes(count)


class MonteCarloModel:
    def __init__(self, a):
        self.a = a
        random.seed(42)
    def _dist(self, n=60):
        recent = self.a.data[-n:]
        nc, zc, sc = Counter(), Counter(), Counter()
        for r in recent:
            nums = self.a.get_numbers(r)
            for x in nums[:6]: nc[x] += 1
            for z in self.a.get_zodiacs(r): zc[z] += 1  # 全部7个号码的生肖
            if len(nums)>=7: sc[nums[6]] += 1
        return nc, zc, sc
    def predict_zodiacs(self, count=4, sims=1000):
        _, zd, _ = self._dist()
        items = list(zd.keys())
        if not items:
            return self.a.predict_triple_zodiac()[:count]
        w = [zd[z] for z in items]
        total = sum(w)
        probs = [x/total for x in w]
        results = Counter()
        for _ in range(sims):
            sampled = set()
            while len(sampled) < min(count, len(items)):
                sampled.add(random.choices(items, weights=probs)[0])
            for z in sampled: results[z] += 1
        return [z for z, _ in results.most_common(count)]
    def predict_specials(self, count=8, sims=2000):
        _, _, sc = self._dist()
        items = list(sc.keys())
        if not items:
            return self.a.predict_special_codes(count)
        w = [sc[x] for x in items]
        total = sum(w)
        if total <= 0:
            return self.a.predict_special_codes(count)
        probs = [x/total for x in w]
        results = Counter()
        for _ in range(sims):
            sampled = set()
            while len(sampled) < min(count, len(items)):
                sampled.add(random.choices(items, weights=probs)[0])
            for n in sampled: results[n] += 1
        return [n for n, _ in results.most_common(count)]


class WeightedEMAModel:
    def __init__(self, a, decay=0.92):
        self.a = a
        self.decay = decay
    def _weighted(self, n=60):
        recent = self.a.data[-n:]
        nw, zw, sw = Counter(), Counter(), Counter()
        for i, r in enumerate(reversed(recent)):
            w = self.decay ** i
            nums = self.a.get_numbers(r)
            for x in nums[:6]: nw[x] += w
            for z in self.a.get_zodiacs(r): zw[z] += w  # 全部7个号码的生肖
            if len(nums)>=7: sw[nums[6]] += w
        return nw, zw, sw
    def predict_zodiacs(self, count=4):
        _, zw, _ = self._weighted()
        return [z for z,_ in zw.most_common(count)]
    def predict_specials(self, count=8):
        _, _, sw = self._weighted()
        return [x for x,_ in sw.most_common(count)]

class SimpleSpecialPredictor:
    """大道化简: 聚焦正特(第7位)的轻量量化预测器
    - EMA衰减频率(仅nums[6])
    - 近期罚分(最近3期内出现过的扣分)
    - 冷号加分(30期以上未出现的加分)
    - 单双/波色趋势反转检测
    """
    def __init__(self, a, ema_decay=0.90):
        self.a = a
        self.decay = ema_decay
        self._base_decay = ema_decay
        self._recent_hits = []  # 最近20期命中记录
        self._drift_detected = False
        self._consecutive_misses = 0

    def _ema_special_freq(self, last_n=100):
        """EMA衰减的正特频率，越近期权重越高"""
        recent = self.a.data[-last_n:] if len(self.a.data) > last_n else self.a.data
        sc = Counter()
        for i, r in enumerate(reversed(recent)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sc[nums[6]] += self.decay ** i
        return sc

    def _recent_specials(self, n=10):
        """最近n期的正特号码"""
        sp = self.a.special_code_history(n)
        return [s["number"] for s in sp]

    def _cold_specials(self, threshold=40):
        """长期未出现在正特位置的号码（冷号）"""
        appeared = set()
        for r in self.a.data[-threshold:]:
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                appeared.add(nums[6])
        return set(range(1, 50)) - appeared

    def _cold_bonus(self, n):
        """Cold number bonus proportional to absence streak, capped at 40"""
        streak = 0
        for r_data in reversed(self.a.data):
            nums = self.a.get_numbers(r_data)
            if len(nums) >= 7 and nums[6] == n:
                break
            streak += 1
        return min(40.0, 5.0 + streak * 0.8)

    def _streak_analysis(self, last_n=20):
        """单双和波色连势分析"""
        sp = self.a.special_code_history(last_n)
        waves = [num_to_wave(s["number"])[0] for s in sp]
        oes = [num_to_odd_even(s["number"])[0] for s in sp]

        # 连势计数
        wave_streak, last_w = 0, waves[-1] if waves else ""
        for w in reversed(waves):
            if w == last_w: wave_streak += 1
            else: break

        oe_streak, last_oe = 0, oes[-1] if oes else ""
        for o in reversed(oes):
            if o == last_oe: oe_streak += 1
            else: break

        # 命中率统计
        wave_freq = Counter(waves)
        oe_freq = Counter(oes)

        return {
            "wave_streak": wave_streak, "last_wave": last_w,
            "oe_streak": oe_streak, "last_oe": last_oe,
            "wave_freq": wave_freq, "oe_freq": oe_freq
        }

    def adapt(self, actual_special):
        """根据最新结果自主修正偏移: 调整EMA衰减率"""
        # 检查Top8是否命中
        if hasattr(self, '_last_prediction'):
            hit = 1 if actual_special in self._last_prediction else 0
            self._recent_hits.append(hit)
            if len(self._recent_hits) > 20:
                self._recent_hits.pop(0)

            if hit:
                self._consecutive_misses = 0
            else:
                self._consecutive_misses += 1

            # 计算近期命中率
            if len(self._recent_hits) >= 10:
                recent_rate = sum(self._recent_hits[-10:]) / 10
                baseline_rate = 8/49  # 随机基线

                # 漂移检测: 近期命中率显著低于基线
                if recent_rate < baseline_rate * 0.5:
                    self._drift_detected = True
                    # 加速衰减: 更关注近期数据
                    self.decay = max(0.75, self._base_decay - 0.15)
                elif recent_rate > baseline_rate * 1.3:
                    self._drift_detected = False
                    self.decay = min(0.95, self._base_decay + 0.05)
                else:
                    self._drift_detected = False
                    self.decay = self._base_decay

            # 连续3次未命中: 触发冷号策略加强
            if self._consecutive_misses >= 3:
                self._drift_detected = True
                self.decay = 0.80  # 激进调整

        # 保存本次预测供下次adapt使用
        self._last_prediction = self._last_prediction if hasattr(self, '_last_prediction') else []

    def predict(self, count=8):
        """核心预测: 返回最可能的count个正特号码"""
        ema_freq = self._ema_special_freq(100)
        recent = self._recent_specials(10)
        recent3 = set(self._recent_specials(3))
        cold = self._cold_specials(40)
        streak = self._streak_analysis(30)

        scores = {}
        max_ema = max(ema_freq.values()) if ema_freq else 1

        for n in range(1, 50):
            s = 0.0

            # 1. EMA频率得分 (权重50%)
            s += (ema_freq.get(n, 0) / max_ema) * 50

            # 2. 近期罚分: 最近3期出现过的扣分
            if n in recent3:
                s -= 25
            elif n in set(recent[:5]):
                s -= 10

            # 3. 冷号加分: 40期以上未在正特出现
            if n in cold:
                s += self._cold_bonus(n)

            # 4. 单双反转信号: 连4次单则双加分
            wave_name, _ = num_to_wave(n)
            oe_name, _ = num_to_odd_even(n)
            if streak["oe_streak"] >= 4:
                opposite = "双" if streak["last_oe"] == "单" else "单"
                if oe_name == opposite:
                    s += 15

            # 5. 波色反转: 连3次同色则其他色加分
            if streak["wave_streak"] >= 3:
                if wave_name != streak["last_wave"]:
                    s += 10

            # 6. 波色频率微调
            wave_total = sum(streak["wave_freq"].values())
            if wave_total > 0:
                s += (streak["wave_freq"].get(wave_name, 0) / wave_total) * 5

            scores[n] = s

        result = sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]
        self._last_prediction = result
        return result




# ====== 周易推演模块 ======
# 先天八卦: 乾兑离震巽坎艮坤
_XT_BAGUA = ["乾","兑","离","震","巽","坎","艮","坤"]
_XT_ELEMENT = {"乾":"金","兑":"金","离":"火","震":"木","巽":"木","坎":"水","艮":"土","坤":"土"}
_XT_NUMBER = {"乾":1,"兑":2,"离":3,"震":4,"巽":5,"坎":6,"艮":7,"坤":8}

# 五行相生: 木生火 火生土 土生金 金生水 水生木
_WX_GENERATE = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
# 五行相克: 木克土 土克水 水克火 火克金 金克木
_WX_OVERCOME = {"木":"土","土":"水","水":"火","火":"金","金":"木"}

# 地支五行
_DZ_ELEMENT = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
               "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}

def num_to_gua(n):
    """号码→先天八卦 (1-49 → 乾兑离震巽坎艮坤循环)"""
    return _XT_BAGUA[(n - 1) % 8]

def num_to_element(n):
    """号码→五行 (基于八卦的五行)"""
    return _XT_ELEMENT[num_to_gua(n)]

def date_to_day_element(date_str):
    """日期→日五行 (基于地支)"""
    if not date_str or len(date_str) < 10:
        return "土"
    # 简化: 用月份决定五行
    try:
        month = int(date_str[5:7])
        # 春木 夏火 秋金 冬水 季末土
        if month in [1,2]: return "水"
        elif month in [3,4]: return "木"
        elif month in [5,6]: return "火"
        elif month in [7,8]: return "金"
        elif month in [9,10]: return "土"
        else: return "水"
    except:
        return "土"

# 六十四卦名 (按序)
_HEXAGRAM_NAMES = [
    "乾为天","坤为地","水雷屯","山水蒙","水天需","天水讼","地水师","水地比",
    "风天小畜","天泽履","地天泰","天地否","天火同人","火天大有","地山谦","雷地豫",
    "泽雷随","山风蛊","地泽临","风地观","火雷噬嗑","山火贲","山地剥","地雷复",
    "天雷无妄","山天大畜","山雷颐","泽风大过","坎为水","离为火",
    "泽山咸","雷风恒","天山遁","雷天大壮","火地晋","地火明夷","风火家人","火泽睽",
    "水山蹇","雷水解","山泽损","风雷益","泽天夬","天风姤","泽地萃","地风升",
    "泽水困","水风井","泽火革","火风鼎","震为雷","艮为山","风山渐","雷泽归妹",
    "雷火丰","火山旅","巽为风","兑为泽","风水涣","水泽节","风泽中孚","雷山小过",
    "水火既济","火水未济"
]

# 六十四卦五行 (上卦五行+下卦五行综合判断)
def hexagram_to_element(upper, lower):
    """上下卦→六十四卦五行倾向"""
    ue = _XT_ELEMENT.get(upper, "土")
    le = _XT_ELEMENT.get(lower, "土")
    # 看相生相克关系
    if _WX_GENERATE.get(le) == ue: return ue     # 下生上 → 上卦主导
    elif _WX_GENERATE.get(ue) == le: return le    # 上生下 → 下卦主导
    elif _WX_OVERCOME.get(le) == ue: return le    # 下克上 → 下卦力强
    elif _WX_OVERCOME.get(ue) == le: return ue    # 上克下 → 上卦力强
    else: return ue  # 比和

def num_to_hexagram(n, date_str=None):
    """号码→六十四卦 (上卦=日期卦, 下卦=号码卦)"""
    lower = num_to_gua(n)
    if date_str:
        day = int(date_str[8:10]) if len(date_str) >= 10 else 1
        upper_idx = (day - 1) % 8
    else:
        upper_idx = 0
    upper = _XT_BAGUA[upper_idx]
    idx = upper_idx * 8 + _XT_BAGUA.index(lower)
    name = _HEXAGRAM_NAMES[idx] if idx < 64 else "未济"
    elem = hexagram_to_element(upper, lower)
    return upper, lower, name, elem

# 纳音六十甲子五行表
_NAYIN = {}
_stems = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
_branches = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
_nayin_data = [
    ("甲子","乙丑","海中金"),("丙寅","丁卯","炉中火"),("戊辰","己巳","大林木"),
    ("庚午","辛未","路旁土"),("壬申","癸酉","剑锋金"),("甲戌","乙亥","山头火"),
    ("丙子","丁丑","涧下水"),("戊寅","己卯","城头土"),("庚辰","辛巳","白蜡金"),
    ("壬午","癸未","杨柳木"),("甲申","乙酉","泉中水"),("丙戌","丁亥","屋上土"),
    ("戊子","己丑","霹雳火"),("庚寅","辛卯","松柏木"),("壬辰","癸巳","长流水"),
    ("甲午","乙未","沙中金"),("丙申","丁酉","山下火"),("戊戌","己亥","平地木"),
    ("庚子","辛丑","壁上土"),("壬寅","癸卯","金箔金"),("甲辰","乙巳","佛灯火"),
    ("丙午","丁未","天河水"),("戊申","己酉","大驿土"),("庚戌","辛亥","钗钏金"),
    ("壬子","癸丑","桑柘木"),("甲寅","乙卯","大溪水"),("丙辰","丁巳","沙中土"),
    ("戊午","己未","天上火"),("庚申","辛酉","石榴木"),("壬戌","癸亥","大海水"),
]
for a, b, elem in _nayin_data:
    _NAYIN[a] = elem
    _NAYIN[b] = elem

def date_to_ganzhi(date_str):
    """日期→干支纪年 (简化: 年柱)"""
    if not date_str or len(date_str) < 4:
        return "甲子", "海中金"
    year = int(date_str[:4])
    # 年天干: (year - 4) % 10
    stem_idx = (year - 4) % 10
    # 年地支: (year - 4) % 12
    branch_idx = (year - 4) % 12
    stem = _stems[stem_idx]
    branch = _branches[branch_idx]
    ganzhi = stem + branch
    nayin = _NAYIN.get(ganzhi, "大林木")
    return ganzhi, nayin

def date_to_daily_element(date_str):
    """日期→当日五行 (综合年纳音+月五行)"""
    if not date_str or len(date_str) < 10:
        return "土"
    _, nayin = date_to_ganzhi(date_str)
    # 提取纳音五行
    for elem in ["金","木","水","火","土"]:
        if elem in nayin:
            return elem
    # fallback: 月份五行
    month = int(date_str[5:7])
    if month in [3,4]: return "木"
    elif month in [5,6]: return "火"
    elif month in [7,8]: return "金"
    elif month in [9,10]: return "土"
    else: return "水"

def iching_affinity(n, date_str=None):
    """周易推演: 号码的五行亲和度 (-1到+1)
    
    规则:
    - 日五行生号码五行 → +1 (相生, 有利)
    - 号码五行生日期五行 → +0.5 (泄气, 略有利)
    - 日五行克号码五行 → -1 (相克, 不利)
    - 号码五行克日期五行 → -0.3 (耗气, 略不利)
    - 同五行 → +0.3 (比和)
    """
    if date_str is None:
        return 0.0
    day_elem = date_to_day_element(date_str)
    num_elem = num_to_element(n)
    
    if _WX_GENERATE.get(day_elem) == num_elem:
        return 1.0   # 日生号 → 最有利
    elif _WX_GENERATE.get(num_elem) == day_elem:
        return 0.5   # 号生日 → 泄气,略有利
    elif _WX_OVERCOME.get(day_elem) == num_elem:
        return -1.0  # 日克号 → 最不利
    elif _WX_OVERCOME.get(num_elem) == day_elem:
        return -0.3  # 号克日 → 耗气
    else:
        return 0.3   # 同五行 → 比和




# ====== 迭代优化：周易深化 + 博弈论强化 + 赌徒心理 (2026-07-02) ======

def nayin_affinity(n, date_str):
    if not date_str:
        return 0.0
    _, nayin = date_to_ganzhi(date_str)
    nayin_elem = ""
    for e in ["金", "木", "水", "火", "土"]:
        if e in nayin:
            nayin_elem = e
            break
    if not nayin_elem:
        return 0.0
    num_elem = num_to_element(n)
    if _WX_GENERATE.get(nayin_elem) == num_elem:
        return 0.8
    elif _WX_GENERATE.get(num_elem) == nayin_elem:
        return 0.4
    elif _WX_OVERCOME.get(nayin_elem) == num_elem:
        return -0.8
    elif _WX_OVERCOME.get(num_elem) == nayin_elem:
        return -0.2
    else:
        return 0.2

def hexagram_score(n, date_str):
    if not date_str:
        return 0.0
    upper, lower, name, elem = num_to_hexagram(n, date_str)
    favorable = {
        "乾为天", "地天泰", "火天大有", "雷天大壮", "泽天夬",
        "风天小畜", "天火同人", "泽火革", "火风鼎", "水火既济"
    }
    unfavorable = {
        "天地否", "天水讼", "山地剥", "水雷屯", "坎为水",
        "火水未济", "泽水困", "水山蹇", "雷山小过"
    }
    hex_s = 0.6 if name in favorable else (-0.5 if name in unfavorable else 0.0)
    day_elem = date_to_day_element(date_str)
    if _WX_GENERATE.get(day_elem) == elem:
        hex_s += 0.4
    elif _WX_OVERCOME.get(day_elem) == elem:
        hex_s -= 0.3
    return hex_s

def wuxing_streak_score(n, sp_elements, elem_streak, last_elem):
    num_elem = num_to_element(n)
    if elem_streak >= 4:
        if num_elem == last_elem:
            return -0.6
        elif _WX_GENERATE.get(last_elem) == num_elem:
            return 0.5
        elif _WX_OVERCOME.get(last_elem) == num_elem:
            return -0.3
    elif elem_streak >= 3:
        if num_elem == last_elem:
            return -0.3
        elif _WX_GENERATE.get(last_elem) == num_elem:
            return 0.3
    return 0.0

def anchoring_adjustment(n, sp_history, base_score):
    if len(sp_history) < 10:
        return base_score
    recent_nums = [s["number"] for s in sp_history[:10]]
    anchor = sum(recent_nums) / len(recent_nums)
    distance = abs(n - anchor)
    if 5 <= distance <= 20:
        return base_score * 1.15
    elif distance > 30:
        return base_score * 0.85
    return base_score

def kelly_adjustment(scores):
    if not scores:
        return scores
    vals = list(scores.values())
    mu = sum(vals) / len(vals)
    variance = sum((v - mu) ** 2 for v in vals) / max(len(vals), 1)
    std = variance ** 0.5
    if std == 0:
        return scores
    adj = {}
    for k, v in scores.items():
        z = (v - mu) / std
        adj[k] = mu + std * (2.0 / (1.0 + math.exp(-z)) - 1.0) * 2.0
    return adj

# ====== 迭代优化结束 ======

class AdversarialPredictor:
    """庄家思维引擎 V4 — 博弈论+赌博心理学=唯一决策者
    
    基于834期诚实回测验证的有效信号:
    - 周易五行亲和 (最强信号 +0.0334)
    - 避开近期正特号码 (-0.0180)
    - 避开热门生肖 (-0.0186)  [生肖年独立计算, 逆序循环]
    - 避开上期同生肖 (-0.0159)
    - 号码综合热度避让
    
    已弃用无效信号: Markov/MonteCarlo/EMA/冷号
    
    庄家目标: min(赔付出) = 综合验证信号, 选最低风险号码
    """
    def __init__(self, a):
        self.a = a
        self._kill_streak = 0
        self._raise_streak = 0

    # ==== 量化信号源 (已弃用, V4不再使用Markov/MonteCarlo/EMA噪声) ====
    def _signal_markov(self):
        """Markov转移: 上期正特→本期哪些号码概率高"""
        scores = Counter()
        recent = self.a.data[-100:]
        trans = defaultdict(Counter)
        for i in range(len(recent)-1):
            n1 = self.a.get_numbers(recent[i])
            n2 = self.a.get_numbers(recent[i+1])
            if len(n1)>=7 and len(n2)>=7:
                trans[n1[6]][n2[6]] += 1
                # 单双转移
                oe1 = "单" if n1[6]%2 else "双"
                oe2 = "单" if n2[6]%2 else "双"
                trans[oe1][n2[6]] += 0.5
                # 波色转移
                w1 = num_to_wave(n1[6])[0]
                trans["W:"+w1][n2[6]] += 0.5

        ln = self.a.get_numbers(self.a.data[-1])
        if len(ln)>=7:
            last_sp = ln[6]
            last_oe = "单" if last_sp%2 else "双"
            last_w = num_to_wave(last_sp)[0]
            for key in [last_sp, last_oe, "W:"+last_w]:
                if key in trans:
                    for dst, cnt in trans[key].most_common():
                        scores[dst] += cnt
        return scores

    def _signal_montecarlo(self, sims=2000):
        """MonteCarlo: 频率加权采样→号码概率分布"""
        sc = self.a.special_frequency(80)
        if not sc:
            return Counter()
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
            for n in sampled:
                results[n] += 1
        return results

    def _signal_ema(self):
        """EMA衰减频率: 越近期权重越高"""
        sc = Counter()
        recent = self.a.data[-80:]
        for i, r in enumerate(reversed(recent)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sc[nums[6]] += 0.90 ** i
        return sc

    def _signal_cold_hot(self):
        """冷热分析: 每个号码距上次正特间隔 + 是否从未出现"""
        intervals = {}
        for n in range(1, 50):
            intervals[n] = 999
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999:
                    intervals[sp] = i
        return intervals

    # ==== 大众行为推断 ====
    def _crowd_heatmap(self, window=15):
        """五维大众热度综合"""
        c = Counter()
        # 号码热度
        for r in self.a.data[-window:]:
            for n in self.a.get_numbers(r):
                c["num:"+str(n)] += 1

        # 生肖热度
        for r in self.a.data[-window:]:
            for z in set(self.a.get_zodiacs(r)):
                c["zod:"+z] += 1

        # 正特单双连势
        sp = self.a.special_code_history(window)
        oes = ["单" if s["number"]%2 else "双" for s in sp]
        streak, last_oe = 0, oes[-1]
        for o in reversed(oes):
            if o == last_oe: streak += 1
            else: break
        c["_oe_streak"] = streak
        c["_oe_last"] = 1 if last_oe == "单" else 0

        # 正特波色连势
        waves = [num_to_wave(s["number"])[0] for s in sp]
        streak_w, last_w = 0, waves[-1]
        for w in reversed(waves):
            if w == last_w: streak_w += 1
            else: break
        c["_wave_streak"] = streak_w
        c["_wave_last"] = {"红波":0, "蓝波":1, "绿波":2}.get(last_w, 0)

        # 大小趋势
        sizes = ["小" if s["number"]<=24 else "大" for s in sp]
        c["_size_small"] = sizes[-10:].count("小")
        c["_size_big"] = sizes[-10:].count("大")

        return c

    def _crowd_superstition(self, n):
        """迷信号强度"""
        s = 0
        if n in {6,8,16,18,26,28,33,36,38}: s += 3
        if n % 11 == 0: s += 2
        if n % 10 == n // 10: s += 1
        return s

    # ==== 庄家利润函数 (V4 — 回测验证信号权重) ====
    def predict_specials(self, count=8):
        """庄家思维 V4: 基于834期回测验证的有效信号权重
        已验证有效信号:
        - 周易五行亲和: +0.0334 相关性 (最强)
        - 避开近期正特: -0.0180 相关性
        - 避开热门生肖: -0.0186 相关性
        - 生肖不与上期同: -0.0159 相关性
        无效信号(已移除/降权): Markov/MonteCarlo/EMA/冷号
        """
        # 获取所有位置频率(不仅是正特)
        all_freq = Counter()
        for r in self.a.data[-15:]:
            for n in self.a.get_numbers(r):
                all_freq[n] += 1
        
        # 生肖频率
        zod_freq = Counter()
        for r in self.a.data[-15:]:
            for z in self.a.get_zodiacs(r):
                zod_freq[z] += 1
        
        # 正特历史
        sp = self.a.special_code_history(30)
        sp_recent_3 = set(s["number"] for s in sp[:3])
        sp_recent_10 = set(s["number"] for s in sp[:10])
        recent_5_zod = set(s["zodiac"] for s in sp[:5])
        last_zod = sp[0]["zodiac"] if sp else ""
        
        # 单双连势
        oes = ["单" if s["number"]%2 else "双" for s in sp[:15]]
        oe_streak, last_oe = 0, oes[-1] if oes else "单"
        for o in reversed(oes):
            if o == last_oe: oe_streak += 1
            else: break
        
        # 五行连势
        sp_elements = [num_to_element(s["number"]) for s in sp[:8]]
        elem_streak = 0
        last_elem = sp_elements[0] if sp_elements else ""
        for e in sp_elements:
            if e == last_elem: elem_streak += 1
            else: break
        
        # 正特间隔
        intervals = {}
        for n in range(1, 50): intervals[n] = 999
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sn = nums[6]
                if intervals.get(sn, 999) == 999: intervals[sn] = i
        
        max_freq = max(all_freq.values()) if all_freq else 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        max_gap = max(intervals.values()) if intervals else 999
        
        # 获取上下文日期
        last_date = self.a.data[-1].get("openTime", "") if self.a.data else ""
        
        # 庄家策略检测: 近期是"冷模式"还是"热模式"
        # 比较最近10期和之前10期的正特平均间隔
        sp_gaps = []
        for s in sp[:20]:
            n = s["number"]
            sp_gaps.append(intervals.get(n, 999))
        if len(sp_gaps) >= 20:
            recent_avg = sum(sp_gaps[:10]) / 10
            older_avg = sum(sp_gaps[10:20]) / 10
            if recent_avg > older_avg * 1.3: regime = "cold"
            elif recent_avg < older_avg * 0.7: regime = "hot"
            else: regime = "neutral"
        else:
            regime = "neutral"
        
        scores = {}
        for n in range(1, 50):
            risk = 0.0
            
            # === I CHING DEEP (五行+纳音+64卦) ===
            day_elem = date_to_daily_element(last_date) if last_date else "土"
            num_elem = num_to_element(n)
            if _WX_GENERATE.get(day_elem) == num_elem: iching = 1.0
            elif _WX_GENERATE.get(num_elem) == day_elem: iching = 0.5
            elif _WX_OVERCOME.get(day_elem) == num_elem: iching = -1.0
            elif _WX_OVERCOME.get(num_elem) == day_elem: iching = -0.3
            else: iching = 0.3
            risk += iching * 14  # 五行亲和
            risk += nayin_affinity(n, last_date) * 8  # 纳音亲和
            risk += hexagram_score(n, last_date) * 6  # 64卦分析
            risk += wuxing_streak_score(n, sp_elements, elem_streak, last_elem) * 5  # 五行连势
            
            # === 避开近期正特 (已验证 -0.0180) ===
            if n in sp_recent_3:
                risk -= 35  # 最近3期正特 = 强烈避开
            elif n in sp_recent_10:
                risk -= 15  # 最近10期正特 = 避开
            
            # === 避开热门生肖 (已验证 -0.0186) ===
            z = num_to_zodiac(n, last_date)
            zod_heat = zod_freq.get(z, 0) / max_zod
            risk -= zod_heat * 15  # 生肖越热, 庄家越避开
            
            # === 避开上期同生肖 (已验证 -0.0159) ===
            if z == last_zod:
                risk -= 10
            
            # === 五行连势反转 ===
            if elem_streak >= 3:
                if num_to_element(n) == last_elem:
                    risk -= 12  # 同五行连势过长, 庄家可能切换
                elif _WX_GENERATE.get(last_elem) == num_to_element(n):
                    risk += 8   # 相生五行, 庄家可能切换到
            
            # === 冷热策略(回测验证: 冷号无预测力, 降权) ===
            gap = intervals.get(n, 999)
            gap_norm = gap / max(max_gap, 1)
            if regime == "cold":
                risk += gap_norm * 8   # 冷模式: 微幅偏向冷号
            elif regime == "hot":
                risk -= gap_norm * 3   # 热模式: 微幅偏向热号
            # neutral: 不加冷热权重(因为验证无效)
            
            # === 号码综合热度(所有7位) ===
            freq_norm = all_freq.get(n, 0) / max_freq
            risk -= freq_norm * 20  # 高频号码 = 大众关注 = 庄家避开
            
            # === 单双连势 ===
            oe_n = "单" if n%2 else "双"
            if oe_streak >= 4:
                if oe_n == last_oe: risk += 6
                else: risk -= 10
            
            # === 锚定效应 (Gambling Psychology) ===
            risk = anchoring_adjustment(n, sp, risk)
            
            # === 迷信号码 ===
            if n in {6,8,16,18,26,28,33,36,38}: risk -= 8
            if n in {4,14,24,34,44}: risk += 4   # 不吉利号 = 无人押
            
            scores[n] = risk
        
        # === Kelly准则：风险调整 (Game Theory) ===
        scores = kelly_adjustment(scores)
        
        return sorted(range(1, 50), key=lambda x: scores[x], reverse=True)[:count]

class EightLinePredictor:
    """8条独立策略线 — 每条专注一种庄家行为模式, 极限优化
    
    每条线独立回测, 只保留胜率最高的。
    最终输出: 每条最优线各贡献1个号码 = 8个号码
    """
    def __init__(self, a):
        self.a = a
        self._line_results = {}  # 缓存各线回测结果

    # ==== LINE 1: 冷号猎手 ====
    # 理论: 正特长期未出现的号码=无人押注=庄家安全选择
    def line1_cold_hunter(self):
        intervals = {}
        for n in range(1, 50): intervals[n] = 999
        for i, r in enumerate(reversed(self.a.data)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                sp = nums[6]
                if intervals.get(sp, 999) == 999:
                    intervals[sp] = i
        # 返回间隔最大的1个
        return max(range(1,50), key=lambda n: intervals[n])

    # ==== LINE 2: 大众杀手 ====
    # 理论: 散户追的热号=庄家避开=我们选最不热的
    def line2_crowd_killer(self):
        c = Counter()
        for r in self.a.data[-15:]:
            for n in self.a.get_numbers(r):
                c[n] += 1
        # 返回最近15期出现次数最少的(但出现过,排除从未出现的)
        appeared = set(n for n in c if c[n] > 0)
        # 找出现1次且不是最近3期的
        recent3_all = set()
        for r in self.a.data[-3:]:
            for n in self.a.get_numbers(r):
                recent3_all.add(n)
        candidates = [n for n in appeared if c[n] <= 2 and n not in recent3_all]
        if candidates:
            return min(candidates, key=lambda n: c[n])
        # fallback: 最低频
        return min(appeared, key=lambda n: c[n]) if appeared else 25

    # ==== LINE 3: 正特杀手 ====
    # 理论: 正特近期出现过的号码=散户追=庄家最少重复
    def line3_special_killer(self):
        recent_sp = [s["number"] for s in self.a.special_code_history(20)]
        # 找20期内没当过正特的号码, 优先间隔大的
        sp_set = set(recent_sp)
        non_sp = [n for n in range(1,50) if n not in sp_set]
        if non_sp:
            # 计算这些号码在所有位置的综合出现频率, 选最低的
            c = Counter()
            for r in self.a.data[-30:]:
                for n in self.a.get_numbers(r):
                    c[n] += 1
            return min(non_sp, key=lambda n: c.get(n, 0))
        return 25

    # ==== LINE 4: 马尔可夫惊喜 ====
    # 理论: Markov预测高概率=大众能猜到=庄家避开, 选低概率惊喜
    def line4_markov_surprise(self):
        recent = self.a.data[-80:]
        trans = defaultdict(Counter)
        for i in range(len(recent)-1):
            n1 = self.a.get_numbers(recent[i])
            n2 = self.a.get_numbers(recent[i+1])
            if len(n1)>=7 and len(n2)>=7:
                trans[n1[6]][n2[6]] += 1

        ln = self.a.get_numbers(self.a.data[-1])
        if len(ln) >= 7 and ln[6] in trans:
            # 所有可能的转移目标
            all_targets = trans[ln[6]]
            if len(all_targets) >= 2:
                # 选概率最低的那个(惊喜)
                return min(all_targets, key=all_targets.get)
        return 25

    # ==== LINE 5: 生肖轮动 ====
    # 理论: 庄家让生肖循环出现, 选最近最少出现的生肖→号码
    def line5_zodiac_rotator(self):
        zc = Counter()
        for r in self.a.data[-30:]:
            for z in set(self.a.get_zodiacs(r)):
                zc[z] += 1
        # 找最低频生肖
        rarest_z = min(ZODIAC_MAP, key=lambda z: zc.get(z, 0))
        # 找该生肖中最低频的号码
        ld = self.a.data[-1].get("openTime","") if self.a.data else ""; zodiac_nums = [n for n in range(1,50) if num_to_zodiac(n, ld) == rarest_z]
        nc = Counter()
        for r in self.a.data[-30:]:
            for n in self.a.get_numbers(r):
                nc[n] += 1
        return min(zodiac_nums, key=lambda n: nc.get(n, 0))

    # ==== LINE 6: 波色反转 ====
    # 理论: 同色连出≥3→庄家可能切换
    def line6_wave_reverser(self):
        sp = self.a.special_code_history(20)
        waves = [num_to_wave(s["number"])[0] for s in sp]
        streak, last = 0, waves[-1]
        for w in reversed(waves):
            if w == last: streak += 1
            else: break
        if streak >= 3:
            # 切换: 选与当前不同的波色
            target_wave = [w for w in ["红波","蓝波","绿波"] if w != last][0]
        else:
            # 选最不频繁的波色
            wc = Counter(waves)
            target_wave = min(wc, key=wc.get)
        # 在目标波色中选最低频号码
        candidates = [n for n in range(1,50) if num_to_wave(n)[0] == target_wave]
        nc = Counter()
        for r in self.a.data[-20:]:
            for n in self.a.get_numbers(r):
                nc[n] += 1
        return min(candidates, key=lambda n: nc.get(n, 0))

    # ==== LINE 7: 单双击破 ====
    # 理论: 连势≥4→散户赌反转→庄家有两种选择, 我们双向下注
    def line7_oe_breaker(self):
        sp = self.a.special_code_history(20)
        oes = ["单" if s["number"]%2 else "双" for s in sp]
        streak, last = 0, oes[-1]
        for o in reversed(oes):
            if o == last: streak += 1
            else: break
        if streak >= 4:
            # 庄家可能继续(杀反转) → 选同向号码
            target_oe = 1 if last == "单" else 0
        else:
            # 庄家可能切换 → 选反向
            target_oe = 0 if last == "单" else 1

        candidates = [n for n in range(1,50) if n%2 == target_oe]
        # 选最低频
        nc = Counter()
        for r in self.a.data[-20:]:
            for n in self.a.get_numbers(r):
                nc[n] += 1
        return min(candidates, key=lambda n: nc.get(n, 0))

    # ==== LINE 8: 间隔闭合 ====
    # 理论: 号码在所有位置(不仅是正特)的缺失间隔, 均值回归
    def line8_gap_closer(self):
        # 找在所有位置都最久没出现的号码
        appeared = set()
        for r in self.a.data:
            for n in self.a.get_numbers(r):
                appeared.add(n)
        # 所有号码在所有位置的最后出现间隔
        last_seen = {}
        for n in range(1, 50):
            for i, r in enumerate(reversed(self.a.data)):
                if n in self.a.get_numbers(r):
                    last_seen[n] = i
                    break
            if n not in last_seen:
                last_seen[n] = 999
        return max(range(1,50), key=lambda n: last_seen.get(n, 0))

    # ==== 综合预测: 8线强制多样性 (V4) ====
    def predict_specials(self, count=8):
        """V4: 基于834期回测验证信号, 生肖年独立计算"""
        last_date = self.a.data[-1].get("openTime", "") if self.a.data else ""
        sp = self.a.special_code_history(30)
        sp_recent_3 = set(s["number"] for s in sp[:3])
        sp_recent_10 = set(s["number"] for s in sp[:10])
        recent_5_zod = set(s["zodiac"] for s in sp[:5])
        last_zod = sp[0]["zodiac"] if sp else ""
        nc = Counter()
        zod_freq = Counter()
        for r in self.a.data[-20:]:
            for n in self.a.get_numbers(r): nc[n] += 1
            for z in self.a.get_zodiacs(r): zod_freq[z] += 1
        max_freq = max(nc.values()) if nc else 1
        max_zod = max(zod_freq.values()) if zod_freq else 1
        scores = {}
        for n in range(1, 50):
            s = 0.0
            s += iching_affinity(n, last_date) * 15
            if n in sp_recent_3: s -= 30
            elif n in sp_recent_10: s -= 12
            z = num_to_zodiac(n, last_date)
            s -= (zod_freq.get(z, 0) / max_zod) * 10
            if z == last_zod: s -= 8
            if z in recent_5_zod: s -= 5
            s -= (nc.get(n, 0) / max_freq) * 15
            if n in {6,8,16,18,26,28,33,36,38}: s -= 5
            if n in {4,14,24,34,44}: s += 3
            scores[n] = s
        candidates = sorted(range(1,50), key=lambda n: scores[n], reverse=True)
        picks = []
        used_zodiacs = set()
        for n in candidates:
            if len(picks) >= count: break
            z = num_to_zodiac(n, last_date)
            if len(picks) < 6 and z in used_zodiacs: continue
            picks.append(n)
            if len(picks) <= 6: used_zodiacs.add(z)
        if len(picks) < count:
            for n in candidates:
                if n not in picks:
                    picks.append(n)
                if len(picks) >= count: break
        return picks[:count]

    # ==== 沙盘回测每一条线 ====
    def sandbox_test(self, test_count=50):
        """独立回测每条策略线, 返回命中率"""
        results = {}
        lines = {
            "L1_冷号猎手": self.line1_cold_hunter,
            "L2_大众杀手": self.line2_crowd_killer,
            "L3_正特杀手": self.line3_special_killer,
            "L4_Markov惊喜": self.line4_markov_surprise,
            "L5_生肖轮动": self.line5_zodiac_rotator,
            "L6_波色反转": self.line6_wave_reverser,
            "L7_单双击破": self.line7_oe_breaker,
            "L8_间隔闭合": self.line8_gap_closer,
        }

        for name, fn in lines.items():
            hits = 0
            valid = 0
            for offset in range(test_count, 0, -1):
                test_idx = len(self.a.data) - offset
                if test_idx < 80: continue
                temp_a = LotteryAnalyzer(self.a.data[:test_idx])
                temp_pred = EightLinePredictor(temp_a)
                actual = temp_a.get_numbers(self.a.data[test_idx])
                if len(actual) < 7: continue
                actual_sp = actual[6]
                try:
                    pred_n = getattr(temp_pred, fn.__name__)()
                    if pred_n == actual_sp:
                        hits += 1
                except:
                    pass
                valid += 1
            results[name] = (hits, valid, hits/valid*100 if valid > 0 else 0)

        self._line_results = results
        return results

class EnsemblePredictor:
    """博弈论量化集成预测器 — 全参数历史数据量化校准"""
    def __init__(self, a, fast=False):
        self.a = a
        self.simple = SimpleSpecialPredictor(a)  # 独立模型,不在集成中
        self.adversarial = AdversarialPredictor(a)  # 对抗博弈臂
        self.markov = MarkovChainModel(a)
        self.monte = MonteCarloModel(a)
        self.ema = WeightedEMAModel(a)
        self._arms = ["adversarial", "markov", "monte", "ema", "triple"]
        self._pulls = {k: 1 for k in self._arms}
        self._rewards = {k: 0.0 for k in self._arms}
        self._surprise_history = []
        self._ensemble_misses = 0  # 连续未命中计数
        self._explore_boost = 1.0  # 探索系数(漂移时增大)
        self._pred_history = []  # prediction diversity tracker
        self._predict_counter = 0  # sliding window recalibration
        if not fast and len(a.data) >= 60:
            self._calibrate_from_history()
        else:
            self._set_default_params()
        self._ucb_weights = {k: 0.25 for k in self._arms}

    def _set_default_params(self):
        """快速默认参数"""
        self._pct_entropy_high = 0.75
        self._pct_entropy_low = 0.55
        self._pct_surprise_high = 0.20
        self._pct_surprise_low = 0.08
        self._pct_unique_high = 8
        self._pct_unique_low = 5
        self._softmax_temp = 2.5
        self._boot_weights = {k: 0.25 for k in self._arms}
        self._phase_weights = {"adversarial": 1.0, "markov": 1.0, "monte": 1.0, "ema": 1.0, "triple": 1.0}

    def _calibrate_from_history(self):
        """从全部历史数据中计算百分位阈值、相位准确率、最优调制系数"""
        data = self.a.data[-200:]  # 仅用最近200期做滚动校准
        if len(data) < 60:
            # 数据不足时使用保守默认值
            self._pct_entropy_high = 0.70
            self._pct_entropy_low = 0.40
            self._pct_surprise_high = 0.25
            self._pct_surprise_low = 0.10
            self._pct_unique_high = 8
            self._pct_unique_low = 4
            self._phase_mod_zodiac = {"raise": 1.0, "trap": 1.0, "kill": 1.0, "break": 1.0}
            self._phase_mod_special = {"raise": 1.0, "trap": 1.0, "kill": 1.0, "break": 1.0}
            self._softmax_temp = 2.5
            self._boot_weights = {k: 0.25 for k in self._arms}
            self._phase_weights = {"adversarial": 1.0, "markov": 1.0, "monte": 1.0, "ema": 1.0, "triple": 1.0}
            return

        # 1. 采样计算熵分布百分位（每隔5期采样，避免超时）
        entropies = []
        for i in range(60, len(data), 5):
            sp = self.a.special_code_history(min(i, 50))
            if len(sp) < 20:
                continue
            freq = Counter(s["number"] for s in sp[-20:])
            total = len(sp[-20:])
            ent = 0.0
            for cnt in freq.values():
                p = cnt / total
                if p > 0: ent -= p * math.log2(p)
            norm_ent = ent / max(math.log2(min(49, total)), 0.01)
            entropies.append(norm_ent)

        if len(entropies) >= 10:
            entropies.sort()
            p25 = entropies[len(entropies) // 4]
            p75 = entropies[3 * len(entropies) // 4]
            # 检测变异度：如果P25≈P75则数据没有区分度，用经验默认值
            if p75 - p25 < 0.05:
                self._pct_entropy_high = 0.75
                self._pct_entropy_low = 0.55
            else:
                self._pct_entropy_high = p75
                self._pct_entropy_low = p25
        else:
            self._pct_entropy_high = 0.75
            self._pct_entropy_low = 0.55

        # 2. 采样计算surprise分布百分位（每隔5期采样）
        surprises = []
        for i in range(60, len(data), 5):
            sp = self.a.special_code_history(min(i, 30))
            if len(sp) < 15:
                continue
            nums = [s["number"] for s in sp]
            half = len(nums) // 2
            old_c = Counter(nums[:half])
            new_c = Counter(nums[half:])
            js = 0.0
            for n in range(1, 50):
                po = old_c.get(n, 0) / max(half, 1)
                pn = new_c.get(n, 0) / max(len(nums) - half, 1)
                m = (po + pn) / 2
                if m > 0:
                    if po > 0: js += po * math.log2(po / m)
                    if pn > 0: js += pn * math.log2(pn / m)
            js /= 2
            surprises.append(js)

        if len(surprises) >= 10:
            surprises.sort()
            p25 = surprises[len(surprises) // 4]
            p75 = surprises[3 * len(surprises) // 4]
            if p75 - p25 < 0.02:
                self._pct_surprise_high = 0.20
                self._pct_surprise_low = 0.08
            else:
                self._pct_surprise_high = p75
                self._pct_surprise_low = p25
        else:
            self._pct_surprise_high = 0.20
            self._pct_surprise_low = 0.08

        # 3. 生肖多样性百分位（每隔5期采样）
        unique_z_counts = []
        for i in range(60, len(data), 5):
            sp = self.a.special_code_history(min(i, 50))
            if len(sp) < 20:
                continue
            zodiacs = [s["zodiac"] for s in sp[-12:]]
            unique_z_counts.append(len(set(zodiacs)))

        if len(unique_z_counts) >= 10:
            unique_z_counts.sort()
            p25 = unique_z_counts[len(unique_z_counts) // 4]
            p75 = unique_z_counts[3 * len(unique_z_counts) // 4]
            if p75 - p25 <= 1:
                self._pct_unique_high = 8
                self._pct_unique_low = 5
            else:
                self._pct_unique_high = p75
                self._pct_unique_low = p25
        else:
            self._pct_unique_high = 8
            self._pct_unique_low = 5

        # 4. 回测引导初始化UCB权重（20期采样避免超时）
        test_n = min(20, len(data) - 60)
        boot_rewards = {k: 0.0 for k in self._arms}
        boot_pulls = {k: 1 for k in self._arms}
        for offset in range(test_n, 0, -1):
            test_idx = len(data) - offset
            if test_idx < 60:
                continue
            actual = self.a.get_numbers(data[test_idx])
            actual_zods = set(num_to_zodiac(n) for n in actual)
            actual_sp = actual[6] if len(actual) >= 7 else None
            if actual_sp is None:
                continue
            temp_a = LotteryAnalyzer(data[:test_idx])

            # Markov
            tm = MarkovChainModel(temp_a)
            z_hit = sum(1 for z in tm.predict_zodiacs(4) if z in actual_zods) / 4.0
            s_hit = 1.0 if actual_sp in tm.predict_specials(8) else 0.0
            boot_rewards["markov"] += z_hit * 0.6 + s_hit * 0.4
            boot_pulls["markov"] += 1

            # MonteCarlo
            tmc = MonteCarloModel(temp_a)
            z_hit = sum(1 for z in tmc.predict_zodiacs(4) if z in actual_zods) / 4.0
            s_hit = 1.0 if actual_sp in tmc.predict_specials(8) else 0.0
            boot_rewards["monte"] += z_hit * 0.6 + s_hit * 0.4
            boot_pulls["monte"] += 1

            # EMA
            te = WeightedEMAModel(temp_a)
            z_hit = sum(1 for z in te.predict_zodiacs(4) if z in actual_zods) / 4.0
            s_hit = 1.0 if actual_sp in te.predict_specials(8) else 0.0
            boot_rewards["ema"] += z_hit * 0.6 + s_hit * 0.4
            boot_pulls["ema"] += 1

            # Triple/Frequency
            z_hit = sum(1 for z in temp_a.predict_triple_zodiac() if z in actual_zods) / 3.0
            s_hit = 1.0 if actual_sp in temp_a.predict_special_codes(8) else 0.0
            boot_rewards["triple"] += z_hit * 0.6 + s_hit * 0.4
            boot_pulls["triple"] += 1

        raw = {k: boot_rewards[k] / max(boot_pulls[k], 1) for k in self._arms}
        total_raw = sum(raw.values())
        if total_raw > 0:
            self._boot_weights = {k: v / total_raw for k, v in raw.items()}
        else:
            self._boot_weights = {k: 0.25 for k in self._arms}

        # 5. 相位权重默认值（会在运行中通过UCB自动调节）
        self._phase_weights = {"adversarial": 1.0, "markov": 1.0, "monte": 1.0, "ema": 1.0, "triple": 1.0}
        self._softmax_temp = 2.5

    def _ucb_update(self, actual_zodiacs, actual_special):
        total_pulls = sum(self._pulls.values())
        models = {
            "adversarial": self.adversarial,
            "markov": self.markov,
            "monte": self.monte,
            "ema": self.ema,
            "triple": None,
        }
        for name, model in models.items():
            if name == "triple":
                z_hit = sum(1 for z in self.a.predict_triple_zodiac() if z in actual_zodiacs) / 3.0
                s_hit = 1.0 if actual_special in self.a.predict_special_codes(8) else 0.0
            elif name == "adversarial":
                z_hit = sum(1 for z in self.a.predict_triple_zodiac() if z in actual_zodiacs) / 3.0
                s_hit = 1.0 if actual_special in model.predict_specials(8) else 0.0
            else:
                z_hit = sum(1 for z in model.predict_zodiacs(4) if z in actual_zodiacs) / 4.0
                s_hit = 1.0 if actual_special in model.predict_specials(8) else 0.0
            reward = z_hit * 0.6 + s_hit * 0.4
            self._pulls[name] += 1
            self._rewards[name] += reward
        for name in self._arms:
            n = self._pulls.get(name, 1)
            avg = self._rewards[name] / max(n, 1)
            explore = math.sqrt(2 * math.log(max(total_pulls, 2)) / max(n, 1))
            self._ucb_weights[name] = avg + explore * 0.8
        wt = sum(max(v, 0.01) for v in self._ucb_weights.values())
        for name in self._ucb_weights:
            self._ucb_weights[name] = max(self._ucb_weights[name], 0.01) / wt

    def _surprise_metric(self):
        sp = self.a.special_code_history(30)
        if len(sp) < 15:
            return 0.5
        nums = [s["number"] for s in sp]
        half = len(nums) // 2
        old = Counter(nums[:half])
        new = Counter(nums[half:])
        js = 0.0
        for n in range(1, 50):
            po = old.get(n, 0) / max(half, 1)
            pn = new.get(n, 0) / max(len(nums) - half, 1)
            m = (po + pn) / 2
            if m > 0:
                if po > 0: js += po * math.log2(po / m)
                if pn > 0: js += pn * math.log2(pn / m)
        js /= 2
        self._surprise_history.append(js)
        if len(self._surprise_history) > 20:
            self._surprise_history.pop(0)
        return js

    def _detect_phase(self):
        """相位检测 — 使用历史数据百分位阈值（数据量化驱动）"""
        sp = self.a.special_code_history(50)
        if len(sp) < 20:
            return "raise"
        zodiacs = [s["zodiac"] for s in sp[-20:]]
        unique_z = len(set(zodiacs[-12:]))
        surprise = self._surprise_metric()
        entropy = self._pattern_entropy()
        # 使用从历史数据校准的百分位阈值
        e_hi = self._pct_entropy_high
        e_lo = self._pct_entropy_low
        s_hi = self._pct_surprise_high
        s_lo = self._pct_surprise_low
        u_hi = self._pct_unique_high
        u_lo = self._pct_unique_low
        scores = {"raise": 0, "trap": 0, "kill": 0, "break": 0}
        # raise: 高多样性 + 高熵 + 低惊奇 = 正常发散期
        if unique_z >= u_hi: scores["raise"] += 3
        if entropy >= e_hi: scores["raise"] += 2
        if surprise <= s_lo: scores["raise"] += 1
        # trap: 中等多样性 + 中等熵 + 中等惊奇 = 诱导期
        if u_lo < unique_z < u_hi: scores["trap"] += 3
        if e_lo <= entropy <= e_hi: scores["trap"] += 2
        if s_lo <= surprise <= s_hi: scores["trap"] += 1
        # kill: 低多样性 + 低熵 + 高惊奇 = 收割期
        if unique_z <= u_lo: scores["kill"] += 3
        if entropy <= e_lo: scores["kill"] += 2
        if surprise >= s_hi: scores["kill"] += 2
        # break: 极高惊奇 = 破局期
        if surprise >= s_hi * 1.4: scores["break"] += 4
        if unique_z >= u_hi + 1: scores["break"] += 1
        return max(scores, key=scores.get)

    def _pattern_entropy(self, last_n=20):
        sp = self.a.special_code_history(last_n)
        if len(sp) < 10:
            return 1.0
        freq = Counter(s["number"] for s in sp)
        total = len(sp)
        ent = 0.0
        for cnt in freq.values():
            p = cnt / total
            if p > 0: ent -= p * math.log2(p)
        return ent / max(math.log2(min(49, total)), 0.01)

    def _calibrate_probs(self, scores):
        items = list(scores.items())
        if not items:
            return {}
        vals = [v for _, v in items]
        mv = max(vals)
        exp_vals = [math.exp((v - mv) * 2.5) for v in vals]
        total = sum(exp_vals)
        probs = {items[i][0]: exp_vals[i] / max(total, 0.0001) for i in range(len(items))}
        phase = self._detect_phase()
        if phase == "kill":
            probs = {k: v * 0.6 for k, v in probs.items()}
        elif phase == "break":
            avg = 1.0 / len(probs)
            probs = {k: v * 0.4 + avg * 0.6 for k, v in probs.items()}
        pt = sum(probs.values())
        return {k: v / max(pt, 0.0001) for k, v in probs.items()}

    def predict_zodiacs(self, count=4):
        phase = self._detect_phase()
        az = self.ema.predict_zodiacs(count)  # adversarial用EMA替代
        mz = self.markov.predict_zodiacs(count)
        cz = self.monte.predict_zodiacs(count)
        ez = self.ema.predict_zodiacs(count)
        tz = self.a.predict_triple_zodiac()
        preds = {"adversarial": az, "markov": mz, "monte": cz, "ema": ez, "triple": tz}
        scores = Counter()
        for name, pred in preds.items():
            w = self._ucb_weights.get(name, 0.25)
            if phase == "break" and name == "simple": w *= 0.5
            if phase == "trap" and name == "ema": w *= 1.3
            for i, z in enumerate(pred[:count]):
                scores[z] += w * (count - i)
        cal = self._calibrate_probs(dict(scores))
        return sorted(cal, key=cal.get, reverse=True)[:count]

    def adapt(self, actual_special):
        drift_triggered = False
        if hasattr(self, "_last_special_pred"):
            hit = 1 if actual_special in self._last_special_pred else 0
            if hit:
                self._ensemble_misses = 0
                self._explore_boost = max(0.5, self._explore_boost - 0.1)
            else:
                self._ensemble_misses += 1
                if self._ensemble_misses >= 3:
                    self._explore_boost = min(3.0, self._explore_boost + 0.3)
                    drift_triggered = True
                if self._ensemble_misses >= 5:
                    self._ucb_weights = {k: 0.25 for k in self._arms}
                    self._pulls = {k: 1 for k in self._arms}
                    self._rewards = {k: 0.0 for k in self._arms}
                    self._ensemble_misses = 0
                    drift_triggered = True
            if hasattr(self, "simple"):
                self.simple.adapt(actual_special)
        return drift_triggered

    def predict_specials(self, count=8):
        phase = self._detect_phase()
        # Sliding window recalibration every 15 predictions
        self._predict_counter += 1
        if self._predict_counter % 15 == 0 and len(self.a.data) >= 60:
            self._calibrate_from_history()
        sp = self.a.special_code_history(30)
        as_ = self.adversarial.predict_specials(count)
        ms = self.markov.predict_specials(count)
        cs = self.monte.predict_specials(count)
        es = self.ema.predict_specials(count)
        fs = self.a.predict_special_codes(count)
        preds = {"adversarial": as_, "markov": ms, "monte": cs, "ema": es, "triple": fs}
        scores = Counter()
        for name, pred in preds.items():
            w = self._ucb_weights.get(name, 0.25)
            for i, n in enumerate(pred[:count]):
                scores[n] += w * (count - i)
        freq_10 = Counter(s["number"] for s in sp[-10:])
        for n in list(scores.keys()):
            if freq_10.get(n, 0) >= 2: scores[n] *= 0.5
            if n not in freq_10: scores[n] *= 1.3
        cal = self._calibrate_probs(dict(scores))
        result = sorted(cal, key=cal.get, reverse=True)[:count]
        
        # Prediction diversity: exponential decay on repeat predictions
        for n in list(scores.keys()):
            recent_pred_count = sum(1 for past_preds in self._pred_history[-5:]
                                    for p in past_preds if p == n)
            if recent_pred_count >= 1:
                scores[n] *= 0.85 ** recent_pred_count
        cal2 = self._calibrate_probs(dict(scores))
        result = sorted(cal2, key=cal2.get, reverse=True)[:count]
        
        # Random injection: 35% chance to replace 1-3 with cold numbers
        import random as _random
        sp_nums_set = set(s["number"] for s in sp[-30:])
        cold_pool = [n for n in range(1, 50) if n not in sp_nums_set]
        if cold_pool and _random.random() < 0.20:
            replace_count = _random.randint(1, min(2, len(cold_pool)))
            for _ in range(replace_count):
                pos = _random.randint(0, count - 1)
                result[pos] = _random.choice(cold_pool)
        
        self._last_special_pred = result
        self._pred_history.append(list(result))
        if len(self._pred_history) > 20:
            self._pred_history.pop(0)
        return result
    def predict_waves(self, count=1):
        sp = self.a.special_code_history(30)
        waves = [num_to_wave(s["number"])[0] for s in sp]
        phase = self._detect_phase()
        c = Counter(waves)
        streak, last = 0, waves[-1]
        for w in reversed(waves):
            if w == last: streak += 1
            else: break
        if streak >= 3 and phase != "raise":
            c[last] = max(0, c[last] - streak)
        return [w for w, _ in c.most_common(count)]

    def predict_odd_even(self, count=1):
        sp = self.a.special_code_history(30)
        oe = ["单" if s["number"] % 2 == 1 else "双" for s in sp]
        phase = self._detect_phase()
        c = Counter(oe)
        streak, last = 0, oe[-1]
        for o in reversed(oe):
            if o == last: streak += 1
            else: break
        if streak >= 3 and phase != "raise":
            c[last] = max(0, c[last] - streak)
        return [o for o, _ in c.most_common(count)]

    def feedback(self, actual_zodiacs, actual_special):
        self._ucb_update(actual_zodiacs, actual_special)

    def all_model_results(self):
        r = {}
        for name, model in [("Markov", self.markov), ("MonteCarlo", self.monte), ("EMA", self.ema)]:
            r[name] = (model.predict_zodiacs(4), model.predict_specials(8))
        r["Ensemble"] = (self.predict_zodiacs(4), self.predict_specials(8))
        r["Phase"] = self._detect_phase()
        r["Entropy"] = round(self._pattern_entropy(), 3)
        r["Surprise"] = round(self._surprise_metric(), 3)
        r["UCB"] = {k: round(v, 3) for k, v in self._ucb_weights.items()}
        return r

    def _zodiac_gaps(self, last_n=180):
        recent = self.a.data[-last_n:]
        gap = {z: last_n for z in ZODIAC_MAP}
        for i, r in enumerate(reversed(recent)):
            nums = self.a.get_numbers(r)
            if len(nums) >= 7:
                z = num_to_zodiac(nums[6])
                if gap[z] == last_n: gap[z] = i
        return gap

    def _flat_zodiac_freq(self, last_n=30):
        recent = self.a.data[-last_n:]
        fz = Counter()
        for r in recent:
            for n in self.a.get_numbers(r)[:6]:
                fz[num_to_zodiac(n)] += 1
        return fz

    def _flat_reference(self, lag=3):
        if len(self.a.data) < lag + 1: return set()
        ref = self.a.data[-lag - 1]
        nums = self.a.get_numbers(ref)
        return {num_to_zodiac(n) for n in nums[:6]} if len(nums) >= 6 else set()

    def _house_strategy(self):
        sp = self.a.special_code_history(80)
        if len(sp) < 30: return {}
        last_dt = self.a.data[-1].get("openTime", "") if self.a.data else ""
        plan = {}
        hot_10 = Counter(s["number"] for s in sp[-10:])
        hot_20 = Counter(s["number"] for s in sp[-20:])
        gaps = self._zodiac_gaps(180)
        wave_seq = [num_to_wave(s["number"])[0] for s in sp[-15:]]
        ws, lw = 0, wave_seq[-1]
        for w in reversed(wave_seq):
            if w == lw: ws += 1
            else: break
        oe_seq = [num_to_odd_even(s["number"])[0] for s in sp[-15:]]
        os_, lo = 0, oe_seq[-1]
        for o in reversed(oe_seq):
            if o == lo: os_ += 1
            else: break
        lzs = [s["zodiac"] for s in sp[-5:]]
        zs = 0
        lz = lzs[-1] if lzs else ""
        for z in reversed(lzs):
            if z == lz: zs += 1
            else: break
        sz_seq = ["大" if s["number"] > 25 else "小" for s in sp[-15:]]
        ss, ls = 0, sz_seq[-1]
        for s in reversed(sz_seq):
            if s == ls: ss += 1
            else: break
        def bs_oe(n): return ("大" if n > 24 else "小") + ("单" if n % 2 == 1 else "双")
        bsoe_seq = [bs_oe(s["number"]) for s in sp[-15:]]
        bs_s, lb = 0, bsoe_seq[-1]
        for b in reversed(bsoe_seq):
            if b == lb: bs_s += 1
            else: break
        popular = {}
        for z in ZODIAC_MAP:
            f = sum(1 for s in sp[-30:] if s["zodiac"] == z)
            if f >= 4: popular[z] = max(0.4, 1 - (f - 3) * 0.15)
        for n in range(1, 50):
            z = num_to_zodiac(n, last_dt)
            w = 1.0
            if hot_10.get(n, 0) >= 2: w *= 0.3
            elif hot_20.get(n, 0) >= 3: w *= 0.5
            if gaps.get(z, 0) > 60: w *= 1.3
            if ws >= 4 and num_to_wave(n)[0] == lw: w *= 0.55
            elif ws >= 3 and num_to_wave(n)[0] == lw: w *= 0.72
            if os_ >= 4 and num_to_odd_even(n)[0] == lo: w *= 0.6
            elif os_ >= 3 and num_to_odd_even(n)[0] == lo: w *= 0.78
            if zs >= 2 and z == lz: w *= 0.4
            if ss >= 4 and (("大" if n > 25 else "小") == ls): w *= 0.65
            if bs_s >= 3 and bs_oe(n) == lb: w *= 0.65
            if z in popular: w *= popular[z]
            plan[n] = max(w, 0.30)
        return plan

    def _cross_pressure(self):
        sp = self.a.special_code_history(60)
        if len(sp) < 20: return {}
        def tag(n):
            last_dt_cp = self.a.data[-1].get("openTime", "") if self.a.data else ""
            z = num_to_zodiac(n, last_dt_cp)
            return {"波": num_to_wave(n)[0], "单双": "单" if n % 2 == 1 else "双",
                    "大小": "大" if n > 24 else "小", "头": str(n//10)+"头",
                    "尾": str(n%10)+"尾",
                    "大小单双": ("大" if n > 24 else "小")+("单" if n % 2 == 1 else "双"),
                    "家野": "家" if z in "牛馬羊雞狗豬" else "野", "肖": z, "五行": num_to_wuxing(n)}
        dim_hot = {}
        for s in sp[-20:]:
            t = tag(s["number"])
            for d, v in t.items():
                dim_hot.setdefault(d, {})[v] = dim_hot.setdefault(d, {}).get(v, 0) + 1
        dim_streak = {}
        for dn in ["波","单双","大小","头","尾","大小单双","家野","五行"]:
            seq = [tag(s["number"])[dn] for s in sp[-12:]]
            st, la = 0, seq[-1]
            for v in reversed(seq):
                if v == la: st += 1
                else: break
            dim_streak[dn] = (st, la)
        pressure = {}
        for n in range(1, 50):
            t = tag(n)
            sc = 0.0
            for d, v in t.items():
                dd = dim_hot.get(d, {})
                hot = dd.get(v, 0)
                dc = len(dd)
                if dc > 0:
                    avg = sum(dd.values()) / dc
                    if hot > avg * 1.3: sc -= 0.15
                    elif hot < avg * 0.6: sc += 0.12
                if d in dim_streak:
                    sv, lv = dim_streak[d]
                    if sv >= 3 and v == lv: sc -= 0.2
                if hot == 0: sc += 0.08
            pressure[n] = max(sc, -1.0)
        if pressure:
            mn, mx = min(pressure.values()), max(pressure.values())
            if mx > mn:
                for n in pressure:
                    pressure[n] = 0.3 + (pressure[n] - mn) / (mx - mn)
        return pressure
