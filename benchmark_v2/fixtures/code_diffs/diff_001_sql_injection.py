# PR #1247: Add user search endpoint
def search_users(db, query_text: str):
    """Search users by name or email."""
    sql = f"SELECT * FROM users WHERE name LIKE '%{query_text}%' OR email LIKE '%{query_text}%'"
    return db.execute(sql).fetchall()

def get_user_profile(db, user_id: int):
    sql = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(sql).fetchone()
