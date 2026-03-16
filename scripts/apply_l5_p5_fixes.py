"""Apply L5 fifth-pass audit fixes (JSON format) to words.xlsx."""
import json, glob, os, openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, 'words.xlsx')
FIX_DIR = os.path.join(ROOT, 'data', 'level_data')

wb = openpyxl.load_workbook(XLSX)
ws = wb.active
header = [cell.value for cell in ws[1]]
col = {name: idx for idx, name in enumerate(header)}

fix_files = sorted(glob.glob(os.path.join(FIX_DIR, 'L5_chunk*_p5_fixes.json')))
print(f"Found {len(fix_files)} fix files")

all_fixes = []
removals = []

for path in fix_files:
    with open(path) as f:
        fixes = json.load(f)
    for fix in fixes:
        if fix.get('field') == 'REMOVE':
            removals.append(fix)
        else:
            all_fixes.append(fix)

print(f"Edits: {len(all_fixes)}, Removals: {len(removals)}")

applied = 0
skipped = 0

for fix in all_fixes:
    row_num = fix['row']
    field = fix['field']
    old_val = fix.get('old', '')
    new_val = fix['new']

    if field not in col:
        print(f"  SKIP row {row_num}: unknown field '{field}'")
        skipped += 1
        continue

    c = col[field] + 1  # openpyxl is 1-indexed
    cell = ws.cell(row=row_num, column=c)
    actual = cell.value
    # Normalize None to empty string for comparison
    if actual is None:
        actual = ''
    if old_val is None:
        old_val = ''

    if actual != old_val:
        print(f"  SKIP row {row_num} field '{field}': expected {repr(old_val)}, got {repr(actual)}")
        skipped += 1
        continue

    cell.value = new_val if new_val != '' else None
    applied += 1

print(f"\nApplied {applied} edits, skipped {skipped}")

# Apply removals in reverse order to preserve row numbers
if removals:
    removal_rows = sorted({r['row'] for r in removals}, reverse=True)
    print(f"Removing {len(removal_rows)} rows: {removal_rows}")
    for row_num in removal_rows:
        ws.delete_rows(row_num)
    print(f"Removed {len(removal_rows)} rows")

wb.save(XLSX)
print("Saved.")
