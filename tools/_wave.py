path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Add wave color function after num_to_zodiac
old_func = '''    return mapping.get(n, "?")

class LotteryAnalyzer:'''
new_func = '''    return mapping.get(n, "?")

# 红蓝绿波映射
def num_to_wave(n):
    """号码转红蓝绿波"""
    red   = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
    blue  = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
    green = {5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49}
    n = int(n)
    if n in red:   return ("红波", "#ff4444")
    if n in blue:  return ("蓝波", "#4488ff")
    if n in green: return ("绿波", "#44cc44")
    return ("?", "#888")

class LotteryAnalyzer:'''
c = c.replace(old_func, new_func)
print("Added num_to_wave")

# 2. Change special numbers label to a frame in _init_predict
# Old: self.sl = tk.Label(i3, text="---", ...
old_label = '''        self.sl = tk.Label(i3, text="---", font=("Segoe UI",18,"bold"), fg=RED, bg=CARD)'''
new_label = '''        self.sl_frame = tk.Frame(i3, bg=CARD)
        self.sl_labels = []'''
c = c.replace(old_label, new_label)

old_pack = '''        self.sl.pack(anchor="w", pady=4)'''
new_pack = '''        self.sl_frame.pack(anchor="w", pady=4, fill=tk.X)'''
c = c.replace(old_pack, new_pack)
print("Changed sl to frame")

# 3. Update _up_predict to use colored labels
old_pred = '''        self.sl.config(text="  ".join("{:02d}({})".format(n, num_to_zodiac(n)) for n in s))'''
new_pred = '''        for w in self.sl_labels:
            w.destroy()
        self.sl_labels.clear()
        for n in s:
            wave_name, wave_color = num_to_wave(n)
            lbl = tk.Label(self.sl_frame, text="{:02d}({})".format(n, num_to_zodiac(n)),
                          font=("Segoe UI", 16, "bold"), fg=wave_color, bg=CARD,
                          padx=6, pady=2)
            lbl.pack(side=tk.LEFT)
            self.sl_labels.append(lbl)'''
c = c.replace(old_pred, new_pred)
print("Updated _up_predict specials display")

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(c)
print("\nAll changes applied")
