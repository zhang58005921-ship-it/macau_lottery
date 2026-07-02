path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

marker = "return m.get(n, '?')"
wave_func = """
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
"""

idx = c.find(marker)
insert_pos = idx + len(marker)
c = c[:insert_pos] + wave_func + c[insert_pos:]

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(c)
print("num_to_wave inserted at position", insert_pos)
