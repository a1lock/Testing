

### 1. `app/api/` — Внешний HTTP-интерфейс (FastAPI)

#### `routes/v1/` (Эндпоинты)
*   **`jobs.py`**: Содержит роутер для `/jobs`. 
    *   Функция `create_job()`: принимает `UploadFile`, валидирует (MIME, размер), сохраняет через `TempFileManager`, создает запись в БД, вызывает `validate_vkr.delay()` (отправка в Celery) и возвращает `job_id`.
    *   Функция `get_job_status()`: принимает `job_id`, отдает текущий статус из БД (`pending`, `processing`, `completed`, `failed`).
*   **`reports.py`**: Содержит роутер для `/reports`.
    *   Функция `get_report()`: отдает готовый JSON-отчет по `job_id` из таблицы `reports`.
*   **`profiles.py`**: Содержит роутер для `/profiles`.
    *   Функции `get_profiles()` и `update_profile()`: API для фронтенда (преподавателя) для просмотра и изменения настроек правил.
*   **`router.py`**: Единый `APIRouter`. Импортирует роутеры из `jobs.py`, `reports.py`, `profiles.py` и объединяет их под префиксом `/api/v1`.

#### `schemas/` (Pydantic-контракты)
*   **`job.py`**: Классы `JobCreateResponse` (содержит `job_id` и `status`) и `JobStatusResponse`.
*   **`report.py`**: Классы `ReportResponse`, `DocumentStatsSchema` и `ViolationSchema`. Жестко описывают структуру ответа для фронтенда.
*   **`profile.py`**: Классы `ProfileSchema`, `RuleConfigSchema` для валидации параметров при изменении настроек.

#### Корень `api/`
*   **`dependencies.py`**: Инъекции зависимостей. Функция `get_db()` (асинхронный генератор `AsyncSession` для работы с Postgres).

---

### 2. `app/core/` — Инфраструктура и настройки

*   **`config.py`**: Класс `Settings(BaseSettings)`. Описывает переменные окружения (`DATABASE_URL`, `REDIS_URL`, `GOTENBERG_URL`, `MAX_FILE_SIZE_MB`, `STORAGE_DIR`).
*   **`database.py`**: Настройка SQLAlchemy. Экземпляр `async_engine`, фабрика `async_sessionmaker`, базовый класс моделей `Base = declarative_base()`.
*   **`celery_app.py`**: Инициализация объекта `celery_app = Celery(...)`. Настройки брокера (Redis), сериализатора (json) и расписания (Celery Beat).
*   **`logging.py`**: Конфигурация стандартного модуля `logging` (или `structlog`) для вывода логов в формате JSON.

---

### 3. `app/domain/` — Бизнес-объекты (Без зависимостей от внешних либ)

#### `models/` (SQLAlchemy схемы)
*   **`job.py`**: Класс `Job`. Поля: `id` (UUID), `status` (Enum), `file_hash`, `error_message`, `created_at`.
*   **`report.py`**: Класс `Report`. Поля: `id`, `job_id` (Foreign Key), `is_valid`, `summary`, `violations` (JSONB).
*   **`profile.py`**: Класс `RuleProfile`. Поля: `id`, `name`, `is_default`, `rules_config` (JSONB — хранит параметры всех правил).

#### `dto/` (Data Transfer Objects — структуры в памяти)
*   **`document.py`**: Датаклассы `DocumentDTO`, `ParagraphDTO`, `TableDTO`, `ImageDTO`, `SectionDTO`. Хранят "слепок" документа в миллиметрах и строках, отвязанный от `python-docx`.
*   **`violation.py`**: Датаклассы `LocationDTO` (страница, абзац, сниппет текста) и `ViolationDTO` (id правила, уровень критичности, сообщение).
*   **`report.py`**: Датакласс `ReportDTO`. Объединяет всю статистику и массив `ViolationDTO` для передачи из движка правил в слой сервисов.

#### `dictionaries/`
*   **`anglicisms.json`**: Обычный JSON-файл. Словарь `{ "бэкенд": "серверная часть", ... }`.
*   **`homoglyphs.py`**: Функция `detect_mixed_scripts(word: str) -> bool`, проверяющая строку на смешивание Unicode-блоков кириллицы и базовой латиницы.

---

### 4. `app/adapters/` — Интеграции с внешним миром

#### `extractors/docx/`
*   **`document_parser.py`**: Класс `DocxExtractor`. Открывает файл через `python-docx`, циклом обходит секции, параграфы, таблицы и возвращает собранный `DocumentDTO`.
*   **`styles_xml.py`**: Функции `get_list_level(paragraph_xml)` и `get_style_hierarchy()`. Работают с `lxml.etree` для извлечения свойств списков, которых нет в публичном API `python-docx`.
*   **`app_props.py`**: Функция `extract_page_count(docx_zip_path)`. Парсит `docProps/app.xml` (через стандартный `zipfile` + `lxml`) и возвращает физическое количество страниц.

#### `extractors/pdf/`
*   **`layout_parser.py`**: Класс `PdfLayoutParser`. Принимает байты PDF, использует `fitz` (PyMuPDF). Извлекает тексты из нижнего колонтитула (координаты Y > 270 мм) для поиска номеров страниц. Возвращает обогащенные данные в `DocumentDTO`.

#### `converters/`
*   **`gotenberg.py`**: Класс `GotenbergClient`. Содержит метод `convert_to_pdf(docx_path)`. Отправляет HTTP `multipart/form-data` запрос в контейнер Gotenberg, обрабатывает ошибки `requests.exceptions.Timeout`.

