path = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Find predict-related display code
idx = c.find("def _up_predict")
idx2 = c.find("def _init_stats")
print(c[idx:idx2][:3000])
