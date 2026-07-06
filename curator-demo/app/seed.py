"""КУРАТОР — сид демо-данных Краснодарского края.

ВНИМАНИЕ: суммы и условия — ДЕМОНСТРАЦИОННЫЕ (примерные), для показа механики подбора.
Перед пилотом администратор заменяет их актуальными данными региона через импорт.
"""
import random
from datetime import datetime, timedelta
from .db import get_conn, jdump

CATEGORIES = [
    ("svo_participant", "Участник СВО", "regional", "23"),
    ("svo_veteran", "Ветеран боевых действий", "federal", None),
    ("svo_family", "Член семьи участника СВО", "regional", "23"),
    ("svo_deceased_family", "Член семьи погибшего участника СВО", "regional", "23"),
    ("svo_injured", "Получивший ранение (СВО)", "regional", "23"),
    ("large_family", "Многодетная семья", "regional", "23"),
    ("disabled", "Инвалид", "federal", None),
    ("low_income", "Малоимущий", "regional", "23"),
    ("has_children", "Имеет несовершеннолетних детей", "federal", None),
]

# Жизненные ситуации (life events)
LIFE_EVENTS = [
    ("svo_return", "Возвращение со службы (СВО)"),
    ("svo_injury", "Ранение / инвалидность (СВО)"),
    ("svo_death", "Гибель участника СВО (для семьи)"),
    ("svo_mobilized", "Мобилизация / служба по контракту"),
    ("childbirth", "Рождение ребёнка"),
    ("large_family", "Статус многодетной семьи"),
    ("disability", "Оформление инвалидности"),
    ("housing", "Улучшение жилищных условий"),
    ("job_search", "Трудоустройство / переобучение"),
    ("education", "Образование детей"),
    ("medical", "Лечение и реабилитация"),
    ("business", "Открытие своего дела"),
]

A = "Минтруд и соцразвития Краснодарского края"
SOC = "Соцзащита Краснодарского края"
MED = "Минздрав Краснодарского края"


def _m(code, title, desc, mtype, level, region, authority, amount, rules,
       docs, required=None, soft=None):
    elig = {"rules": rules, "required_fields": required or []}
    if soft:
        elig["soft"] = soft
    return {"code": code, "title": title, "description": desc, "measure_type": mtype,
            "level": level, "region_code": region, "authority": authority, "amount": amount,
            "eligibility": elig, "required_documents": docs}


def _cat(*vals):
    return {"field": "categories", "op": "contains_any", "value": list(vals)}

def _catall(*vals):
    return {"field": "categories", "op": "contains_all", "value": list(vals)}

def _reg23():
    return {"field": "region_code", "op": "eq", "value": "23"}

DOC_PASS = "Паспорт"
DOC_MIL = "Военный билет / справка о статусе участника СВО"

