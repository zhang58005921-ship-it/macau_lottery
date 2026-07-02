#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import sys, json, os, ssl, random, math, itertools
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
import threading
import macaujc_api
import tkinter.messagebox as messagebox

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

# ---- 共享预测引擎 ----
import sys, os
_sd = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shared')
if _sd not in sys.path:
    sys.path.insert(0, _sd)
from engine import (
    LotteryAnalyzer, MarkovChainModel, MonteCarloModel, WeightedEMAModel,
    SimpleSpecialPredictor, AdversarialPredictor, EightLinePredictor,
    EnsemblePredictor, sync_latest
)
# 更新数据文件路径指向 shared 目录
DATA_FILE = os.path.join(_sd, 'macaujc_data.json')
ZODIAC_YEAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zodiac_year_config.json')
class App:
    def __init__(self, root):
        self.root = root
        root.title("数字游戏预测")
        root.geometry("1280x960")
        root.minsize(1024, 800)
        root.configure(bg=BG)
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=[18,6], font=("Segoe UI",10), background=CARD, foreground=TXT)
        s.map("TNotebook.Tab", background=[("selected",BG)], foreground=[("selected",ACC)])
        s.configure("TFrame", background=BG)
        self.analyzer = None
        self.data = None
        self.ensemble = None
        self.status_var = tk.StringVar(value="加载中...")
        tk.Label(root, textvariable=self.status_var, bg=CARD, fg=SUB, font=("Segoe UI",9), anchor="w", padx=12, pady=4).pack(side=tk.BOTTOM, fill=tk.X)
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill=tk.X, padx=20, pady=(12,0))
        tk.Label(hdr, text="数字游戏预测", font=("Segoe UI",20,"bold"), fg=GLD, bg=BG).pack(side=tk.LEFT)
        self.zbtn = tk.Button(hdr, text=" 生肖配置", command=self._zodiac_year_config_dialog, bg=PUR, fg="#fff", font=("Segoe UI",10), relief="flat", padx=16, pady=4, cursor="hand2")
        self.zbtn.pack(side=tk.RIGHT, padx=(0,8))
        self.mbtn = tk.Button(hdr, text=" 手动录入", command=self._manual_entry, bg=GRN, fg="#000", font=("Segoe UI",10), relief="flat", padx=16, pady=4, cursor="hand2")
        self.mbtn.pack(side=tk.RIGHT, padx=(0,8))
        self.rbtn = tk.Button(hdr, text=" 刷新数据", command=self.refresh, bg=ACC, fg="#fff", font=("Segoe UI",10), relief="flat", padx=16, pady=4, cursor="hand2")
        self.rbtn.pack(side=tk.RIGHT)
        self.nb = ttk.Notebook(root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.pf = ttk.Frame(self.nb)
        self.sf = ttk.Frame(self.nb)
        self.tf = ttk.Frame(self.nb)
        self.hf = ttk.Frame(self.nb)
        self.mf = ttk.Frame(self.nb)
        self.nb.add(self.pf, text="  预测  ")
        self.nb.add(self.sf, text="  分析  ")
        self.nb.add(self.tf, text="  走势  ")
        self.nb.add(self.hf, text="  历史  ")
        self.nb.add(self.mf, text="  模型  ")
        self.zf = ttk.Frame(self.nb)
        self.ff = ttk.Frame(self.nb)
        self.nb.add(self.zf, text="  生肖追踪  ")
        self.nb.add(self.ff, text="  采集  ")
        self._init_predict()
        self._init_stats()
        self._init_trend()
        self._init_history()
        self._init_ml()
        self._init_zodiac_track()
        self._init_data_mgr()
        threading.Thread(target=self._load, daemon=True).start()

    def _card(self, parent, title, sub="", acc=ACC):
        c = tk.Frame(parent, bg=CARD, highlightbackground=BDR, highlightthickness=1)
        inner = tk.Frame(c, bg=CARD)
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
        tk.Label(inner, text=title, font=("Segoe UI",13,"bold"), fg=acc, bg=CARD).pack(anchor="w")
        if sub:
            tk.Label(inner, text=sub, font=("Segoe UI",9), fg=SUB, bg=CARD).pack(anchor="w", pady=(2,8))
        return c, inner

    def _load(self):
        self.data = sorted(load_data(), key=lambda x: int(x.get("expect",0)))
        if self.data:
            self.analyzer = LotteryAnalyzer(self.data)
            self.ensemble = EnsemblePredictor(self.analyzer)
            self.root.after(0, self._ready)
        else:
            self.status_var.set("无本地数据，正在从网络获取...")
            self.root.after(100, self.refresh)
    def refresh(self):
        self.status_var.set("刷新中...")
        self.rbtn.config(state=tk.DISABLED)
        def r():
            nd = fetch_data()
            if nd:
                ex = set()
                if os.path.exists(DATA_FILE):
                    ex = {d["expect"] for d in load_data()}
                ad = [d for d in nd if d.get("expect") not in ex]
                old = load_data() if os.path.exists(DATA_FILE) else []
                all_d = sorted(old + ad, key=lambda x: int(x.get("expect",0)))
                save_data(all_d)
                self.data = all_d
            else:
                self.data = load_data()
            self.analyzer = LotteryAnalyzer(self.data)
            self.ensemble = EnsemblePredictor(self.analyzer)
            self.root.after(0, self._ready)
            self.root.after(0, lambda: self.rbtn.config(state=tk.NORMAL))
        threading.Thread(target=r, daemon=True).start()

    def _ready(self):
        if not self.data:
            self.status_var.set("加载失败，请检查网络并点击刷新")
            return
        lt = self.data[-1]
        self.status_var.set(" {} 条记录 | 最新: #{}".format(len(self.data), lt.get("expect","?")))
        self.rbtn.config(state=tk.NORMAL)
        self._up_predict()
        self._up_stats()
        self._up_trend()
        self._up_history()
        self._up_zodiac_track()
        self._up_ml()
    def _init_predict(self):
        m = tk.Frame(self.pf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        ci, ii = self._card(m, "最新开奖", acc=GLD)
        ci.pack(fill=tk.X, pady=(0,12))
        self.ll = tk.Label(ii, text="加载中...", font=("Segoe UI",10), fg=TXT, bg=CARD, justify=tk.LEFT, wraplength=900)
        self.ll.pack(fill=tk.X)
        sf = tk.Frame(m, bg=BG)
        sf.pack(fill=tk.X, pady=(0,10))
        tk.Label(sf, text="模型:", fg=SUB, bg=BG, font=("Segoe UI",10)).pack(side=tk.LEFT, padx=(0,8))
        self.mv = tk.StringVar(value="集成模型")
        mm = ttk.Combobox(sf, textvariable=self.mv, values=["集成模型","对抗博弈","Simple(轻量)","Markov Chain","Monte Carlo","Weighted EMA","Frequency"], state="readonly", width=16)
        mm.pack(side=tk.LEFT)
        mm.bind("<<ComboboxSelected>>", lambda e: self._up_predict())
        tk.Button(sf, text="开始预测", command=self._up_predict, bg=GRN, fg="#000", font=("Segoe UI",10,"bold"), relief="flat", padx=16, pady=4, cursor="hand2").pack(side=tk.RIGHT)
        g = tk.Frame(m, bg=BG)
        g.pack(fill=tk.BOTH, expand=True)
        c1, i1 = self._card(g, "三连肖", "最可能出现的 前三", GRN)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=6)
        self.tl = tk.Label(i1, text="---", font=("Segoe UI",24,"bold"), fg=GRN, bg=CARD)
        self.tl.pack(anchor="w", pady=4)
        c2, i2 = self._card(g, "四连肖", "最可能出现的 前四", ACC)
        c2.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=6)
        self.ql = tk.Label(i2, text="---", font=("Segoe UI",20,"bold"), fg=ACC, bg=CARD)
        self.ql.pack(anchor="w", pady=4)
        c5, i5 = self._card(g, "一码中特", "集成模型最推荐号码", GLD)
        c5.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=6)
        self.om_frame = tk.Frame(i5, bg=CARD)
        self.om_label = tk.Label(self.om_frame, text="---", font=("Segoe UI", 48, "bold"), fg=GLD, bg=CARD)
        self.om_label.pack(side=tk.LEFT, padx=10)
        self.om_info = tk.Label(self.om_frame, text="", font=("Segoe UI", 11), fg=SUB, bg=CARD, justify=tk.LEFT)
        self.om_info.pack(side=tk.LEFT, padx=10, pady=8)
        self.om_frame.pack(anchor="center", pady=10)
        c3, i3 = self._card(g, "特码预测", "频率 + 近期罚分 + 冷号加分", RED)
        c3.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=6)
        self.sl_frame = tk.Frame(i3, bg=CARD)
        self.sl_labels = []
        self.sl_frame.pack(anchor="w", pady=4, fill=tk.X)
        c4, i4 = self._card(g, "提示", "以上结果为统计推测，仅供参考", PUR)
        c4.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=6)
        self.cl = tk.Label(i4, text="", font=("Segoe UI",9), fg=PUR, bg=CARD, justify=tk.LEFT)
        self.cl.pack(fill=tk.X)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)

    def _up_predict(self):
        if not self.ensemble:
            return
        a = self.analyzer
        lt = self.data[-1]
        nums = a.get_numbers(lt)
        zods = a.get_zodiacs(lt)
        # ---- 自适应偏移修复：反馈上期结果 ----
        if len(nums) >= 7:
            actual_sp = nums[6]
            actual_zods = set(zods)
            try:
                self.ensemble.adapt(actual_sp)
                self.ensemble.feedback(actual_zods, actual_sp)
            except Exception:
                pass
        ns = "  ".join("{}".format(n)+"("+num_to_zodiac(n)+")" for n in nums)
        self.ll.config(text="#" + str(lt.get("expect","?")) + " | " + str(lt.get("openTime","")) + chr(10) + ns)
        m = self.mv.get()
        if m == "对抗博弈":
            t = a.predict_triple_zodiac()
            q = a.predict_quad_zodiac()
            s = self.ensemble.adversarial.predict_specials(8)
        elif m == "Simple(轻量)":
            t = a.predict_triple_zodiac()
            q = a.predict_quad_zodiac()
            s = self.ensemble.simple.predict(8)
        elif m == "Markov Chain":
            t = self.ensemble.markov.predict_zodiacs(3)
            q = self.ensemble.markov.predict_zodiacs(4)
            s = self.ensemble.markov.predict_specials(8)
        elif m == "Monte Carlo":
            t = self.ensemble.monte.predict_zodiacs(3)
            q = self.ensemble.monte.predict_zodiacs(4)
            s = self.ensemble.monte.predict_specials(8)
        elif m == "Weighted EMA":
            t = self.ensemble.ema.predict_zodiacs(3)
            q = self.ensemble.ema.predict_zodiacs(4)
            s = self.ensemble.ema.predict_specials(8)
        elif m == "Frequency":
            t = a.predict_triple_zodiac()
            q = a.predict_quad_zodiac()
            s = a.predict_special_codes(8)
        else:
            t = self.ensemble.predict_zodiacs(3)
            q = self.ensemble.predict_zodiacs(4)
            s = self.ensemble.predict_specials(8)
        self.tl.config(text="  ".join("[{}]".format(z) for z in t))
        self.ql.config(text="  ".join("[{}]".format(z) for z in q))
        for w in self.sl_labels:
            w.destroy()
        self.sl_labels.clear()
        for n in s:
            wave_name, wave_color = num_to_wave(n)
            lbl = tk.Label(self.sl_frame, text="{:02d}({})".format(n, num_to_zodiac(n)),
                          font=("Segoe UI", 16, "bold"), fg=wave_color, bg=CARD,
                          padx=6, pady=2)
            lbl.pack(side=tk.LEFT)
            self.sl_labels.append(lbl)
        from datetime import datetime
        waves = self.ensemble.predict_waves(1)
        oe_pred = self.ensemble.predict_odd_even(1)
        # 一码中特
        top_one = s[0]
        oz = num_to_zodiac(top_one)
        ow, oc = num_to_wave(top_one)
        ooe, ooec = num_to_odd_even(top_one)
        self.om_label.config(text="{:02d}".format(top_one), fg=oc)
        top_house = self.ensemble._house_strategy().get(top_one, 0.5)
        self.om_info.config(
            text="生肖: {}   波色: {}   单双: {} | 庄家意愿: {:.0%}".format(
                oz, ow, ooe, top_house),
            fg=oc)
        self.cl.config(text="模型: {} | {} 条数据 | 波色: {} | 单双: {} | {}".format(
            m, len(self.data), "/".join(waves), "/".join(oe_pred), datetime.now().strftime("%Y-%m-%d %H:%M")))

    def _init_stats(self):
        m = tk.Frame(self.sf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        L = tk.Frame(m, bg=BG)
        L.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        R = tk.Frame(m, bg=BG)
        R.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8,0))
        c1, i1 = self._card(L, "号码频率", acc=GRN)
        c1.pack(fill=tk.BOTH, expand=True, pady=(0,6))
        self.ft = tk.Text(i1, bg=BG, fg=GRN, font=("Consolas",9), height=14, relief="flat", padx=4, pady=2, wrap=tk.WORD)
        self.ft.pack(fill=tk.BOTH, expand=True)
        c2, i2 = self._card(L, "冷热号", acc=RED)
        c2.pack(fill=tk.BOTH, expand=True, pady=(6,0))
        self.ht = tk.Text(i2, bg=BG, fg=TXT, font=("Segoe UI",10), height=8, relief="flat", padx=4, pady=2)
        self.ht.pack(fill=tk.BOTH, expand=True)
        c3, i3 = self._card(R, "生肖频率", acc=GLD)
        c3.pack(fill=tk.BOTH, expand=True, pady=(0,6))
        self.zt = tk.Text(i3, bg=BG, fg=GLD, font=("Consolas",10), height=14, relief="flat", padx=4, pady=2, wrap=tk.WORD)
        self.zt.pack(fill=tk.BOTH, expand=True)
        c4, i4 = self._card(R, "特码预测", acc=ORG)
        c4.pack(fill=tk.BOTH, expand=True, pady=(6,0))
        self.st = tk.Text(i4, bg=BG, fg=ORG, font=("Consolas",9), height=8, relief="flat", padx=4, pady=2)
        self.st.pack(fill=tk.BOTH, expand=True)

    def _up_stats(self):
        if not self.analyzer:
            return
        a = self.analyzer
        nc, zc = a.frequency_stats(100)
        self.ft.delete(1.0, tk.END)
        for n in range(1,50):
            c = nc.get(n,0)
            bar = chr(9608) * min(c, 40)
            tag = "热" if c > 15 else ("冷" if c < 8 else "")
            z = num_to_zodiac(n)
            self.ft.insert(tk.END, "{:02d}({}) {} {}{}".format(n, z, bar, c, tag) + chr(10))
        hot, cold, _ = a.hot_cold_numbers(50)
        self.ht.delete(1.0, tk.END)
        self.ht.insert(tk.END, "热号: ", "hot")
        self.ht.insert(tk.END, " ".join("{:02d}({})".format(x, num_to_zodiac(x)) for x in hot))
        self.ht.insert(tk.END, "\n\nCOLD: ", "cold")
        self.ht.insert(tk.END, " ".join("{:02d}({})".format(x, num_to_zodiac(x)) for x in cold))
        self.ht.tag_config("hot", foreground=RED, font=("Segoe UI",10,"bold"))
        self.ht.tag_config("cold", foreground=ACC, font=("Segoe UI",10,"bold"))
        self.zt.delete(1.0, tk.END)
        for z in sorted(ZODIAC_MAP, key=lambda x: zc.get(x,0), reverse=True):
            c = zc.get(z,0)
            self.zt.insert(tk.END, "{}  {} {}".format(z, chr(9608) * min(c, 40), c) + chr(10))
        sp = a.special_code_history(30)
        self.st.delete(1.0, tk.END)
        sc = Counter(s["number"] for s in sp)
        for n, c in sc.most_common(20):
            self.st.insert(tk.END, "{:02d}({}) x{}  ".format(n, num_to_zodiac(n), c))
        self.st.insert(tk.END, "\n\n--- 近期特码 ---\n")
        for s in reversed(sp[-15:]):
            self.st.insert(tk.END, "{} -> {:02d}({})".format(s["expect"], s["number"], s["zodiac"]) + chr(10))

        wc = a.wave_stats(100)
        oc = a.odd_even_stats(100)
        self.st.insert(tk.END, "\n--- 波色分布(近100期) ---\n")
        for w in ["红波", "蓝波", "绿波"]:
            c = wc.get(w, 0)
            bar = chr(9608) * min(c, 30)
            self.st.insert(tk.END, "{}: {} {}\n".format(w, bar, c))
        self.st.insert(tk.END, "\n--- 单双分布(近100期) ---\n")
        total_oe = sum(oc.values()) or 1
        self.st.insert(tk.END, "单: {} ({:.0f}%)  双: {} ({:.0f}%)\n".format(
            oc.get("单",0), oc.get("单",0)/total_oe*100,
            oc.get("双",0), oc.get("双",0)/total_oe*100))

    def _init_trend(self):
        m = tk.Frame(self.tf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        c1, i1 = self._card(m, "号码分布矩阵（近50期）", acc=GLD)
        c1.pack(fill=tk.BOTH, expand=True)
        tf = tk.Frame(i1, bg=CARD)
        tf.pack(fill=tk.BOTH, expand=True)
        self.tt = tk.Text(tf, bg=BG, fg=TXT, font=("Consolas",9), relief="flat", padx=8, pady=4)
        sb = tk.Scrollbar(tf, command=self.tt.yview)
        self.tt.configure(yscrollcommand=sb.set)
        self.tt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _up_trend(self):
        if not self.analyzer:
            return
        a = self.analyzer
        self.tt.delete(1.0, tk.END)
        self.tt.insert(tk.END, "{:>6} {:>12} {:>49} {}\n".format("期号", "日期", "矩阵", "生肖"), "hdr")
        self.tt.insert(tk.END, "-" * 120 + "\n")
        for r in reversed(self.data[-50:]):
            ex = r.get("expect","")[-4:]
            ts = (r.get("openTime","") or "")[:10]
            nums = a.get_numbers(r)
            zods = a.get_zodiacs(r)
            parts = []
            for n in range(1,50):
                if len(nums) >= 7 and n == nums[6]:
                    parts.append("*")
                elif n in nums[:6]:
                    parts.append("O")
                else:
                    parts.append(".")
            self.tt.insert(tk.END, "{:>6} {} {} ".format(ex, ts, "".join(parts)))
            if zods:
                self.tt.insert(tk.END, " ".join(zods[:6]) + " | " + (zods[6] if len(zods) >= 7 else ""))
            self.tt.insert(tk.END, "\n")
        self.tt.insert(tk.END, "\nO 正码  * 特码\n", "leg")
        self.tt.tag_config("hdr", foreground=GLD, font=("Consolas",9,"bold"))
        self.tt.tag_config("leg", foreground=SUB, font=("Segoe UI",9))

    def _init_history(self):
        m = tk.Frame(self.hf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        hdr = tk.Frame(m, bg=BG)
        hdr.pack(fill=tk.X, pady=(0,12))
        tk.Label(hdr, text="开奖历史", font=("Segoe UI",16,"bold"), fg=GLD, bg=BG).pack(side=tk.LEFT)
        cvs = tk.Canvas(m, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(m, orient="vertical", command=cvs.yview)
        self.his_frame = tk.Frame(cvs, bg=BG)
        self.his_frame.bind("<Configure>", lambda e: cvs.configure(scrollregion=cvs.bbox("all")))
        win = cvs.create_window((0, 0), window=self.his_frame, anchor="nw")
        cvs.configure(yscrollcommand=sb.set)
        def _on_canvas_resize(event):
            if event.width > 1:
                cvs.itemconfig(win, width=event.width)
        cvs.bind("<Configure>", _on_canvas_resize)
        cvs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.his_canvas = cvs
        def _on_mousewheel(event):
            cvs.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.his_canvas.bind("<MouseWheel>", _on_mousewheel)

    def _up_history(self):
        if not self.analyzer:
            return
        a = self.analyzer
        for w in self.his_frame.winfo_children():
            w.destroy()
        hdr = tk.Frame(self.his_frame, bg=CARD)
        hdr.pack(fill=tk.X, pady=(0, 3))
        for text, w in [("期号", 10), ("开奖时间", 20), ("中奖号码", 64), ("单双", 10)]:
            tk.Label(hdr, text=text, fg=GLD, bg=CARD, font=("Segoe UI", 12, "bold"), width=w, anchor="w").pack(side=tk.LEFT, padx=3)
        for r in reversed(self.data[-50:]):
            row = tk.Frame(self.his_frame, bg=BG)
            row.pack(fill=tk.X, pady=2)
            ex = r.get("expect", "")[-4:]
            ts = (r.get("openTime", "") or "")[:10]
            nums = a.get_numbers(r)
            tk.Label(row, text="第{}期".format(ex), fg=TXT, bg=BG, font=("Segoe UI", 11), width=10, anchor="w").pack(side=tk.LEFT, padx=3)
            tk.Label(row, text=ts, fg=SUB, bg=BG, font=("Segoe UI", 11), width=20, anchor="w").pack(side=tk.LEFT, padx=3)
            bf = tk.Frame(row, bg=BG)
            bf.pack(side=tk.LEFT, padx=3)
            for i_n, n in enumerate(nums):
                wave_name, wave_color = num_to_wave(n)
                zodiac = num_to_zodiac(n)
                if i_n == 6:
                    tk.Label(bf, text="+", fg=GLD, bg=BG, font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=3)
                ball = tk.Frame(bf, bg=wave_color, width=44, height=44)
                ball.pack_propagate(False)
                ball.pack(side=tk.LEFT, padx=2)
                tk.Label(ball, text=str(n), fg="#fff", bg=wave_color, font=("Segoe UI", 11, "bold")).pack()
                tk.Label(ball, text=zodiac, fg="#fff", bg=wave_color, font=("Segoe UI", 9)).pack()
            oes = [num_to_odd_even(n) for n in nums[:6]]
            odd_count = sum(1 for o, _ in oes if o == "单")
            even_count = 6 - odd_count
            oe_color = "#ff8c00" if odd_count > even_count else "#8888ff" if even_count > odd_count else SUB
            tk.Label(row, text="{}单{}双".format(odd_count, even_count), fg=oe_color, bg=BG, font=("Segoe UI", 11), width=10, anchor="w").pack(side=tk.LEFT, padx=3)


    def _init_ml(self):
        m = tk.Frame(self.mf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        c1, i1 = self._card(m, "模型对比", "所有模型并列对比，集成模型加权投票", PUR)
        c1.pack(fill=tk.BOTH, expand=True)
        cols = ("模型名称", "三连肖", "四连肖", "特码预测")
        self.mt = ttk.Treeview(i1, columns=cols, show="headings", height=6)
        for col in cols:
            self.mt.heading(col, text=col)
            self.mt.column(col, width=180 if col != "模型名称" else 140, anchor="w")
        self.mt.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        ss = ttk.Style()
        ss.configure("Treeview", background=CARD, foreground=TXT, fieldbackground=CARD, rowheight=30)
        ss.configure("Treeview.Heading", background=BG, foreground=GLD, font=("Segoe UI",10,"bold"))
        ss.map("Treeview", background=[("selected","#1f6feb")])
        df = tk.Frame(i1, bg=CARD)
        df.pack(fill=tk.X)
        desc = "马尔可夫链: 期间转移概率矩阵 | 蒙特卡洛: 2000次随机模拟 | 指数衰减: 衰减系数0.92，近期加权更高 | 频率统计: 计数+遗漏加分 | 集成模型: 加权投票 (0.35/0.25/0.25/0.15)"
        tk.Label(df, text=desc, font=("Consolas",9), fg=SUB, bg=CARD, justify=tk.LEFT).pack(anchor="w", padx=4)

    def _up_ml(self):
        if not self.ensemble:
            return
        for item in self.mt.get_children():
            self.mt.delete(item)
        for model, (zods, specials) in self.ensemble.all_model_results().items():
            zs = "  ".join("[{}]".format(z) for z in zods)
            ss_text = "  ".join("{:02d}({})".format(n, num_to_zodiac(n)) for n in specials)
            tag = "ens" if model == "集成模型" else "norm"
            self.mt.insert("", tk.END, values=(model, zs, zs, ss_text), tags=(tag,))
        self.mt.tag_configure("ens", background="#1a2332", font=("Segoe UI",10,"bold"))

    def _init_zodiac_track(self):
        """生肖特码追踪 - 柱状图展示近180期未开期数"""
        m = tk.Frame(self.zf, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        hdr = tk.Frame(m, bg=BG)
        hdr.pack(fill=tk.X, pady=(0,12))
        tk.Label(hdr, text="特码生肖追踪", font=("Segoe UI",16,"bold"), fg=GLD, bg=BG).pack(side=tk.LEFT)
        tk.Label(hdr, text="柱高 = 未开期数 | 绿色 = 最新期已开 | 近180期统计", fg=SUB, bg=BG, font=("Segoe UI",9)).pack(side=tk.RIGHT)
        self.zf_cvs = tk.Canvas(m, bg=BG, highlightthickness=0, height=320)
        self.zf_cvs.pack(fill=tk.BOTH, expand=True)

    def _up_zodiac_track(self):
        """生肖特码追踪 - 圆柱体柱状图，12生肖，180期统计"""
        if not self.analyzer:
            return
        a = self.analyzer
        cvs = self.zf_cvs
        cvs.delete("all")
        w = cvs.winfo_width()
        if w < 100: w = 900
        h = cvs.winfo_height()
        if h < 50: h = 320
        recent = self.data[-180:]
        gap = {z: 180 for z in ZODIAC_MAP}
        latest_zodiac = None
        if recent:
            nums = a.get_numbers(recent[-1])
            if len(nums) >= 7:
                latest_zodiac = num_to_zodiac(nums[6])
        for i, r in enumerate(reversed(recent)):
            nums = a.get_numbers(r)
            if len(nums) >= 7:
                z = num_to_zodiac(nums[6])
                if gap[z] == 180:
                    gap[z] = i
        n = len(ZODIAC_MAP)
        bar_w = max((w - 160) // n - 10, 24)
        max_gap = max(max(gap.values()), 1)
        base_y = h - 55
        bar_area_h = h - 100
        # 背景网格线
        for level in range(0, max_gap + 1, max(1, max_gap // 5)):
            ly = base_y - int((level / max_gap) * bar_area_h)
            cvs.create_line(60, ly, w - 40, ly, fill="#1a2233", width=1, dash=(2, 6))
            cvs.create_text(50, ly, text=str(level), fill=SUB, font=("Segoe UI", 8), anchor="e")
        # 基线
        cvs.create_line(60, base_y, w - 40, base_y, fill=BDR, width=2)
        # 每根圆柱
        for idx, z in enumerate(ZODIAC_MAP):
            g = gap[z]
            x0 = 70 + idx * (bar_w + 10)
            x1 = x0 + bar_w
            bar_h = int((g / max_gap) * bar_area_h) if g > 0 else 6
            bar_h = max(bar_h, 6)
            top_y = base_y - bar_h
            rx = bar_w // 2
            ry = 6
            # 颜色分级：绿(已开) → 黄(短) → 橙(中) → 红(长)
            if g == 0:
                color, dark, light = GRN, "#1a6b2a", "#7df07d"
            elif g <= 5:
                color, dark, light = "#4ae04a", "#1f6b1f", "#90f090"
            elif g <= 10:
                color, dark, light = GLD, "#8b6914", "#f0d060"
            elif g <= 15:
                color, dark, light = ORG, "#7a4a10", "#f0b040"
            elif g <= 20:
                color, dark, light = "#ff6644", "#8b2210", "#ffaa88"
            else:
                color, dark, light = RED, "#8b1111", "#ff7070"
            # 圆柱主体
            cvs.create_rectangle(x0, top_y + ry, x1, base_y, fill=color, outline="", width=0)
            # 圆柱暗面（右侧阴影）
            cvs.create_rectangle(x0 + bar_w * 0.65, top_y + ry, x1, base_y, fill=dark, outline="", width=0, stipple="gray50")
            # 圆柱顶面椭圆
            cvs.create_oval(x0, top_y, x1, top_y + ry * 2, fill=light, outline=color, width=1)
            # 底部椭圆
            cvs.create_oval(x0, base_y - ry, x1, base_y + ry, fill=dark, outline=color, width=1)
            # 期数标签（柱顶上方）
            if g == 0:
                label = "已开特码"
            elif g == 1:
                label = "1期未开"
            else:
                label = str(g) + "期未开"
            cvs.create_text(x0 + bar_w // 2, top_y - 16, text=label, fill=light, font=("Segoe UI", 9, "bold"))
            # 生肖标签（底部）
            cvs.create_text(x0 + bar_w // 2, base_y + 18, text=z, fill=TXT, font=("Segoe UI", 12, "bold"))
            # 最新期已开标记
            if z == latest_zodiac:
                cvs.create_text(x0 + bar_w // 2, top_y - 32, text="▼ 最新", fill=GRN, font=("Segoe UI", 8, "bold"))
        # 标题
        cvs.create_text(w // 2, 14, text="特码生肖未开期数统计 · 近180期 · 圆柱表", fill=SUB, font=("Segoe UI", 10))


    # ===== 手动录入功能 =====
    def _manual_entry(self):
        """手动录入开奖数据 - 支持单期/多期"""
        from datetime import datetime, timedelta
        
        latest_expect = 0
        latest_date = ""
        if self.data:
            lt = self.data[-1]
            latest_expect = int(lt.get("expect", 0))
            latest_date = (lt.get("openTime", "") or "")[:10]

        today = datetime.now().strftime("%Y-%m-%d")
        
        missing_count = 1
        if latest_date:
            try:
                d1 = datetime.strptime(latest_date, "%Y-%m-%d")
                d2 = datetime.strptime(today, "%Y-%m-%d")
                gap_days = (d2 - d1).days
                missing_count = max(1, min(gap_days, 30))
            except:
                missing_count = 1

        missing_dates = []
        if latest_date and missing_count > 1:
            try:
                base_d = datetime.strptime(latest_date, "%Y-%m-%d")
                for i in range(1, missing_count + 1):
                    d = base_d + timedelta(days=i)
                    if d <= datetime.strptime(today, "%Y-%m-%d"):
                        missing_dates.append(d.strftime("%Y-%m-%d"))
            except:
                missing_dates = [today]
        else:
            missing_dates = [today]

        top = tk.Toplevel(self.root)
        top.title("手动录入开奖数据")
        top.configure(bg=BG)
        rows = len(missing_dates)
        win_h = min(180 + rows * 62, 700)
        top.geometry("580x" + str(win_h))
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 580) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - win_h) // 2
        top.geometry("+%d+%d" % (max(0, x), max(0, y)))

        f = tk.Frame(top, bg=BG)
        f.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        tk.Label(f, text="手动录入开奖数据", font=("Segoe UI", 14, "bold"), fg=GLD, bg=BG).pack(anchor="w")
        info = "最新: 第%d期 (%s)  |  今日: %s  |  需录入: %d期" % (latest_expect, latest_date, today, len(missing_dates))
        tk.Label(f, text=info, fg=SUB, bg=BG, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        canvas = tk.Canvas(f, bg=BG, highlightthickness=0, height=min(rows * 62, 420))
        scrollbar = tk.Scrollbar(f, orient="vertical", command=canvas.yview)
        entry_frame = tk.Frame(canvas, bg=BG)
        entry_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=entry_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        entries = []
        for idx, date_str in enumerate(missing_dates):
            bg_color = CARD if idx % 2 == 0 else BG
            bdr_color = BDR if idx % 2 == 0 else BG
            row_frame = tk.Frame(entry_frame, bg=bg_color, highlightbackground=bdr_color, highlightthickness=1)
            row_frame.pack(fill=tk.X, pady=1, ipady=2)

            exp_num = latest_expect + idx + 1
            tk.Label(row_frame, text="第" + str(exp_num) + "期", fg=GLD, bg=bg_color, font=("Segoe UI", 9, "bold"), width=8).pack(side=tk.LEFT, padx=4)

            date_var = tk.StringVar(value=date_str)
            tk.Entry(row_frame, textvariable=date_var, bg=CARD, fg=TXT, font=("Segoe UI", 8), width=11, relief="flat").pack(side=tk.LEFT, padx=2)

            code_var = tk.StringVar(value="")
            tk.Entry(row_frame, textvariable=code_var, bg=CARD, fg=TXT, font=("Segoe UI", 10), width=30, relief="flat").pack(side=tk.LEFT, padx=4)

            tk.Label(row_frame, text="6平特+1正特", fg=SUB, bg=bg_color, font=("Segoe UI", 7)).pack(side=tk.LEFT)

            entries.append({"expect": exp_num, "date": date_var, "codes": code_var})

        error_var = tk.StringVar(value="")
        tk.Label(f, textvariable=error_var, fg=RED, bg=BG, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        btn_frame = tk.Frame(f, bg=BG)
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="取消", command=top.destroy, bg=BDR, fg=SUB, font=("Segoe UI", 10),
                 relief="flat", padx=20, pady=4, cursor="hand2").pack(side=tk.LEFT)

        def save_all():
            saved = 0
            for entry in entries:
                codes_str = entry["codes"].get().strip()
                if not codes_str:
                    continue
                parts = [p.strip() for p in codes_str.replace("，", ",").split(",") if p.strip()]
                if len(parts) != 7:
                    continue
                try:
                    nums = [int(p) for p in parts]
                    if not all(1 <= n <= 49 for n in nums):
                        continue
                except ValueError:
                    continue

                expect_num = entry["expect"]
                date_str = entry["date"].get().strip()
                codes_fmt = ",".join("%02d" % n for n in nums)
                new_record = {
                    "expect": str(expect_num),
                    "openCode": codes_fmt,
                    "openTime": date_str + " 21:30:00"
                }
                existing = load_data() if os.path.exists(DATA_FILE) else []
                existing = [d for d in existing if d.get("expect") != str(expect_num)]
                existing.append(new_record)
                all_data = sorted(existing, key=lambda x: int(x.get("expect", 0)))
                save_data(all_data)
                saved += 1

            if saved > 0:
                self.data = sorted(load_data(), key=lambda x: int(x.get("expect", 0)))
                self.analyzer = LotteryAnalyzer(self.data)
                self.ensemble = EnsemblePredictor(self.analyzer)
                self._ready()
                top.destroy()
                messagebox.showinfo("录入成功", "已录入 %d 期数据" % saved)
            else:
                error_var.set("请至少填写一期完整数据（7个号码以逗号分隔）")

        tk.Button(btn_frame, text="确认录入", command=save_all, bg=GRN, fg="#000",
                 font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=4, cursor="hand2").pack(side=tk.RIGHT)

    def _zodiac_year_config_dialog(self):
        """生肖年份配置弹窗"""
        top = tk.Toplevel(self.root)
        top.title("生肖年份配置")
        top.configure(bg=BG)
        top.geometry("520x420")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()

        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 520) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 420) // 2
        top.geometry("+{}+{}".format(max(0, x), max(0, y)))

        f = tk.Frame(top, bg=BG)
        f.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(f, text="生肖年份配置", font=("Segoe UI", 16, "bold"), fg=GLD, bg=BG).pack(anchor="w")
        tk.Label(f, text="每年农历新年后生肖对应的起始数字会轮转\n当前默认使用最新年份的映射", fg=SUB, bg=BG, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 12))

        cfg = _load_zodiac_year_config()
        cfg_frame = tk.Frame(f, bg=CARD, highlightbackground=BDR, highlightthickness=1)
        cfg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        header = tk.Frame(cfg_frame, bg=CARD)
        header.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(header, text="年份", fg=GLD, bg=CARD, font=("Segoe UI", 10, "bold"), width=8).pack(side=tk.LEFT)
        tk.Label(header, text="起始生肖（1号对应）", fg=GLD, bg=CARD, font=("Segoe UI", 10, "bold"), width=20).pack(side=tk.LEFT)

        entries = {}
        sorted_years = sorted(cfg.keys(), reverse=True)
        for year in sorted_years:
            row = tk.Frame(cfg_frame, bg=CARD)
            row.pack(fill=tk.X, padx=12, pady=2)
            tk.Label(row, text=str(year), fg=TXT, bg=CARD, font=("Segoe UI", 10), width=8).pack(side=tk.LEFT)
            var = tk.StringVar(value=cfg[year])
            cb = ttk.Combobox(row, textvariable=var, values=ZODIAC_MAP, state="readonly", width=16)
            cb.pack(side=tk.LEFT)
            entries[year] = var

        def save_config():
            new_cfg = {}
            for year, var in entries.items():
                new_cfg[year] = var.get()
            with open(ZODIAC_YEAR_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_cfg, f, ensure_ascii=False, indent=2)
            global _DEFAULT_ZODIAC_MAP
            _DEFAULT_ZODIAC_MAP = _get_zodiac_mapping()
            messagebox.showinfo("保存成功", "生肖年份配置已更新，下次启动生效")
            top.destroy()

        add_frame = tk.Frame(f, bg=BG)
        add_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(add_frame, text="添加新年份:", fg=TXT, bg=BG, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        new_year_var = tk.StringVar(value=str(int(sorted_years[0]) + 1) if sorted_years else "2027")
        tk.Entry(add_frame, textvariable=new_year_var, bg=CARD, fg=TXT, font=("Segoe UI", 9), width=6, relief="flat", insertbackground=TXT).pack(side=tk.LEFT, padx=(0, 8))
        new_zodiac_var = tk.StringVar(value="鼠")
        ttk.Combobox(add_frame, textvariable=new_zodiac_var, values=ZODIAC_MAP, state="readonly", width=8).pack(side=tk.LEFT, padx=(0, 8))

        def add_year():
            y = new_year_var.get().strip()
            if not y.isdigit():
                return
            # 添加新行到显示
            row = tk.Frame(cfg_frame, bg=CARD)
            row.pack(fill=tk.X, padx=12, pady=2, before=cfg_frame.winfo_children()[1])
            tk.Label(row, text=y, fg=TXT, bg=CARD, font=("Segoe UI", 10), width=8).pack(side=tk.LEFT)
            var = tk.StringVar(value=new_zodiac_var.get())
            cb = ttk.Combobox(row, textvariable=var, values=ZODIAC_MAP, state="readonly", width=16)
            cb.pack(side=tk.LEFT)
            entries[y] = var

        tk.Button(add_frame, text="添加", command=add_year, bg=ACC, fg="#fff", font=("Segoe UI", 9),
                 relief="flat", padx=12, pady=2, cursor="hand2").pack(side=tk.LEFT)

        btn_frame = tk.Frame(f, bg=BG)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="取消", command=top.destroy, bg=BDR, fg=SUB, font=("Segoe UI", 10),
                 relief="flat", padx=20, pady=4, cursor="hand2").pack(side=tk.LEFT)
        tk.Button(btn_frame, text="保存配置", command=save_config, bg=GRN, fg="#000",
                 font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=4, cursor="hand2").pack(side=tk.RIGHT)



    def _init_data_mgr(self):
        m = tk.Frame(self.ff, bg=BG)
        m.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        ctrl = tk.Frame(m, bg=BG)
        ctrl.pack(fill=tk.X, pady=(0,12))
        tk.Label(ctrl, text="数据 API", font=("Segoe UI",16,"bold"), fg=GLD, bg=BG).pack(side=tk.LEFT)
        self.dm_status = tk.Label(ctrl, text="就绪", fg=SUB, bg=BG, font=("Segoe UI",9))
        self.dm_status.pack(side=tk.RIGHT)
        yr_row = tk.Frame(m, bg=BG)
        yr_row.pack(fill=tk.X, pady=(0,8))
        tk.Label(yr_row, text="数据年份:", fg=TXT, bg=BG, font=("Segoe UI",10)).pack(side=tk.LEFT, padx=(0,8))
        self.dm_year = tk.StringVar(value="2024,2025,2026")
        tk.Entry(yr_row, textvariable=self.dm_year, bg=CARD, fg=TXT, font=("Segoe UI",10), width=20, relief="flat").pack(side=tk.LEFT)
        btn_row = tk.Frame(m, bg=BG)
        btn_row.pack(fill=tk.X, pady=(0,12))
        tk.Button(btn_row, text="更新数据", command=self._dm_fetch, bg=GRN, fg="#000",
                 font=("Segoe UI",10,"bold"), relief="flat", padx=16, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0,8))
        tk.Button(btn_row, text="查看已缓存", command=self._dm_show_cached, bg=ACC, fg="#fff",
                 font=("Segoe UI",10,"bold"), relief="flat", padx=16, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0,8))
        tk.Button(btn_row, text="清空", command=self._dm_clear, bg=BDR, fg=SUB,
                 font=("Segoe UI",9), relief="flat", padx=12, pady=4, cursor="hand2").pack(side=tk.RIGHT)
        c1, i1 = self._card(m, "API 日志", "macaujc.com 直连接口，无需第三方服务", GRN)
        c1.pack(fill=tk.BOTH, expand=True)
        self.dm_text = tk.Text(i1, bg=BG, fg=TXT, font=("Consolas",9), relief="flat", padx=8, pady=4, wrap=tk.WORD)
        sb = tk.Scrollbar(i1, command=self.dm_text.yview)
        self.dm_text.configure(yscrollcommand=sb.set)
        self.dm_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _dm_fetch(self):
        self.dm_status.config(text="获取中...", fg=GLD)
        self.dm_text.delete(1.0, tk.END)
        self.dm_text.insert(tk.END, "正在从 macaujc.com API 获取数据...\n")
        self.root.update()
        def run():
            try:
                years_str = self.dm_year.get().strip()
                years = [int(y.strip()) for y in years_str.split(",") if y.strip()]
                nd = macaujc_api.fetch_all(years)
                msgs = [f"获取完成，共 {len(nd)} 条记录"]
                if os.path.exists(DATA_FILE):
                    old = load_data()
                    ex = {d["expect"] for d in old}
                    ad = [d for d in nd if d.get("expect") not in ex]
                    msgs.append(f"新增: {len(ad)} 条")
                    all_d = sorted(old + ad, key=lambda x: int(x.get("expect",0)))
                    save_data(all_d)
                    msgs.append(f"总计: {len(all_d)} 条")
                else:
                    save_data(nd)
                    msgs.append(f"已保存 {len(nd)} 条")
                self.root.after(0, lambda: self._dm_show("\n".join(msgs), GRN))
            except Exception as e:
                self.root.after(0, lambda: self._dm_show(f"获取失败: {e}", RED))
        threading.Thread(target=run, daemon=True).start()

    def _dm_show_cached(self):
        self.dm_text.delete(1.0, tk.END)
        if os.path.exists(DATA_FILE):
            data = load_data()
            self.dm_text.insert(tk.END, f"已缓存记录: {len(data)} 条\n")
            self.dm_text.insert(tk.END, f"文件: {DATA_FILE}\n\n")
            if data:
                first = data[0]; last = data[-1]
                self.dm_text.insert(tk.END, f"第一期: {first['expect']} ({first['openTime']})\n")
                self.dm_text.insert(tk.END, f"最新期: {last['expect']} ({last['openTime']})\n")
            self.dm_status.config(text=f"{len(data)} 条", fg=GRN)
        else:
            self.dm_text.insert(tk.END, "未找到缓存文件，请先点击更新数据")
            self.dm_status.config(text="无数据", fg=RED)

    def _dm_show(self, text, color=GRN):
        self.dm_text.delete(1.0, tk.END)
        self.dm_text.insert(tk.END, text)
        self.dm_status.config(text="完成" if color == GRN else "失败", fg=color)

    def _dm_clear(self):
        self.dm_text.delete(1.0, tk.END)
        self.dm_status.config(text="就绪", fg=SUB)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
