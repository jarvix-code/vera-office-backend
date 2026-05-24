import yaml

with open('backend/data/folder_templates/base.yaml', 'r', encoding='utf-8') as f:
    base = yaml.safe_load(f)
with open('backend/data/folder_templates/arztpraxis.yaml', 'r', encoding='utf-8') as f:
    branch = yaml.safe_load(f)

def print_tree(folders, indent=0):
    for f in folders:
        prefix = '  ' * indent
        ret = f.get('retention_years')
        ret_str = ' [' + str(ret) + 'J]' if ret else (' [dauerhaft]' if ret is None and indent > 0 else '')
        yearly = ' +Jahr' if f.get('yearly') else ''
        monthly = '/Monat' if f.get('monthly') else ''
        quarterly = '/Quartal' if f.get('quarterly') else ''
        per_ent = ' (pro Person)' if f.get('per_entity') else ''
        docs = f.get('doc_types', [])
        doc_str = '  -> ' + ', '.join(docs) if docs else ''
        print(prefix + f['id'] + ' ' + f.get('display_name', f['name']) + ret_str + yearly + monthly + quarterly + per_ent)
        if docs:
            print(prefix + '     ' + doc_str)
        if f.get('children'):
            print_tree(f['children'], indent + 1)

print('=== BASIS-STRUKTUR (alle KMU) ===')
print()
print_tree(base.get('folders', []))
print()
print('=== BRANCHENERWEITERUNG: ZAHNARZTPRAXIS ===')
print()
print_tree(branch.get('folders', []))
