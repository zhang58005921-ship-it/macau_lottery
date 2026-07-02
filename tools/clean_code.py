"""Clean up main.py: remove unused code, fix docstrings, optimize framework"""
import re

filepath = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

fixes = 0

# 1. Update AdversarialPredictor __init__: remove Markov/MonteCarlo/EMA (noise)
old_init = '''    def __init__(self, a):
        self.a = a
        self.markov = MarkovChainModel(a)
        self.monte = MonteCarloModel(a)
        self.ema = WeightedEMAModel(a)
        self._kill_streak = 0
        self._raise_streak = 0'''

new_init = '''    def __init__(self, a):
        self.a = a
        self._kill_streak = 0
        self._raise_streak = 0'''

if old_init in content:
    content = content.replace(old_init, new_init)
    fixes += 1
    print("CLEAN 1: Removed Markov/MonteCarlo/EMA from AdversarialPredictor.__init__")

# 2. Remove unused signal methods from AdversarialPredictor
# _signal_markov, _signal_montecarlo, _signal_ema, _signal_cold_hot, _crowd_heatmap (old)
# These are no longer called by predict_specials V4
# Keep them for backward compatibility but mark as deprecated
old_deprecated = '''    # ==== 量化信号源 ====
    def _signal_markov(self):'''
new_deprecated = '''    # ==== 量化信号源 (已弃用, V4不再使用Markov/MonteCarlo/EMA噪声) ====
    def _signal_markov(self):'''
if old_deprecated in content:
    content = content.replace(old_deprecated, new_deprecated)
    fixes += 1
    print("CLEAN 2: Marked old signal methods as deprecated")

# 3. Update class docstring
old_doc = '''class AdversarialPredictor:
    """庄家思维引擎 — 博弈论+赌博心理学=唯一决策者
    
    量化模型全部降级为信号源(情报输入), 庄家利润函数筛选。
    
    信号源:
    - MarkovChainModel: 号码转移概率
    - MonteCarloModel: 频率采样分布  
    - WeightedEMAModel: 指数衰减频率
    - LotteryAnalyzer: 间隔/冷热/生肖共现
    - 大众行为推断: 五维热度(号码/单双/波色/生肖/大小)
    
    庄家目标: min(总赔付出) = 综合所有信号, 选最低风险号码
    """'''

new_doc = '''class AdversarialPredictor:
    """庄家思维引擎 V4 — 博弈论+赌博心理学=唯一决策者
    
    基于834期诚实回测验证的有效信号:
    - 周易五行亲和 (最强信号 +0.0334)
    - 避开近期正特号码 (-0.0180)
    - 避开热门生肖 (-0.0186)  [生肖年独立计算, 逆序循环]
    - 避开上期同生肖 (-0.0159)
    - 号码综合热度避让
    
    已弃用无效信号: Markov/MonteCarlo/EMA/冷号
    
    庄家目标: min(赔付出) = 综合验证信号, 选最低风险号码
    """'''

if old_doc in content:
    content = content.replace(old_doc, new_doc)
    fixes += 1
    print("CLEAN 3: Updated AdversarialPredictor docstring")

# 4. Add reverse cycle comment to num_to_zodiac
old_n2z = '''def num_to_zodiac(num, date_str=None):
    """号码→生肖，支持按农历年自动切换"""'''
new_n2z = '''def num_to_zodiac(num, date_str=None):
    """号码→生肖，支持按农历年自动切换
    注意: 澳门彩使用逆序生肖循环 (zi - (n-1)) % 12, 而非标准 (zi + (n-1)) % 12"""'''
if old_n2z in content:
    content = content.replace(old_n2z, new_n2z)
    fixes += 1
    print("CLEAN 4: Added reverse cycle comment")

# Write
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nTotal cleanups: {fixes}")

# Verify
try:
    compile(content, filepath, 'exec')
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")