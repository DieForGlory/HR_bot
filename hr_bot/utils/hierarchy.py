from sqlalchemy import select
from hr_bot.database.models import User, Department


async def get_manager_tg_id(session, user: User) -> list[int]:
    # 1. Прямое переопределение (установленное вручную)
    if user.manager_id:
        mgr = await session.get(User, user.manager_id)
        if mgr: return [mgr.tg_id]

    # 2. Иерархия подразделений
    if user.department_id:
        dept = await session.get(Department, user.department_id)
        if dept:
            if dept.head_id == user.id:
                if dept.parent_id:
                    parent = await session.get(Department, dept.parent_id)
                    if parent and parent.head_id:
                        head = await session.get(User, parent.head_id)
                        if head: return [head.tg_id]
            else:
                if dept.head_id:
                    head = await session.get(User, dept.head_id)
                    if head: return [head.tg_id]

    # 3. Маршрутизация по умолчанию (HR отдел / Администраторы)
    hrs = await session.execute(select(User).where(User.role == "hr"))
    return [hr.tg_id for hr in hrs.scalars()]