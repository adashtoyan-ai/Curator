# КУРАТОР — демонстрационный прототип

Рабочий вертикальный срез сквозного сценария MVP:
**вход по SMS → категории → создание кейса → анкета → подбор мер (Rule Engine) → объяснение →
подача заявки → кабинет координатора видит заявку.**

Модульный монолит на FastAPI + SQLite (запускается без внешней инфраструктуры).

## Запуск

```bash
cd curator-demo
python3 -m pip install -r requirements.txt --break-system-packages   # один раз
python3 -m uvicorn app.main:app --reload --port 8000
```

Открыть в браузере: http://localhost:8000

Демо-код SMS — **1234** (любой телефон). Координатор — кнопка «Войти как координатор (демо)».

## Структура

```
curator-demo/
├── app/
│   ├── main.py         # FastAPI: роутеры модулей (Auth, Users, Projects,
│   │                   #   Questionnaire, Rule Engine, Applications, Coordinator)
│   ├── rule_engine.py  # движок подбора: eligibility → Score → Explainability
│   ├── db.py           # SQLite-хранилище (схема из модели данных)
│   └── seed.py         # демо-меры поддержки Краснодарского края + категории
└── web/index.html      # одностраничный интерфейс сквозного сценария
```

## Важно

Суммы и условия мер в `seed.py` — **демонстрационные** (примерные), для показа механики.
Перед пилотом администратор заменяет их актуальными данными Краснодарского края.

Соответствует спецификациям: `MVP_Data_Model_v1.md`, `Rule_Engine_MVP_v1.md`,
`MVP_API_Contracts_v1.md`, `MVP_User_Flows_v1.md`.
