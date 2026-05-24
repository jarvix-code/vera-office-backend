#!/usr/bin/env python3
# Fix emoji encoding for Windows

import sys

content = open('vera_qm_template_parser.py', 'r', encoding='utf-8').read()

# Remove all emojis
content = content.replace('⚠️', 'WARN')
content = content.replace('🧠', '')
content = content.replace('✅', 'OK')
content = content.replace('❌', 'ERR')
content = content.replace('📁', '')
content = content.replace('📊', '')
content = content.replace('📄', '')
content = content.replace('📂', '')
content = content.replace('ℹ️', '--')

# Fix batch_process_pdfs to respect limit parameter
old_code = '''def batch_process_pdfs(pdf_folder: Path, max_workers: int = 4) -> List[Dict]:
    """
    Process all PDFs in parallel
    """
    
    # Get all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if limit:
        pdf_files = pdf_files[:limit]
        print(f"TEST MODE: Processing first {len(pdf_files)} PDFs (out of {len(list(pdf_folder.glob('*.pdf')))} total)")
    else:
        print(f"Found {len(pdf_files)} PDFs")'''

new_code = '''def batch_process_pdfs(pdf_folder: Path, max_workers: int = 4, limit: int = None) -> List[Dict]:
    """
    Process all PDFs in parallel
    """
    
    # Get all PDF files
    pdf_files = list(pdf_folder.glob("*.pdf"))
    
    if limit:
        pdf_files = pdf_files[:limit]
        print(f"TEST MODE: Processing first {len(pdf_files)} PDFs")
    else:
        print(f"Found {len(pdf_files)} PDFs")'''

content = content.replace(old_code, new_code)

# Fix main() to pass limit
old_main = '''    # 2. Process PDFs
    print(f"\\nProcessing PDFs from: {PDF_FOLDER}")
    
    test_limit = TEST_LIMIT if TEST_MODE else None
    results = batch_process_pdfs(PDF_FOLDER, max_workers=MAX_WORKERS, limit=test_limit)'''

new_main = '''    # 2. Process PDFs
    print(f"\\nProcessing PDFs from: {PDF_FOLDER}")
    
    test_limit = TEST_LIMIT if TEST_MODE else None
    results = batch_process_pdfs(PDF_FOLDER, max_workers=MAX_WORKERS, limit=test_limit)'''

if old_main not in content:
    # Alternative: simple version
    content = content.replace(
        'results = batch_process_pdfs(PDF_FOLDER, max_workers=MAX_WORKERS)',
        'test_limit = TEST_LIMIT if TEST_MODE else None; results = batch_process_pdfs(PDF_FOLDER, max_workers=MAX_WORKERS, limit=test_limit)'
    )

open('vera_qm_template_parser.py', 'w', encoding='utf-8').write(content)
print('File fixed!')
