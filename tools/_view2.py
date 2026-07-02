path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(18, 30):
    print(f"{i+1}: {repr(lines[i].rstrip())}")
