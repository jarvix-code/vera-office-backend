import yaml

with open('backend/data/folder_templates/base.yaml', 'r', encoding='utf-8') as f:
    base = yaml.safe_load(f)
with open('backend/data/folder_templates/arztpraxis.yaml', 'r', encoding='utf-8') as f:
    branch = yaml.safe_load(f)

count = 0
def count_folders(folders, depth=0):
    global count
    for f in folders:
        count += 1
        name = f.get('display_name', f.get('name', ''))
        yearly = f.get('yearly', False)
        monthly = f.get('monthly', False)
        quarterly = f.get('quarterly', False)
        extra = 0
        if yearly:
            extra += 1  # year folder
        if monthly:
            extra += 12  # month folders
        if quarterly:
            extra += 4
        if extra:
            count += extra
            print(f"{'  '*depth}{f['id']} {name} (+{extra} Zeit-Ordner)")
        else:
            print(f"{'  '*depth}{f['id']} {name}")
        if f.get('children'):
            count_folders(f['children'], depth+1)

print("=== BASIS ===")
count_folders(base.get('folders', []))
base_count = count
print(f"\nBasis-Ordner: {base_count}")

print("\n=== ZAHNARZTPRAXIS ===")
count_folders(branch.get('folders', []))
total = count
branch_count = total - base_count
print(f"\nBranche: {branch_count}")
print(f"GESAMT: {total}")
