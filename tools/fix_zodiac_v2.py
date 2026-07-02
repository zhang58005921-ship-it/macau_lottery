"""Fix zodiac direction + full audit"""
import re

filepath = r"C:\Users\PENGYI\Documents\学习codex\macau_lottery\main.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

fixes = 0

# CRITICAL FIX: Reverse zodiac cycle direction
# OLD: ZODIAC_MAP[(zi + (n - 1)) % 12]
# NEW: ZODIAC_MAP[(zi - (n - 1)) % 12]  (Macau lottery uses reverse cycle)

old_formula = "ZODIAC_MAP[(zi + (n - 1)) % 12]"
new_formula = "ZODIAC_MAP[(zi - (n - 1)) % 12]"
count = content.count(old_formula)
if count > 0:
    content = content.replace(old_formula, new_formula)
    fixes += 1
    print(f"FIX 1: Reversed zodiac cycle direction ({count} occurrences) -> ZODIAC_MAP[(zi - (n-1)) % 12]")

# Also fix the flattened version (in num_to_zodiac, line 57 area)
# The function body might use the formula inline
# Check and fix the actual implementation
old2 = "(zi + (n - 1)) % 12"
new2 = "(zi - (n - 1)) % 12"
count2 = content.count(old2)
if count2 > 0:
    content = content.replace(old2, new2)
    fixes += 1
    print(f"FIX 2: Inline formula fix ({count2} occurrences)")

# Fix the docstring/comment
old_doc = "# 默认使用2026马年映射"
new_doc = "# 默认使用2026马年映射 (逆序: 马蛇龍兔虎牛鼠豬狗雞猴羊)"

# Update the _LUNAR_NEW_YEAR comment to note the reverse cycle
old_comment = "    \"2026-02-17\": \"馬\","
new_comment = "    \"2026-02-17\": \"馬\",  # 注意: 澳门彩生肖为逆序循环"
content = content.replace(old_comment, new_comment)

# Write
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nTotal fixes: {fixes}")

# Verify syntax
try:
    compile(content, filepath, 'exec')
    print("Syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")

# Quick validation: test num_to_zodiac
print("\n=== Quick Validation ===")
exec(compile(content, filepath, 'exec'), globals_dict := {})
# Test the function
result_12 = globals_dict.get('num_to_zodiac', lambda n,d: '?')(12, '2026-07-01')
print(f"num_to_zodiac(12, '2026-07-01') = {result_12}")
expected = "羊"
print(f"Expected: {expected} -> {'PASS' if result_12 == expected else 'FAIL'}")

# Test a few more
tests = [(1, '2026-07-01', '馬'), (7, '2026-07-01', '鼠'), (13, '2026-07-01', '馬'),
         (1, '2024-07-01', '龍'), (12, '2024-07-01', '兔')]
for n, d, exp in tests:
    res = globals_dict.get('num_to_zodiac', lambda n,d: '?')(n, d)
    status = "PASS" if res == exp else "FAIL"
    print(f"  num_to_zodiac({n}, '{d[:10]}') = {res} (expected {exp}) {status}")