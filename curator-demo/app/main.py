"""КУРАТОР — демо-прототип (модульный монолит на FastAPI).

Сквозной сценарий: вход по SMS → создание кейса → анкета → подбор (Rule Engine) →
объяснение → подача заявки → кабинет координатора видит заявку.

Запуск:  uvicorn app.main:app --reload  (из папки curator-demo)
Демо-код SMS: 1234
"""
from __future__ import annotations
import os
from datetime import date, datetime

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import get_conn, init_db, jload, jdump
from .seed import seed, LIFE_EVENTS as SEED_LIFE_EVENTS
from . import rule_engine

DEFAULT_BRANDING = {
    "region_name": "Краснодарский край",
    "system_name": "КУРАТОР",
    "emblem": "🛡️",
    "color_primary": "#0b5cab",
    "welcome": "Цифровое сопровождение участников СВО и членов их семей",
}

def log_event(conn, project_id, event, actor="Гражданин", status=None):
    conn.execute(
        "INSERT INTO case_events(project_id,event,actor,status,created_at) VALUES(?,?,?,?,?)",
        (project_id, event, actor, status, datetime.utcnow().isoformat()))

def notify(conn, user_id, text):
    conn.execute(
        "INSERT INTO notifications(user_id,text,created_at) VALUES(?,?,?)",
        (user_id, text, datetime.utcnow().isoformat()))

def get_branding(conn):
    b = dict(DEFAULT_BRANDING)
    for r in conn.execute("SELECT key,value FROM settings").fetchall():
        if r["key"].startswith("brand."):
            b[r["key"][6:]] = r["value"]
    return b

DEMO_OTP = "1234"
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")

app = FastAPI(title="КУРАТОР — демо", version="0.1")


@app.on_event("startup")
def _startup():
    init_db()
    seed()


# ---------- Auth helpers ----------
def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer user-"):
        raise HTTPException(401, "unauthorized")
    uid = authorization.replace("Bearer user-", "")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(401, "unauthorized")
    return dict(row)


def _categories(conn, uid):
    return [r["category_code"] for r in
            conn.execute("SELECT category_code FROM user_categories WHERE user_id=?", (uid,)).fetchall()]


# ---------- MODULE: Auth ----------
class OtpReq(BaseModel):
    phone: str

class OtpVerify(BaseModel):
    phone: str
    code: str
    first_name: str | None = None
    last_name: str | None = None

@app.post("/api/v1/auth/otp/request")
def otp_request(body: OtpReq):
    return {"request_id": "demo", "demo_code": DEMO_OTP, "message": "Демо: код всегда 1234"}

@app.post("/api/v1/auth/otp/verify")
def otp_verify(body: OtpVerify):
    if body.code != DEMO_OTP:
        raise HTTPException(422, "invalid_otp")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE phone=?", (body.phone,)).fetchone()
        if not row:
            cur = conn.execute(
                "INSERT INTO users(role,phone,first_name,last_name,region_code) VALUES('citizen',?,?,?, '23')",
                (body.phone, body.first_name or "Гость", body.last_name or ""))
            uid = cur.lastrowid
        else:
            uid = row["id"]
        u = dict(conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    return {"token": f"user-{uid}", "user": u}


# ---------- MODULE: Users ----------
class Cats(BaseModel):
    categories: list[str]

@app.get("/api/v1/users/me")
def me(user=Depends(current_user)):
    with get_conn() as conn:
        user["categories"] = _categories(conn, user["id"])
    return user

@app.put("/api/v1/users/me")
def update_me(body: dict, user=Depends(current_user)):
    fields = {k: body[k] for k in ("first_name", "last_name", "birth_date", "region_code") if k in body}
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        with get_conn() as conn:
            conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*fields.values(), user["id"]))
    return {"ok": True}

@app.put("/api/v1/users/me/categories")
def set_categories(body: Cats, user=Depends(current_user)):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_categories WHERE user_id=?", (user["id"],))
        for c in body.categories:
            conn.execute("INSERT OR IGNORE INTO user_categories(user_id,category_code) VALUES(?,?)",
                         (user["id"], c))
    return {"ok": True, "categories": body.categories}