#### `storage/`
*   **`local.py`**: Класс `TempFileManager`. Контекстный менеджер. В `__enter__` сохраняет загруженный файл в `/tmp`, в `__exit__` удаляет его (`os.remove()`).
*   **`cleaner.py`**: Функция `clean_old_files()`. Обходит папку хранилища и удаляет файлы старше 1 часа (защита от утечек).

---

### 5. `app/rule_engine/` — Паттерн Стратегия

*   **`base.py`**: Класс `BaseRule` (абстрактный класс с методом `check` и свойством `rule_id`).
*   **`registry.py`**: Словарь `RULE_REGISTRY` и функция-декоратор `@register_rule("ID")`.
*   **`engine.py`**: Класс `RuleEngine`. Инициализируется массивом включенных правил, запускает их цикл, собирает все `ViolationDTO` и возвращает `ReportDTO`.

#### `rules/` (Реализация 39 пунктов из документа)
*   **`structure/`**
    *   `required_sections.py`: Ищет Введение, Аннотацию, Заключение (п. 8, 12, 14).
    *   `chapters_count.py`: Считает главы (минимум 3) и ищет слово "Выводы" (п. 13).
    *   `toc_matching.py`: Сверяет оглавление с текстом, ищет запрещенные строки (п. 9, 10, 11).
*   **`typography/`**
    *   `margins.py`: Проверка 30/15/20/20 мм (п. 24).
    *   `fonts_and_sizes.py`: Проверка Times New Roman, 14/12 пт (п. 25, 21).
    *   `indents_intervals.py`: Проверка абзацев 1.25 см, интервалов 1.5 и 15 мм (п. 25, 30, 31).
    *   `headings_format.py`: Проверка КАПСА, выравнивания, полужирности для 1-го и 2-го уровней (п. 29, 32-34).
*   **`objects/`**
    *   `tables.py`: Проверка формата "Таблица 1 – Название" и интервала 1.0 (п. 21).
    *   `illustrations.py`: Сквозная нумерация, наличие ссылок в тексте (п. 20).
    *   `listings.py`: Поиск "Листинг X.X", проверка моноширинности кода, отсутствие картинок (п. 22).
*   **`bibliography/`**
    *   `sources_count.py`: Проверка на $\ge 50$ штук и $\ge 5\%$ латиницы (п. 15).
    *   `electronic_resources.py`: Проверка на $\le 50\%$ URL и дату обращения (п. 16).
    *   `cross_references.py`: Парсинг `[1]`, проверка кавычек для цитат, валидность индексов (п. 18).
*   **`text_quality/`**
    *   `homoglyphs_check.py`: Вызывает функцию из словаря `homoglyphs.py` (п. 26).
    *   `anglicisms_check.py`: Ищет слова из `anglicisms.json` (п. 7).
    *   `lists_format.py`: Ищет `w:ilvl > 0` (запрет многоуровневых списков, п. 28).

---

### 6. `app/services/` — Бизнес-Оркестрация

*   **`job_service.py`**: Класс `JobService`. Методы `create_job()`, `update_job_status()`, `fail_job()`. Выполняет транзакции в Postgres.
*   **`profile_service.py`**: Класс `ProfileService`. Читает YAML при старте, сохраняет профиль в БД `get_active_profile()`.
*   **`validation_pipeline.py`**: Класс `ValidationPipeline`. Выполняет строгий сценарий: `DocxExtractor` $\rightarrow$ `GotenbergClient` (опционально) $\rightarrow$ `PdfLayoutParser` $\rightarrow$ `RuleEngine` $\rightarrow$ `job_service.save_report()`.

---

### 7. `app/worker/` — Фоновые задачи Celery

*   **`tasks.py`**: Содержит функцию `@celery_app.task` с именем `validate_vkr`. Внутри функции инстанцируется `ValidationPipeline` и вызывается его метод `execute()`. Обрабатывает `Exception` и пишет Traceback в логи, переводя задачу в статус `failed`.
*   **`scheduled.py`**: Содержит периодическую задачу `@celery_app.task` с именем `clean_orphaned_files`, вызывающую `clean_old_files()` из слоя хранения.

---

### 8. Ресурсы, Тесты и Инфраструктура (Корень)

*   **`resources/rule_presets/gost_7_32_2017.yaml`**: Дефолтные настройки для общего ГОСТа.
*   **`resources/rule_presets/department_vkr_2025.yaml`**: Настройки для кафедры (отступ 12.5, источников 50 и т.д.).
*   **`tests/fixtures/valid_vkr.docx` / `broken_margins.docx` / `fake_homoglyphs.docx`**: Физические `.docx` файлы, на которых гоняются автотесты.
*   **`tests/unit/`**: Папка с тестами для проверки бизнес-логики (например, `test_homoglyphs.py`, `test_margins_rule.py`). Не используют БД.
*   **`tests/integration/`**: Папка с тестами эндпоинтов FastAPI (через `TestClient`) и полного прогона `ValidationPipeline`.
*   **`docker-compose.yml`**: Манифест развертывания. Содержит сервисы: `api`, `worker`, `db` (Postgres), `redis`, `gotenberg`.
*   **`Dockerfile`**: Многоэтапная сборка. Устанавливает зависимости из `pyproject.toml`, копирует код, запускает Uvicorn или Celery (в зависимости от CMD).
*   **`pyproject.toml`**: Файл зависимостей (Poetry/Pip). Указаны `fastapi`, `sqlalchemy`, `celery`, `redis`, `python-docx`, `lxml`, `pymupdf`, `pytest`.

