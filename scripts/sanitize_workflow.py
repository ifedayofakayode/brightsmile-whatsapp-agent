#!/usr/bin/env python3
"""Make an n8n workflow export safe to publish.

Usage:  python sanitize_workflow.py my_export.json workflows/main-assistant.json

What it does
  - deletes pinned test data (it contains real phone numbers and names)
  - removes credential references, webhook IDs, instance ID and workflow IDs
  - replaces Google Sheet, Calendar, Slack and Wassenger identifiers with placeholders
  - masks anything that looks like a Nigerian phone number
  - then scans the result and WARNS about anything that still looks like a secret
Always read the output file yourself before you commit it.
"""
import json, re, sys

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, dst = sys.argv[1], sys.argv[2]
wf = json.load(open(src, encoding="utf-8"))

# 1) top-level clean-up
wf.pop("pinData", None)
for k in ("id", "versionId", "shared"):
    wf.pop(k, None)
wf.get("meta", {}).pop("instanceId", None)
wf["active"] = False

# 2) per-node clean-up
def walk(o):
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if k == "documentId" and isinstance(v, dict):
                v["value"] = "YOUR_GOOGLE_SHEET_ID"; v.pop("cachedResultUrl", None)
            elif k == "sheetName" and isinstance(v, dict):
                v.pop("cachedResultUrl", None)
            elif k == "calendar" and isinstance(v, dict) and "value" in v:
                v["value"] = "YOUR_CALENDAR_ID"
            elif k == "channelId" and isinstance(v, dict):
                v["value"] = "YOUR_SLACK_CHANNEL_ID"
            elif k == "device" and isinstance(v, str):
                o[k] = "YOUR_WASSENGER_DEVICE_ID"
            else:
                walk(v)
    elif isinstance(o, list):
        for i in o:
            walk(i)

for node in wf.get("nodes", []):
    node.pop("credentials", None)
    node.pop("webhookId", None)
walk(wf.get("nodes", []))

# 3) mask phone numbers anywhere in the text
text = json.dumps(wf, indent=2, ensure_ascii=False)
text = re.sub(r"\+?234\d{10}", "+234XXXXXXXXXX", text)

# 4) scan for anything that still looks sensitive
patterns = {
    "OpenAI-style key": r"sk-[A-Za-z0-9_-]{20,}",
    "Slack token": r"xox[abprs]-[A-Za-z0-9-]{10,}",
    "Bearer token": r"Bearer\s+[A-Za-z0-9._-]{20,}",
    "Google API key": r"AIza[0-9A-Za-z_-]{20,}",
    "Long hex id": r"\b[0-9a-f]{24,}\b",
    "Email address": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}",
    "Google Docs link": r"docs\.google\.com/[^\s\"']+",
}
found = False
for label, pat in patterns.items():
    hits = sorted(set(re.findall(pat, text)))
    if hits:
        found = True
        print(f"WARNING {label}: {hits[:5]}")
open(dst, "w", encoding="utf-8").write(text)
print("Saved", dst, "-", "review the warnings above" if found else "no warnings")