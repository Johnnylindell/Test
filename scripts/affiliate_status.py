#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
links = json.loads((ROOT / 'data' / 'affiliate_links.json').read_text(encoding='utf-8'))
missing = [(k, v) for k, v in links.items() if v.get('status') != 'active' or not v.get('url')]
print('# Affiliate-status')
print()
if not missing:
    print('Alla affiliate-länkar är aktiva. Bygg om sajten och kontrollera disclosure.')
else:
    print(f'Saknar {len(missing)} länkar/kategorier:')
    for key, item in missing:
        print(f'- {key}: {item.get("needed_link", "länk saknas")}')
        for page in item.get('target_pages', []):
            print(f'  - {page}')
    print()
    print('Nästa steg: skapa affiliatekonto och lägg in riktiga tracking-länkar i data/affiliate_links.json. Använd inte placeholder-länkar publikt.')
