"""
Backfill Embeddings for Existing VERA Learning Log
Generates semantic embeddings for all entries without embeddings
"""
import sys
sys.path.insert(0, '.')

from backend.core.ai.brain_v2 import BrainV2
import sqlite3
from pathlib import Path

DB_PATH = Path("data/brain.db")

def backfill_embeddings():
    """Generate embeddings for all learning_log entries"""
    
    # Init Brain v2 with VERA's learning_log
    brain = BrainV2(db_path=str(DB_PATH), table_name="learning_log")
    
    # Get all entries without embeddings
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    
    cursor = db.execute("""
        SELECT id, event_type, description, data 
        FROM learning_log 
        WHERE embedding IS NULL
        ORDER BY id
    """)
    
    entries = cursor.fetchall()
    total = len(entries)
    
    print(f"🧠 Backfilling embeddings for {total} entries...\n")
    
    if total == 0:
        print("✅ All entries already have embeddings!")
        db.close()
        return
    
    # Generate embeddings
    updated = 0
    errors = 0
    
    for i, entry in enumerate(entries, 1):
        log_id = entry['id']
        event_type = entry['event_type']
        description = entry['description']
        data = entry['data'] or ''
        
        try:
            # Combine description + data for embedding
            text = description + (' ' + data if data else '')
            
            # Generate embedding
            emb = brain.embedder.encode(text)
            
            # Update database
            db.execute("""
                UPDATE learning_log 
                SET embedding = ?, confidence = 1.0, lifecycle = 'validated'
                WHERE id = ?
            """, (emb.tobytes(), log_id))
            
            updated += 1
            
            # Progress
            if i % 10 == 0 or i == total:
                pct = (i / total) * 100
                print(f"  [{pct:5.1f}%] {i}/{total} | Last: #{log_id} ({event_type})")
        
        except Exception as e:
            errors += 1
            print(f"  ❌ Error on #{log_id}: {e}")
            continue
    
    # Commit all updates
    db.commit()
    db.close()
    
    print(f"\n✅ Backfill complete!")
    print(f"   Updated: {updated}")
    print(f"   Errors:  {errors}")
    print(f"   Total:   {total}")

if __name__ == "__main__":
    backfill_embeddings()