MEASURES = [
    # --- Выплаты участникам СВО ---
    _m("KK-SVO-PAY-001", "Единовременная региональная выплата участнику СВО",
       "Единовременная денежная выплата участникам СВО, зарегистрированным в крае.",
       "payment", "regional", "23", A, 100000,
       {"all": [_cat("svo_participant"), _reg23()]},
       [DOC_PASS, DOC_MIL], ["categories", "region_code"]),
    _m("KK-SVO-PAY-002", "Ежемесячная выплата семье участника СВО с детьми",
       "Ежемесячная выплата семьям участников СВО с несовершеннолетними детьми.",
       "payment", "regional", "23", SOC, 15000,
       {"all": [_cat("svo_participant", "svo_family"), _reg23(),
                {"field": "children_count", "op": "gte", "value": 1}]},
       [DOC_PASS, "Свидетельства о рождении детей"],
       ["categories", "region_code", "children_count"]),
    _m("KK-SVO-PAY-006", "Единовременная выплата семье погибшего участника СВО",
       "Единовременная выплата членам семьи погибшего (умершего) участника СВО.",
       "payment", "regional", "23", A, 1000000,
       {"all": [_cat("svo_deceased_family"), _reg23()]},
       [DOC_PASS, "Свидетельство о смерти", "Документы о родстве"],
       ["categories", "region_code"]),
    _m("KK-SVO-PAY-011", "Ежемесячная выплата по инвалидности вследствие ранения",
       "Региональная доплата участникам СВО, получившим инвалидность вследствие ранения.",
       "payment", "regional", "23", SOC, 20000,
       {"all": [_reg23()], "any": [_cat("svo_injured"), _cat("disabled")]},
       [DOC_PASS, "Справка об инвалидности / ранении"],
       ["categories", "region_code"]),
    # --- Льготы и услуги ---
    _m("KK-SVO-LAND-003", "Первоочередное предоставление земельного участка",
       "Первоочередное право на бесплатный земельный участок многодетным семьям участников СВО.",
       "benefit", "regional", "23", "Департамент имущественных отношений КК", None,
       {"all": [_catall("svo_participant", "large_family"), _reg23()]},
       [DOC_PASS, "Документы о составе семьи"], ["categories", "region_code"]),
    _m("KK-SVO-REHAB-004", "Санаторно-курортная реабилитация",
       "Направление на реабилитацию для участников СВО, получивших ранение.",
       "service", "regional", "23", MED, None,
       {"all": [_cat("svo_participant"), _reg23()],
        "any": [_cat("disabled"), {"field": "has_injury", "op": "is_true", "value": True}]},
       [DOC_PASS, "Медицинское заключение"], ["categories", "region_code"]),
    _m("KK-SVO-PSY-007", "Психологическое сопровождение семьи",
       "Бесплатные консультации психолога для участников СВО и членов их семей.",
       "service", "regional", "23", "Центр соцобслуживания КК", None,
       {"all": [_cat("svo_participant", "svo_family", "svo_deceased_family"), _reg23()]},
       [DOC_PASS], ["categories", "region_code"]),
    _m("KK-SVO-MED-012", "Первоочередное медицинское обслуживание",
       "Внеочередной приём в медучреждениях края для участников СВО и ветеранов.",
       "benefit", "regional", "23", MED, None,
       {"all": [_cat("svo_participant", "svo_veteran"), _reg23()]},
       [DOC_PASS, DOC_MIL], ["categories", "region_code"]),
    _m("KK-SVO-TRANSPORT-013", "Бесплатный проезд в общественном транспорте",
       "Право бесплатного проезда для участников СВО и ветеранов боевых действий.",
       "benefit", "regional", "23", "Минтранс Краснодарского края", None,
       {"all": [_cat("svo_participant", "svo_veteran"), _reg23()]},
       [DOC_PASS, DOC_MIL], ["categories", "region_code"]),
    _m("KK-SVO-UTIL-014", "Компенсация части расходов на ЖКУ",
       "Компенсация 50% расходов на коммунальные услуги семьям участников СВО.",
       "compensation", "regional", "23", SOC, None,
       {"all": [_cat("svo_participant", "svo_family", "svo_deceased_family"), _reg23()]},
       [DOC_PASS, "Квитанции ЖКУ"], ["categories", "region_code"]),
    # --- Жильё ---
    _m("KK-SVO-HOUSE-005", "Субсидия на улучшение жилищных условий",
       "Субсидия на приобретение/строительство жилья участникам СВО с невысоким доходом.",
       "compensation", "regional", "23", "Минстрой Краснодарского края", 500000,
       {"all": [_cat("svo_participant"), _reg23()]},
       [DOC_PASS, "Справка о доходах", "Документы на жильё"],
       ["categories", "region_code", "income_month"],
       soft=[{"field": "income_month", "op": "lte", "value": 30000, "weight": 20}]),
    _m("KK-LOW-HOUSE-015", "Постановка на учёт нуждающихся в жилье",
       "Постановка малоимущих семей на учёт для получения жилья по договору соцнайма.",
       "benefit", "regional", "23", "Минстрой Краснодарского края", None,
       {"all": [_cat("low_income"), _reg23()]},
       [DOC_PASS, "Справка о доходах"], ["categories", "region_code"]),
    # --- Дети и образование ---
    _m("FED-SVO-EDU-010", "Бесплатное обучение детей участника СВО в вузе (квота)",
       "Федеральная квота на бесплатное высшее образование для детей участников СВО.",
       "benefit", "federal", None, "Минобрнауки России", None,
       {"all": [_cat("svo_participant", "svo_family"),
                {"field": "children_count", "op": "gte", "value": 1}]},
       [DOC_PASS, "Документы об обучении ребёнка"], ["categories", "children_count"]),
    _m("KK-CHILD-EDU-016", "Бесплатное питание школьников",
       "Бесплатное горячее питание для детей из семей участников СВО и многодетных семей.",
       "benefit", "regional", "23", "Минобразования КК", None,
       {"all": [_reg23(), {"field": "children_count", "op": "gte", "value": 1}],
        "any": [_cat("svo_participant", "svo_family"), _cat("large_family")]},
       [DOC_PASS, "Справка из школы"], ["categories", "region_code", "children_count"]),
    _m("KK-CHILD-KG-017", "Первоочередное зачисление в детский сад",
       "Первоочередное предоставление места в детском саду детям участников СВО.",
       "benefit", "regional", "23", "Минобразования КК", None,
       {"all": [_cat("svo_participant", "svo_family"), _reg23(),
                {"field": "children_count", "op": "gte", "value": 1}]},
       [DOC_PASS, "Свидетельство о рождении ребёнка"],
       ["categories", "region_code", "children_count"]),
    _m("FED-CHILD-BIRTH-018", "Единовременное пособие при рождении ребёнка",
       "Федеральное единовременное пособие при рождении ребёнка.",
       "payment", "federal", None, "СФР", 24600,
       {"all": [{"field": "children_count", "op": "gte", "value": 1}]},
       [DOC_PASS, "Свидетельство о рождении"], ["children_count"]),
    # --- Многодетные / малоимущие ---
    _m("KK-LARGE-019", "Ежемесячная выплата многодетной семье",
       "Ежемесячная денежная выплата многодетным семьям края.",
       "payment", "regional", "23", SOC, 8000,
       {"all": [_cat("large_family"), _reg23()]},
       [DOC_PASS, "Удостоверение многодетной семьи"], ["categories", "region_code"]),
    _m("KK-LOW-020", "Социальный контракт",
       "Единовременная помощь малоимущим на развитие подсобного хозяйства/самозанятости.",
       "compensation", "regional", "23", SOC, 350000,
       {"all": [_cat("low_income"), _reg23()]},
       [DOC_PASS, "Справка о доходах"], ["categories", "region_code", "income_month"],
       soft=[{"field": "income_month", "op": "lte", "value": 20000, "weight": 20}]),
    # --- Трудоустройство / бизнес ---
    _m("KK-SVO-JOB-021", "Приоритетное трудоустройство и переобучение",
       "Содействие в трудоустройстве и бесплатное переобучение участников СВО.",
       "service", "regional", "23", "Центр занятости КК", None,
       {"all": [_cat("svo_participant", "svo_veteran"), _reg23()]},
       [DOC_PASS, DOC_MIL], ["categories", "region_code"]),
    _m("KK-SVO-BIZ-022", "Грант на открытие своего дела",
       "Региональный грант участникам СВО на запуск малого бизнеса.",
       "payment", "regional", "23", "Департамент инвестиций КК", 500000,
       {"all": [_cat("svo_participant"), _reg23()]},
       [DOC_PASS, DOC_MIL, "Бизнес-план"], ["categories", "region_code"]),
    # --- Инвалидность ---
    _m("FED-DIS-023", "Ежемесячная денежная выплата инвалидам (ЕДВ)",
       "Федеральная ежемесячная денежная выплата инвалидам.",
       "payment", "federal", None, "СФР", 5000,
       {"all": [_cat("disabled")]},
       [DOC_PASS, "Справка об инвалидности"], ["categories"]),
    _m("KK-DIS-024", "Обеспечение техническими средствами реабилитации",
       "Предоставление ТСР инвалидам, в т.ч. вследствие ранения на СВО.",
       "service", "regional", "23", MED, None,
       {"all": [_cat("disabled"), _reg23()]},
       [DOC_PASS, "ИПРА"], ["categories", "region_code"]),
    # --- Ветераны ---
    _m("FED-VET-025", "Ежемесячная выплата ветерану боевых действий",
       "Федеральная ежемесячная выплата ветеранам боевых действий.",
       "payment", "federal", None, "СФР", 4000,
       {"all": [_cat("svo_veteran")]},
       [DOC_PASS, "Удостоверение ветерана"], ["categories"]),
    _m("KK-VET-026", "Налоговая льгота по имущественному налогу",
       "Освобождение от налога на имущество для ветеранов и участников СВО.",
       "benefit", "regional", "23", "ФНС / Минфин КК", None,
       {"all": [_cat("svo_participant", "svo_veteran"), _reg23()]},
       [DOC_PASS, DOC_MIL], ["categories", "region_code"]),
]

