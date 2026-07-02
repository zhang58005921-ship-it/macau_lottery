import sys; sys.path.insert(0, r"C:\Users\PENGYI\Documents\学习codex\macau_lottery")
from main import load_data, LotteryAnalyzer, EnsemblePredictor, num_to_wave, num_to_zodiac
data = load_data()
a = LotteryAnalyzer(data)
ep = EnsemblePredictor(a)
specials = ep.predict_specials(7)
print("Specials:", specials)
for n in specials:
    wave, color = num_to_wave(n)
    print(f"  {n:02d}({num_to_zodiac(n)}) -> {wave} {color}")