@app.get("/api/v1/dictionaries/citizen_categories")
def dict_categories():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM citizen_categories").fetchall()]


# ---------- White Label (branding) ----------
@app.get("/api/v1/branding")
def branding():
    with get_conn() as conn:
        return get_branding(conn)

@app.put("/api/v1/branding")
def set_branding(body: dict, user=Depends(current_user)):
    if user["role"] not in ("admin", "coordinator"):
        raise HTTPException(403, "forbidden")
    with get_conn() as conn:
        for k, v in body.items():
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (f"brand.{k}", str(v)))
        return get_branding(conn)


# ---------- MODULE: Projects ----------
LIFE_EVENTS = [{"code": c, "title": t} for c, t in SEED_LIFE_EVENTS]

class ProjIn(BaseModel):
    life_event: str
    title: str | None = None

@app.get("/api/v1/life_events")
def life_events():
    return LIFE_EVENTS

@app.post("/api/v1/projects")
def create_project(body: ProjIn, user=Depends(current_user)):
    le_title = next((e["title"] for e in LIFE_EVENTS if e["code"] == body.life_event), body.life_event)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO projects(citizen_id,title,life_event,status) VALUES(?,?,?,'active')",
            (user["id"], body.title or "Кейс сопровождения", body.life_event))
        pid = cur.lastrowid
        log_event(conn, pid, f"Создан кейс: {le_title}", "Гражданин", "active")
        return dict(conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone())

@app.get("/api/v1/projects/{pid}/timeline")
def timeline(pid: int, user=Depends(current_user)):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM case_events WHERE project_id=? ORDER BY id", (pid,)).fetchall()
        return [dict(r) for r in rows]

@app.get("/api/v1/projects")
def list_projects(user=Depends(current_user)):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM projects WHERE citizen_id=?", (user["id"],)).fetchall()
        return [dict(r) for r in rows]


# ---------- MODULE: Questionnaire ----------
def questionnaire_schema(life_event: str):
    base = [
        {"code": "children_count", "type": "number", "required": False, "label": "Сколько несовершеннолетних детей?"},
    ]
    dynamic = []
    if life_event in ("svo_injury",):
        dynamic = [{"code": "has_injury", "type": "bool", "required": True, "label": "Есть ранение/инвалидность?"}]
    return [{"code": "base", "title": "Базовые данные", "questions": base}] + (
        [{"code": life_event, "title": "Уточнения", "questions": dynamic}] if dynamic else [])

@app.get("/api/v1/projects/{pid}/questionnaire")
def get_quest(pid: int, user=Depends(current_user)):
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p:
            raise HTTPException(404, "not_found")
        return {"schema": questionnaire_schema(p["life_event"]), "answers": jload(p["answers"]) or {}}

@app.put("/api/v1/projects/{pid}/questionnaire")
def put_quest(pid: int, body: dict, user=Depends(current_user)):
    answers = body.get("answers", {})
    with get_conn() as conn:
        conn.execute("UPDATE projects SET answers=?, status='active' WHERE id=?", (jdump(answers), pid))
        log_event(conn, pid, "Заполнена анкета", "Гражданин")
    return {"ok": True, "answers": answers}


# ---------- MODULE: Rule Engine (matching) ----------
def build_context(conn, user, project) -> dict:
    cats = _categories(conn, user["id"])
    answers = jload(project["answers"]) or {}
    age = None
    if user.get("birth_date"):
        try:
            b = datetime.strptime(user["birth_date"], "%Y-%m-%d").date()
            age = (date.today() - b).days // 365
        except Exception:
            pass
    return {
        "subject_type": "citizen",
        "categories": cats,
        "region_code": user.get("region_code"),
        "age": age,
        "children_count": answers.get("children_count"),
        "has_injury": answers.get("has_injury"),
        "income_month": answers.get("income_month"),
    }

