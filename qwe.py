import asyncio
import re
from sqlalchemy import select
from hr_bot.database.models import Department, Base
from hr_bot.database.engine import async_session, engine

DEPARTMENTS_DATA = [
    "1. Руководство",
    "1.1 Отдел по административным вопросам",
    "1.2 Отдел административного управления",
    "2. Юридический отдел",
    "3. Отдел клиентского обслуживания",
    "4. Управление земельных отношений и разрешительной документации",
    "4.1 Отдел земельных отношений и кадастра",
    "4.2 Отдел разрешительной документации",
    "5. Финансовый департамент",
    "5.1 Управление бухгалтерского учета и отчетности",
    "5.1.1 Отдел взаиморасчетов",
    "5.1.2 Отдел операционного учета",
    "5.1.3 Отдел реализации",
    "5.1.4 Отдел расчета заработной платы",
    "5.2 Планово - экономический отдел",
    "5.2.1 Группа экономической аналитики",
    "5.2.2 Группа казначейства",
    "6. Административный департамент",
    "6.1 Административно – хозяйственный отдел",
    "6.2 Отдел технической поддержки и системного администрирования",
    "7. Коммерческий департамент",
    "7.1 Управление продаж",
    "7.1.1 Отдел продаж",
    "Группа №1",
    "7.1.2 Отдел продаж коммерческой недвижимости",
    "7.1.3 Отдел телефонных продаж",
    "7.2 Отдел ипотеки и специальных программ",
    "7.3 Отдел по работе с дебиторской задолженностью",
    "7.4 Отдел оформления",
    "7.5 Отдел развития стратегических программ",
    "7.6 Отдел аналитики и развития",
    "7.6.1 Группа аналитики",
    "7.7 Управление маркетинга и рекламы",
    "7.7.1 Отдел digital-маркетинга",
    "8. Департамент клиентского сервиса",
    "8.1 Отдел передачи и клиентского сопровождения",
    "8.2 Отдел гарантийного ремонта",
    "9. Департамент технического заказчика",
    "9.1 Управление инженерных сетей",
    "9.2 Отдел охраны труда и техники безопасности",
    "9.3 Отдел технического надзора",
    "9.4 Производственно технический отдел",
    "9.4.1 Сметно - договорная группа",
    "10. Управление проектами",
    "10.1 Отдел планирования и отчетности",
    "10.2 Отдел главных инженеров проектов",
    "10.3 Отдел архитектуры и дизайна",
    "11. Департамент по работе с персоналом и организационному развитию",
    "11.1 Отдел кадрового администрирования",
    "11.2 Отдел по работе с персоналом",
    "12. Департамент по безопасности",
    "12.1 Отдел технических средств охраны по обеспечению защиты имущества"
]


async def seed_departments():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        level_map = {}
        last_parent_id = None

        for line in DEPARTMENTS_DATA:
            clean_line = line.strip()
            if not clean_line:
                continue

            match = re.match(r'^([\d\.]+)\s*(.*)', clean_line)

            if match:
                raw_prefix = match.group(1)
                prefix = raw_prefix.rstrip('.')
                name = match.group(2).strip()

                parent_prefix = '.'.join(prefix.split('.')[:-1])
                parent_id = level_map.get(parent_prefix) if parent_prefix else None
            else:
                name = clean_line
                prefix = None
                parent_id = last_parent_id

            stmt = select(Department).where(Department.name == name)
            result = await session.execute(stmt)
            existing_dept = result.scalar_one_or_none()

            if existing_dept:
                dept_id = existing_dept.id
            else:
                dept = Department(name=name, parent_id=parent_id)
                session.add(dept)
                await session.flush()
                dept_id = dept.id

            if prefix:
                level_map[prefix] = dept_id
            last_parent_id = dept_id

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_departments())