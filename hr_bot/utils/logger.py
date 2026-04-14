from hr_bot.database.models import AuditLog
from datetime import datetime

async def log_action(session, user_id: int, action: str, details: str = ""):
    log = AuditLog(user_id=user_id, action=action, details=details, timestamp=datetime.now())
    session.add(log)