def _measures(conn):
    out = []
    for r in conn.execute("SELECT * FROM measures WHERE is_current=1").fetchall():
        m = dict(r)
        m["eligibility"] = jload(m["eligibility"])
        m["required_documents"] = jload(m["required_documents"])
        out.append(m)
    return out

@app.post("/api/v1/projects/{pid}/matching/run")
def run_matching(pid: int, user=Depends(current_user)):
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not p:
            raise HTTPException(404, "not_found")
        ctx = build_context(conn, user, dict(p))
        results = rule_engine.match(ctx, _measures(conn), include_hidden=False)
        now = datetime.utcnow().isoformat()
        for r in results:
            conn.execute(
                "INSERT INTO rule_eval_log(project_id,measure_id,score,category,evaluated_at) VALUES(?,?,?,?,?)",
                (pid, r["measure_id"], r["score"], r["category"], now))
        eligible = sum(1 for r in results if r["category"] == "eligible")
        log_event(conn, pid, f"Подбор мер: найдено {len(results)} (положено — {eligible})", "Система")
    return {"count": len(results), "results": results, "context": ctx}


# ---------- MODULE: Applications ----------
class AppIn(BaseModel):
    project_id: int
    measure_id: int

@app.post("/api/v1/applications")
def create_application(body: AppIn, user=Depends(current_user)):
    with get_conn() as conn:
        m = conn.execute("SELECT * FROM measures WHERE id=?", (body.measure_id,)).fetchone()
        if not m:
            raise HTTPException(404, "measure_not_found")
        coord = conn.execute("SELECT id FROM users WHERE role='coordinator' LIMIT 1").fetchone()
        cur = conn.execute(
            """INSERT INTO applications(project_id,citizen_id,measure_id,measure_version,
               coordinator_id,status,expected_amount,created_at)
               VALUES(?,?,?,?,?,'submitted',?,?)""",
            (body.project_id, user["id"], body.measure_id, m["version"],
             coord["id"] if coord else None, m["amount"], datetime.utcnow().isoformat()))
        aid = cur.lastrowid
        log_event(conn, body.project_id, f"Подана заявка: {m['title']}", "Гражданин", "submitted")
        return dict(conn.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone())

@app.get("/api/v1/applications")
def my_applications(user=Depends(current_user)):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT a.*, m.title measure_title FROM applications a
               JOIN measures m ON m.id=a.measure_id WHERE a.citizen_id=?""", (user["id"],)).fetchall()
        return [dict(r) for r in rows]


# ---------- MODULE: Coordinator ----------
@app.get("/api/v1/coordinator/applications")
def coordinator_applications(user=Depends(current_user)):
    if user["role"] != "coordinator":
        raise HTTPException(403, "forbidden")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT a.*, m.title measure_title, u.first_name, u.last_name, u.phone
               FROM applications a
               JOIN measures m ON m.id=a.measure_id
               JOIN users u ON u.id=a.citizen_id
               WHERE a.coordinator_id=? ORDER BY a.id DESC""", (user["id"],)).fetchall()
        return [dict(r) for r in rows]

APPLICATION_STATUSES = [
    {"code": "submitted", "title": "Подана", "order": 20},
    {"code": "in_review", "title": "На проверке", "order": 30},
    {"code": "approved", "title": "Одобрена", "order": 50},
    {"code": "paid", "title": "Выплачена", "order": 60},
    {"code": "rejected", "title": "Отказано", "order": 90},
]

@app.get("/api/v1/application_statuses")
def application_statuses():
    return APPLICATION_STATUSES

class StatusIn(BaseModel):
    status: str

@app.post("/api/v1/coordinator/applications/{aid}/status")
def change_status(aid: int, body: StatusIn, user=Depends(current_user)):
    if user["role"] != "coordinator":
        raise HTTPException(403, "forbidden")
    if body.status not in {s["code"] for s in APPLICATION_STATUSES}:
        raise HTTPException(422, "invalid_status")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id=? AND coordinator_id=?",
                           (aid, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "not_found")
        conn.execute("UPDATE applications SET status=? WHERE id=?", (body.status, aid))
        st_title = next((s["title"] for s in APPLICATION_STATUSES if s["code"] == body.status), body.status)
        log_event(conn, row["project_id"], f"Статус заявки: {st_title}", "Координатор", body.status)
        m = conn.execute("SELECT title FROM measures WHERE id=?", (row["measure_id"],)).fetchone()
        notify(conn, row["citizen_id"], f"Статус заявки «{m['title'] if m else ''}»: {st_title}")
    return {"ok": True, "id": aid, "status": body.status}

