import json, random

rows = [json.loads(l) for l in open("chunks.jsonl", encoding="utf-8")]
for r in random.sample(rows, 5):
    print(f"=== {r['id']}  (source={r['source']}, tokens={r['token_count']}) ===")
    print(r["text"])
    print()
