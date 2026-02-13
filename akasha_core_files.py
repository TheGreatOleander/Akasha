# gate.py
import sys
from mirror import reflect
from archive import append

LAW = {"open_the_gate", "acknowledge", "commit", "record_thought", 
       "create_artifact", "update_context", "query_records", 
       "resume_thread", "branch_reality", "merge_timelines"}

def invoke(intent):
    mirrored = reflect(intent)
    if mirrored["normalized"] not in LAW:
        raise PermissionError("Gate denied")
    return append(mirrored)

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "invoke":
        print("usage: gate.py invoke <intent>")
        exit(1)
    h = invoke(sys.argv[2])
    print("Recorded:", h)


# ============================================

# mirror.py
def reflect(intent: str) -> dict:
    intent = intent.strip().lower()
    if not intent:
        raise ValueError("Empty intent")
    return {
        "intent": intent,
        "normalized": intent.replace(" ", "_")
    }


# ============================================

# archive.py
import json, time, hashlib, os

LOG = "akasha.log"

def append(record):
    record["time"] = time.time()
    blob = json.dumps(record, sort_keys=True)
    record["hash"] = hashlib.sha256(blob.encode()).hexdigest()
    with open(LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record["hash"]

def recall():
    if not os.path.exists(LOG):
        return []
    return [json.loads(l) for l in open(LOG)]
