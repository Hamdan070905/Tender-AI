# Fix 4 — 2 steps only

## Status: UI looks good! 8 real tenders visible. 

## Remaining fixes:

### Step 1 — Run fix_all.py (removes "Base" fake tender + fills Eligibility/Risk)
```
cd D:\Tender AI\backend
copy fix_all.py .
python fix_all.py
```
Refresh browser → "No data" on Eligibility/Risk will be fixed.

### Step 2 — For CPPP live crawl + Go/No-Go when Groq rate limited
Paste ANTIGRAVITY_PROMPT.txt into Antigravity/Claude/any AI tool.
It gives you the exact fixed connectors/cppp.py and your AI router file.

## That's it. The rest is working correctly.
