"""
Chat Message Model
Database operations for VERA Chat history

Schema:
- chat_messages table: Stores user and assistant messages
- Indexed by user_id and timestamp for fast retrieval
"""
from datetime import datetime
from typing import List, Dict
from backend.db.database import SessionLocal
from loguru import logger


async def init_chat_db():
    """
    Initialize chat_messages table if it doesn't exist.
    Called on application startup.
    """
    from backend.db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Create chat_messages table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        
        # Create index for fast lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_chat_user_time 
            ON chat_messages(user_id, created_at DESC)
        """))
        
        conn.commit()
    
    logger.info("✅ Chat database initialized")


async def store_chat_message(
    user_id: int,
    role: str,
    content: str
) -> int:
    """
    Store a chat message (user or assistant).
    
    Args:
        user_id: User ID (from JWT)
        role: 'user' or 'assistant'
        content: Message text
    
    Returns:
        Message ID
    """
    if role not in ['user', 'assistant']:
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
    
    from backend.db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            INSERT INTO chat_messages (user_id, role, content, created_at)
            VALUES (:user_id, :role, :content, :created_at)
            """),
            {"user_id": user_id, "role": role, "content": content, "created_at": datetime.now()}
        )
        conn.commit()
        message_id = result.lastrowid
    
    logger.debug(f"Stored {role} message (ID: {message_id}) for user {user_id}")
    return message_id


async def get_chat_history(
    user_id: int,
    limit: int = 50
) -> List[Dict]:
    """
    Get chat history for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of messages (default: 50)
    
    Returns:
        List of messages (newest first)
    """
    from backend.db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit}
        )
        
        messages = []
        for row in result.fetchall():
            messages.append({
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'created_at': row[3]
            })
    
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    
    return messages


async def clear_chat_history(user_id: int):
    """
    Clear all chat messages for a user.
    
    Args:
        user_id: User ID
    """
    from backend.db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM chat_messages WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        deleted_count = result.rowcount
        conn.commit()
    
    logger.info(f"Cleared {deleted_count} messages for user {user_id}")


async def get_chat_stats(user_id: int) -> Dict:
    """
    Get chat statistics for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        Dict with message counts and first/last message dates
    """
    from backend.db.database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT 
                COUNT(*) as total_messages,
                SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as user_messages,
                SUM(CASE WHEN role = 'assistant' THEN 1 ELSE 0 END) as assistant_messages,
                MIN(created_at) as first_message,
                MAX(created_at) as last_message
            FROM chat_messages
            WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        
        row = result.fetchone()
    
    return {
        'total_messages': row[0] or 0,
        'user_messages': row[1] or 0,
        'assistant_messages': row[2] or 0,
        'first_message': row[3],
        'last_message': row[4]
    }
