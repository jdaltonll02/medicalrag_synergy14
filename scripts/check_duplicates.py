import sys
import json
from collections import Counter

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <input_jsonl>")
    sys.exit(1)

input_path = sys.argv[1]

pmid_counter = Counter()
with open(input_path, 'r') as f:
    for line in f:
        try:
            doc = json.loads(line)
            pmid = doc.get('pmid')
            if pmid:
                pmid_counter[pmid] += 1
        except Exception as e:
            print(f"Error parsing line: {e}")

duplicates = [pmid for pmid, count in pmid_counter.items() if count > 1]
print(f"Total documents: {sum(pmid_counter.values())}")
print(f"Unique PMIDs: {len(pmid_counter)}")
print(f"Duplicate PMIDs: {len(duplicates)}")
if duplicates:
    print("Sample duplicate PMIDs:")
    for pmid in duplicates[:10]:
        print(f"  {pmid}: {pmid_counter[pmid]} times")