@app.post("/api/v1/coordinator/login")
def coordinator_login():
    """Демо-вход координатора одним кликом."""
    with get_conn() as conn:
        c = conn.execute("SELECT * FROM users WHERE role='coordinator' LIMIT 1").fetchone()
        return {"token": f"user-{c['id']}", "user": dict(c)}


# ---------- MODULE: Notifications ----------
@app.get("/api/v1/notifications")
def notifications(user=Depends(current_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/v1/notifications/{nid}/read")
def read_notification(nid: int, user=Depends(current_user)):
    with get_conn() as conn:
        conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (nid, user["id"]))
    return {"ok": True}


# ---------- MODULE: Admin (управление мерами, White Label) ----------
@app.post("/api/v1/admin/login")
def admin_login():
    with get_conn() as conn:
        a = conn.execute("SELECT * FROM users WHERE role='admin' LIMIT 1").fetchone()
        return {"token": f"user-{a['id']}", "user": dict(a)}

@app.get("/api/v1/admin/measures")
def admin_measures(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "forbidden")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id,code,title,measure_type,level,region_code,authority,amount,is_current FROM measures ORDER BY id").fetchall()
        return [dict(r) for r in rows]

class MeasureIn(BaseModel):
    title: str
    amount: float | None = None
    category_code: str = "svo_participant"
    region_code: str = "23"
    authority: str = "Администрация региона"
    documents: list[str] = []

@app.post("/api/v1/admin/measures")
def admin_create_measure(body: MeasureIn, user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "forbidden")
    elig = {"rules": {"all": [
        {"field": "categories", "op": "contains_any", "value": [body.category_code]},
        {"field": "region_code", "op": "eq", "value": body.region_code},
    ]}, "required_fields": ["categories", "region_code"]}
    code = "ADM-" + str(abs(hash(body.title)) % 100000)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO measures(code,title,description,measure_type,level,region_code,
               authority,amount,eligibility,required_documents,version,is_current)
               VALUES(?,?,?,?,?,?,?,?,?,?,1,1)""",
            (code, body.title, "Добавлено администратором региона", "payment", "regional",
             body.region_code, body.authority, body.amount, jdump(elig), jdump(body.documents)))
        return {"ok": True, "id": cur.lastrowid, "code": code}


# ---------- MODULE: Dashboard (руководитель) ----------
@app.get("/api/v1/dashboard/summary")
def dashboard_summary():
    with get_conn() as conn:
        new_cases = conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"]
        active_apps = conn.execute("SELECT COUNT(*) c FROM applications WHERE status NOT IN ('paid','rejected')").fetchone()["c"]
        done_cases = conn.execute("SELECT COUNT(*) c FROM applications WHERE status='paid'").fetchone()["c"]
        by_status = {s["code"]: 0 for s in APPLICATION_STATUSES}
        for r in conn.execute("SELECT status, COUNT(*) c FROM applications GROUP BY status").fetchall():
            by_status[r["status"]] = r["c"]
        top = conn.execute(
            """SELECT m.title, COUNT(*) c FROM applications a JOIN measures m ON m.id=a.measure_id
               GROUP BY a.measure_id ORDER BY c DESC LIMIT 5""").fetchall()
        total_paid = conn.execute("SELECT COALESCE(SUM(expected_amount),0) s FROM applications WHERE status='paid'").fetchone()["s"]
        return {
            "new_cases": new_cases,
            "active_applications": active_apps,
            "completed": done_cases,
            "total_paid": total_paid,
            "by_status": by_status,
            "top_measures": [{"title": r["title"], "count": r["c"]} for r in top],
        }


# ---------- Static web ----------
@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))

if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
