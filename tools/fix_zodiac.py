"""Fix zodiac year bugs in main.py"""
import re, sys

filepath = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

fixes = 0

# Fix 1: Replace EightLinePredictor old predict_specials with V4
start_marker = '    # ==== 综合预测: 8线强制多样性 ===='
end_marker = '    # ==== 沙盘回测每一条线 ===='

new_predict = '''    # ==== 综合预测: 8线强制多样性 (V4) ====
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
        return picks[:count]'''

start = content.find(start_marker)
end = content.find(end_marker)
if start > 0 and end > start:
    content = content[:start] + new_predict + '\n\n' + content[end:]
    fixes += 1
    print("FIX 1: EightLinePredictor.predict_specials -> V4")
else:
    print(f"WARNING: markers not found start={start} end={end}")

# Fix 2: line5_zodiac_rotator
old_l5 = '        zodiac_nums = [n for n in range(1,50) if num_to_zodiac(n) == rarest_z]'
if old_l5 in content:
    new_l5 = '        ld = self.a.data[-1].get("openTime","") if self.a.data else ""; zodiac_nums = [n for n in range(1,50) if num_to_zodiac(n, ld) == rarest_z]'
    content = content.replace(old_l5, new_l5)
    fixes += 1
    print("FIX 2: line5_zodiac_rotator")

# Write
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Total fixes: {fixes}")

# Verify
compile(content, filepath, 'exec')
print("Syntax OK")