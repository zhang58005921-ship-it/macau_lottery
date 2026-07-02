path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
idx = c.find("num_to_wave")
if idx < 0:
    print("num_to_wave NOT FOUND in file!")
else:
    print(c[idx:idx+200])
