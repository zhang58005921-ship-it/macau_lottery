path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Show _init_predict area
for i, line in enumerate(lines, 1):
    if 380 <= i <= 470:
        print(f"{i}: {line.rstrip()}")
