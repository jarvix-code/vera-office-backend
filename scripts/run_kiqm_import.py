#!/usr/bin/env python3
"""Direct KIQM import runner."""
import sys
import os

# Change to project root (needed for relative DB paths!)
os.chdir("C:/Jarvix/vera-office")
sys.path.insert(0, "C:/Jarvix/vera-office")

from backend.modules.qm import kiqm_import

# Initialize job
kiqm_import._import_jobs = {
    'direct': {
        'status': 'importing',
        'total': 0,
        'done': 0,
        'errors': 0,
        'error_details': [],
        'current_document': None
    }
}

print("Starting KIQM import...")
kiqm_import._run_import('direct')

job = kiqm_import._import_jobs['direct']
print(f"\n✅ Import complete!")
print(f"   Total: {job['total']}")
print(f"   Done: {job['done']}")
print(f"   Errors: {job['errors']}")

if job['error_details']:
    print(f"\nFirst 5 errors:")
    for err in job['error_details'][:5]:
        print(f"  - {err}")
