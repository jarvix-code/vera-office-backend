"""
Brain v2 Migration for VERA
Adds semantic search capabilities to existing VERA Brain
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/brain.db")

def backup_db():
    """Create timestamped backup"""
    backup = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(DB_PATH, backup)
    print(f"✅ Backup created: {backup}")
    return backup

def check_schema():
    """Show current learning_log schema"""
    db = sqlite3.connect(DB_PATH)
    cursor = db.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='learning_log'
    """)
    schema = cursor.fetchone()
    db.close()
    
    if schema:
        print("\n📋 Current learning_log schema:")
        print(schema[0])
        return True
    else:
        print("❌ No learning_log table found!")
        return False

def add_brain_v2_columns():
    """Add Brain v2 columns to learning_log"""
    db = sqlite3.connect(DB_PATH)
    
    # Add embedding column
    try:
        db.execute("ALTER TABLE learning_log ADD COLUMN embedding BLOB")
        print("✅ Added: embedding column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⏭️  embedding column exists")
        else:
            raise
    
    # Add confidence column
    try:
        db.execute("ALTER TABLE learning_log ADD COLUMN confidence REAL DEFAULT 1.0")
        print("✅ Added: confidence column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⏭️  confidence column exists")
        else:
            raise
    
    # Add lifecycle column
    try:
        db.execute("ALTER TABLE learning_log ADD COLUMN lifecycle TEXT DEFAULT 'fresh'")
        print("✅ Added: lifecycle column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("⏭️  lifecycle column exists")
        else:
            raise
    
    db.commit()
    db.close()

def create_knowledge_graph():
    """Create knowledge graph table"""
    db = sqlite3.connect(DB_PATH)
    
    db.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            predicate TEXT NOT NULL,
            object_id INTEGER NOT NULL,
            strength REAL DEFAULT 1.0,
            last_accessed TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(subject_id) REFERENCES learning_log(id),
            FOREIGN KEY(object_id) REFERENCES learning_log(id),
            UNIQUE(subject_id, predicate, object_id)
        )
    """)
    print("✅ Created: knowledge_graph table")
    
    db.execute("CREATE INDEX IF NOT EXISTS idx_kg_subject ON knowledge_graph(subject_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_kg_object ON knowledge_graph(object_id)")
    print("✅ Created: knowledge_graph indexes")
    
    db.commit()
    db.close()

def create_fts5():
    """Create FTS5 full-text search"""
    db = sqlite3.connect(DB_PATH)
    
    # Create FTS5 table
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS learning_log_fts 
        USING fts5(description, data, content='learning_log', content_rowid='id')
    """)
    print("✅ Created: learning_log_fts table")
    
    # Triggers
    try:
        db.execute("""
            CREATE TRIGGER learning_log_ai AFTER INSERT ON learning_log BEGIN
              INSERT INTO learning_log_fts(rowid, description, data) 
              VALUES (new.id, new.description, new.data);
            END
        """)
        print("✅ Created: INSERT trigger")
    except sqlite3.OperationalError:
        print("⏭️  INSERT trigger exists")
    
    try:
        db.execute("""
            CREATE TRIGGER learning_log_au AFTER UPDATE ON learning_log BEGIN
              UPDATE learning_log_fts 
              SET description=new.description, data=new.data 
              WHERE rowid=new.id;
            END
        """)
        print("✅ Created: UPDATE trigger")
    except sqlite3.OperationalError:
        print("⏭️  UPDATE trigger exists")
    
    try:
        db.execute("""
            CREATE TRIGGER learning_log_ad AFTER DELETE ON learning_log BEGIN
              DELETE FROM learning_log_fts WHERE rowid=old.id;
            END
        """)
        print("✅ Created: DELETE trigger")
    except sqlite3.OperationalError:
        print("⏭️  DELETE trigger exists")
    
    # Populate FTS5 from existing data
    db.execute("""
        INSERT OR REPLACE INTO learning_log_fts(rowid, description, data)
        SELECT id, description, data FROM learning_log
    """)
    count = db.execute("SELECT COUNT(*) FROM learning_log").fetchone()[0]
    print(f"✅ Populated FTS5: {count} entries")
    
    db.commit()
    db.close()

def verify_migration():
    """Verify all changes"""
    db = sqlite3.connect(DB_PATH)
    
    # Check columns
    cursor = db.execute("PRAGMA table_info(learning_log)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required = {'embedding', 'confidence', 'lifecycle'}
    missing = required - columns
    
    if missing:
        print(f"❌ Missing columns: {missing}")
        return False
    else:
        print(f"✅ All columns present: {required}")
    
    # Check tables
    cursor = db.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('knowledge_graph', 'learning_log_fts')
    """)
    tables = {row[0] for row in cursor.fetchall()}
    
    if len(tables) == 2:
        print(f"✅ All tables present: {tables}")
    else:
        missing = {'knowledge_graph', 'learning_log_fts'} - tables
        print(f"❌ Missing tables: {missing}")
        return False
    
    db.close()
    return True

if __name__ == "__main__":
    print("🧠 BRAIN V2 MIGRATION FOR VERA\n")
    
    # 1. Backup
    backup_db()
    
    # 2. Check schema
    if not check_schema():
        print("\n❌ ABORT: learning_log table missing!")
        exit(1)
    
    # 3. Add columns
    print("\n📝 Adding Brain v2 columns...")
    add_brain_v2_columns()
    
    # 4. Knowledge graph
    print("\n🕸️  Creating knowledge graph...")
    create_knowledge_graph()
    
    # 5. FTS5
    print("\n🔍 Creating full-text search...")
    create_fts5()
    
    # 6. Verify
    print("\n✅ Verifying migration...")
    if verify_migration():
        print("\n🎉 MIGRATION COMPLETE!")
    else:
        print("\n❌ MIGRATION FAILED!")
        exit(1)
