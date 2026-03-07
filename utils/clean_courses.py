import pandas as pd
import re

# Load data
df = pd.read_csv(r'R:\Coding\Projects\SCRAPING\data\courses_output.csv')

print(f"Original rows: {len(df)}")
print(f"Original unique codes: {df['course_code'].nunique()}")
print(f"Original unique titles: {df['course_title'].nunique()}\n")

# ============= NORMALIZE =============
def normalize_code(code):
    if pd.isna(code):
        return None
    code = str(code).strip().upper().replace(' ', '')
    return code if code else None

def normalize_title(title):
    if pd.isna(title):
        return None
    title = str(title).strip().lower()
    title = re.sub(r'&ndash;|–|_', '-', title)
    title = re.sub(r'\s*\([^)]*(?:20\d{2}|autumn|spring|summer|winter)[^)]*\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title).strip()
    return title if title else None

def extract_year(year_str):
    if pd.isna(year_str):
        return 0
    match = re.search(r'(\d{4})', str(year_str))
    return int(match.group(1)) if match else 0

df['norm_code'] = df['course_code'].apply(normalize_code)
df['norm_title'] = df['course_title'].apply(normalize_title)
df['year_num'] = df['year'].apply(extract_year)

# ============= BUILD UNION-FIND =============
parent = {}

def find(x):
    if x not in parent:
        parent[x] = x
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]

def union(x, y):
    px, py = find(x), find(y)
    if px != py:
        parent[px] = py

# Union rows with same norm_code
print("=== Unioning by norm_code and norm_title ===")
for norm_code in df['norm_code'].dropna().unique():
    rows = df[df['norm_code'] == norm_code].index.tolist()
    for i in range(len(rows) - 1):
        union(rows[i], rows[i + 1])

# Union rows with same norm_title
for norm_title in df['norm_title'].dropna().unique():
    rows = df[df['norm_title'] == norm_title].index.tolist()
    for i in range(len(rows) - 1):
        union(rows[i], rows[i + 1])

# ============= GROUP ROWS BY ROOT =============
groups = {}
for idx in range(len(df)):
    root = find(idx)
    if root not in groups:
        groups[root] = []
    groups[root].append(idx)

print(f"Total groups: {len(groups)}\n")

# ============= FOR EACH GROUP: SELECT CANONICAL AND MAP ALL ROWS =============
print("=== Processing each group ===")

# Map: row_index -> (final_code, final_title)
row_to_canonical = {}

for group_id, row_indices in groups.items():
    rows_in_group = df.loc[row_indices]
    
    # Skip groups with no valid data
    if rows_in_group[['course_code', 'course_title']].isna().all().all():
        for idx in row_indices:
            row_to_canonical[idx] = (None, None)
        continue
    
    # Most recent code (latest year)
    valid_years = rows_in_group[rows_in_group['year_num'] > 0]
    if len(valid_years) > 0:
        latest_idx = valid_years['year_num'].idxmax()
    else:
        latest_idx = row_indices[0]
    canonical_code = df.loc[latest_idx, 'course_code']
    
    # Most popular title
    title_counts = rows_in_group['course_title'].value_counts()
    canonical_title = title_counts.index[0] if len(title_counts) > 0 else None
    
    # Map EVERY row in group to this canonical
    for idx in row_indices:
        row_to_canonical[idx] = (canonical_code, canonical_title)
    
    if len(row_indices) > 1:
        print(f"Group {group_id}: {len(row_indices)} rows -> ({canonical_code}, {canonical_title})")

print(f"\nMappings created: {len(row_to_canonical)}\n")

# ============= APPLY MAPPINGS =============
print("=== Applying mappings to all rows ===")
for row_idx, (code, title) in row_to_canonical.items():
    df.at[row_idx, 'course_code'] = code
    df.at[row_idx, 'course_title'] = title

# ============= DROP HELPER COLUMNS =============
df = df.drop(columns=['norm_code', 'norm_title', 'year_num'])

# ============= SAVE =============
output_path = r'R:\Coding\Projects\SCRAPING\data\courses_output_cleaned.csv'
df.to_csv(output_path, index=False)

print(f"✅ Saved to: {output_path}\n")

# ============= VERIFY =============
print("=== FINAL VERIFICATION ===")
final_codes = df['course_code'].nunique()
final_titles = df['course_title'].nunique()
final_pairs = len(df.groupby(['course_code', 'course_title']).size())

print(f"Total rows: {len(df)}")
print(f"Unique codes: {final_codes}")
print(f"Unique titles: {final_titles}")
print(f"Unique pairs: {final_pairs}")
print(f"Total groups: {len(groups)}")

if final_codes == final_titles == final_pairs == len(groups):
    print("\n✅ SUCCESS! All values match!")
else:
    print("\n❌ MISMATCH")
    print("\nRows with NaN:")
    print(df[df['course_code'].isna() | df['course_title'].isna()])
    print("\nChecking for hidden duplicates...")
    df_no_nan = df.dropna(subset=['course_code', 'course_title'])
    print(f"Non-NaN rows: {len(df_no_nan)}")
    print(f"Non-NaN unique codes: {df_no_nan['course_code'].nunique()}")
    print(f"Non-NaN unique titles: {df_no_nan['course_title'].nunique()}")
    print(f"Non-NaN unique pairs: {len(df_no_nan.groupby(['course_code', 'course_title']).size())}")

print(f"\nSample output:")
print(df[['course_code', 'course_title', 'year']].head(20))
