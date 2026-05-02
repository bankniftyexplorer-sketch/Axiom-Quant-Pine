import csv
import re
import sys

filename = "/home/km/PineWorkspace/pinescript-dev/log csv/pine-logs-Institutional Delta Architecture (IDA)_nifty.csv"
pattern = r"Idx:(\d+)\|Spot:([0-9.]+)\|ATR:(.+?)\|Score:(.+?)\|ATM:(\d+)\|CE4:(.+?)\|PE4:(.+?)\|CDom:(.+?)\|CWt:(.+?)\|CVel:(.+?)\|PVel:(.+?)\|U1D:(.+?)\|D1D:(.+?)"

valid_rows = []
with open(filename, 'r') as f:
    reader = csv.reader(f)
    next(reader) # skip header
    for row in reader:
        if len(row) < 2: continue
        msg = row[1]
        m = re.search(pattern, msg)
        if m:
            d = m.groups()
            try:
                score = float(d[3])
                cdom = float(d[7])
                valid_rows.append((score, cdom))
            except ValueError:
                pass

if not valid_rows:
    print("No valid numeric rows found.")
    sys.exit()

scores = [r[0] for r in valid_rows]
cdoms = [r[1] for r in valid_rows]

print(f"Total Valid Bars Analysed: {len(valid_rows)}")
print(f"ComparatorScore -> Min: {min(scores):.4f}, Max: {max(scores):.4f}, Mean: {sum(scores)/len(scores):.4f}")
print(f"CDom (Raw Dominance) -> Min: {min(cdoms):.4f}, Max: {max(cdoms):.4f}, Mean: {sum(cdoms)/len(cdoms):.4f}")

zeros = sum(1 for s in scores if abs(s) < 0.0001)
print(f"Score is near zero for {zeros} bars ({zeros/len(scores)*100:.1f}%)")
