import json
from collections import Counter

with open('report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

leaks = data.get('findings', [])
print(f"Total Definitive Leaks: {len(leaks)}")

sinks = Counter(f['sink']['target_signature'] for f in leaks)
print("\nTop 5 Sinks:")
for k, v in sinks.most_common(5):
    print(f"  {v} times: {k}")

cats = Counter(f"{f['source']['category']} -> {f['sink']['category']}" for f in leaks)
print("\nTop 5 Category Flows:")
for k, v in cats.most_common(5):
    print(f"  {v} times: {k}")