DEMO_USERS = [
    {"role": "coordinator", "phone": "+79180000001", "first_name": "Мария", "last_name": "Соколова", "region_code": "23"},
    {"role": "admin", "phone": "+79180000002", "first_name": "Администратор", "last_name": "региона", "region_code": "23"},
]


def seed():
    with get_conn() as conn:
        cur = conn.cursor()
        if cur.execute("SELECT COUNT(*) c FROM measures").fetchone()["c"] > 0:
            return
        for code, title, level, region in CATEGORIES:
            cur.execute("INSERT OR IGNORE INTO citizen_categories(code,title,level,region_code) VALUES(?,?,?,?)",
                        (code, title, level, region))
        for m in MEASURES:
            cur.execute(
                """INSERT INTO measures(code,title,description,measure_type,level,region_code,
                   authority,amount,eligibility,required_documents) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (m["code"], m["title"], m["description"], m["measure_type"], m["level"],
                 m["region_code"], m["authority"], m["amount"], jdump(m["eligibility"]),
                 jdump(m["required_documents"])))
        for u in DEMO_USERS:
            cur.execute("INSERT OR IGNORE INTO users(role,phone,first_name,last_name,region_code) VALUES(?,?,?,?,?)",
                        (u["role"], u["phone"], u["first_name"], u["last_name"], u["region_code"]))


_FIRST = ["Иван","Сергей","Андрей","Дмитрий","Алексей","Николай","Павел","Артём","Владимир","Максим",
          "Олег","Роман","Юрий","Егор","Денис","Виктор","Анна","Елена","Ольга","Наталья","Марина",
          "Татьяна","Ирина","Светлана","Людмила","Галина"]
_LAST = ["Ковалёв","Соколов","Морозов","Волков","Лебедев","Козлов","Новиков","Фёдоров","Никитин","Орлов",
         "Макаров","Захаров","Борисов","Киселёв","Ильин","Гусев","Титов","Кузьмин","Кудрявцев","Баранов"]
_STATUS = ["submitted"]*5 + ["in_review"]*4 + ["approved"]*4 + ["paid"]*6 + ["rejected"]*2
_LIFE = ["svo_return","svo_injury","svo_death","svo_mobilized","childbirth","housing","disability",
         "large_family","medical","job_search"]
_EVENTS = ["Создан кейс","Заполнена анкета","Подбор мер поддержки","Поданы документы","Заявка отправлена"]


def seed_synthetic(n=38):
    """Наполнение демо синтетикой: граждане, кейсы, заявки во всех статусах за 14 дней."""
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) c FROM users WHERE phone LIKE '+7999%'").fetchone()["c"] > 0:
            return
        coord = conn.execute("SELECT id FROM users WHERE role='coordinator' LIMIT 1").fetchone()
        coord_id = coord["id"] if coord else None
        measures = [dict(r) for r in conn.execute("SELECT id,amount FROM measures WHERE is_current=1").fetchall()]
        cats = [r["code"] for r in conn.execute("SELECT code FROM citizen_categories").fetchall()]
        if not measures:
            return
        for _ in range(n):
            fn, ln = random.choice(_FIRST), random.choice(_LAST)
            phone = f"+7999{random.randint(1000000, 9999999)}"
            uid = conn.execute(
                "INSERT INTO users(role,phone,first_name,last_name,region_code,coordinator_id) VALUES('citizen',?,?,?,?,?)",
                (phone, fn, ln, "23", coord_id)).lastrowid
            for cc in random.sample(cats, k=random.randint(1, 2)):
                conn.execute("INSERT OR IGNORE INTO user_categories(user_id,category_code) VALUES(?,?)", (uid, cc))
            le = random.choice(_LIFE)
            days = random.randint(0, 13)
            base = datetime.utcnow() - timedelta(days=days, hours=random.randint(0, 23))
            pid = conn.execute(
                "INSERT INTO projects(citizen_id,coordinator_id,title,life_event,status) VALUES(?,?,?,?,'active')",
                (uid, coord_id, "Кейс сопровождения", le)).lastrowid
            # события истории кейса
            for k, ev in enumerate(_EVENTS):
                conn.execute("INSERT INTO case_events(project_id,event,actor,created_at) VALUES(?,?,?,?)",
                             (pid, ev, "Система" if k == 2 else "Гражданин",
                              (base + timedelta(minutes=k * 3)).isoformat()))
            for _a in range(random.randint(1, 2)):
                m = random.choice(measures)
                st = random.choice(_STATUS)
                ts = (base + timedelta(hours=random.randint(1, 20))).isoformat()
                conn.execute(
                    """INSERT INTO applications(project_id,citizen_id,measure_id,measure_version,coordinator_id,status,expected_amount,created_at)
                       VALUES(?,?,?,1,?,?,?,?)""",
                    (pid, uid, m["id"], coord_id, st, m["amount"], ts))
