# DECISIONS.md

按时间顺序记录本次"补测试和 CI"工作中的每个决定与理由。规则：选最简单、最容易解释的方案。

## 1. 虚拟环境用 Homebrew Python 3.12（本机已有）

系统默认 `python3` 是 3.14（Framework 安装），部分依赖生态对 3.14 支持还不稳；本机已有 Homebrew 的 `python@3.12`，Streamlit 1.52 / Supabase / pandas 2.3 全部官方支持 3.12。
本机残留过一个指向 3.14 的旧 `.venv`（lib 下同时有 python3.12 和 python3.14 两套目录），已删除并用 3.12 重建。`.venv` 在 `.gitignore` 里，不属于仓库内容。

## 2. 本地集成测试用 pgserver（pip 包）提供真 PostgreSQL

本机没有 psql，也没有 Docker，且规则禁止 brew/Docker Desktop 这类系统级安装。
选了 `pgserver`（pip 包，内嵌 PostgreSQL 16.2 二进制，只装进项目 `.venv`），实测能启动并跑通 `docx/schema.sql`（24 products / 1 goal）。
CI 里不用它：CI 按要求用 GitHub Actions 的 postgres service container，本地导出 `DATABASE_URL` 时 pgserver 自动让位（见 conftest 设计）。

## 3. 重构方向：`src/database.py` 承载数据访问，client 作为参数注入

`src/app.py` 里 7 个直接调 `supabase.table(...)` 的函数（get_foods / get_goals / get_todays_logs / get_week_data / add_food_log / delete_log / update_goals）抽到 `src/database.py`，全部改成第一个参数接收 `client`。
理由：
- Supabase-py 走 REST，本机起不了真 Supabase；把 client 变成参数后，测试可以注入同接口的替身（真 Postgres 适配器或内存假件），生产行为完全不变。
- Streamlit 专属的东西留在 app.py：`@st.cache_data` 缓存装饰、`st.error/st.warning` 错误展示。database.py 不 import streamlit，错误一律抛异常，由 app.py 的调用点 try/except 后展示——和重构前"界面显示 error 文案 + 返回空数据"的可见行为一致。
- `get_week_data` 里的日期区间计算（今天往前推 6 天）属于业务逻辑，移出：`fetch_week_logs(client, start_date, end_date)` 接收显式日期，app.py 负责算"今天"。

## 4. 纯计算函数继续放 `src/nutrition.py`

- 目标追踪的百分比逻辑（`min(intake/goal*100, 100)`，goal<=0 时为 0）从 app.py 四个指标卡里抽出为 `goal_progress(current, goal)`。
- 7 天趋势聚合的 for 循环抽出为 `build_weekly_trend(logs_df, end_date, days=7)`，返回带 `date` 列（%m/%d）的 DataFrame，行为与原内联循环逐行等价。
- 都是无 UI 依赖的纯函数，单元测试直接覆盖。

## 5. 集成测试通过一个测试专用的 Postgres 适配器

`src/database.py` 的函数只会用到 Supabase 查询构造器的一小撮能力（select/order/limit/eq/gte/lte/insert/update/delete + 两种固定形态的嵌套查询 `*, products(...)`）。
集成测试在 `tests/postgres_client.py` 里实现一个约百行的 `PostgresClient`，用 psycopg 连真 PostgreSQL（pgserver 或 CI 的 service container），模拟这一小撮接口，包括把 `products(...)` 嵌套查询翻译成 LEFT JOIN、把 DECIMAL 转成 float（模拟 PostgREST 返回 JSON 数字的行为）。
理由：这样集成测试跑的是**生产同款函数**（src/database.py），而不是另一套只为测试写的 SQL。适配器只在 tests/ 里，生产代码不引用。

## 6. `init_supabase` 支持环境变量覆盖（仅为可测性）

Streamlit 1.52 的 `st.secrets` 只读 secrets.toml，没有环境变量回退；E2E 不能碰 `secrets.toml`，也不能连线上库。
改动：`init_supabase` 先看 `SUPABASE_URL`/`SUPABASE_KEY` 环境变量，没有才读 `st.secrets`。用户平时（无这两个环境变量）运行行为完全不变；E2E 把它指到本地 stub 服务。这是唯一的生产行为面改动，且是向后兼容的超集。

## 7. E2E 用进程内 PostgREST 风格 stub（内存数据）

Playwright E2E 需要 `streamlit run` 真跑起来。supabase-py 只会说 REST（PostgREST 协议），本机起不了真 Supabase。
方案：`tests/e2e/postgrest_stub.py` 用标准库 `http.server` 起一个线程内 HTTP 服务，实现 app 用到的那几个端点（products/goals/daily_logs 的查询、插入、更新、删除），数据放内存。
理由：E2E 的职责是验证 UI 流程（记录一餐 → 宏量更新 → 趋势图），数据库层已有真 Postgres 集成测试兜底；stub 让 E2E 自包含、不依赖 Docker/外网。

## 8. 覆盖率如实上报，app.py（纯 UI）不硬凑覆盖率

`app.py` 是 Streamlit 页面脚本，导入即执行 UI 代码，不纳入单测；覆盖率报告会显示它 0%。这是如实数字，不为好看而排除或造假。业务逻辑全部位于 `src/nutrition.py` 和 `src/database.py`，这两个文件要求高覆盖。

## 9. Playwright 浏览器装进项目目录（`.playwright-browsers/`）

规则要求只在本文件夹内工作。Playwright 默认把 Chromium 装到 `~/Library/Caches/ms-playwright`（文件夹之外），所以本地安装时用 `PLAYWRIGHT_BROWSERS_PATH=$PWD/.playwright-browsers` 重定向，并加进 `.gitignore`。E2E 的 conftest 只在该目录存在时才设置这个环境变量，CI 里仍用默认缓存位置。这不是系统级安装：只是项目目录里的一组浏览器二进制文件。

## 10. E2E 断言"持久状态"，不断言一闪而过的提示

App 在 `st.success()` 之后立刻 `st.rerun()`，成功提示实际上不会停留在页面上（重构前后行为一致）。所以 E2E 的"记录一餐"测试断言的是持久证据：Today's Logs 里出现该条目 + 顶部宏量指标变为对应数值。E2E 里发现的这个行为与重构前代码完全相同，没有为测试去改 app 的行为。

## 11. 文档里的每个数字都来自真实命令输出

README/STATUS 里的测试数量和覆盖率直接取自本地最后一次运行的 pytest 输出（58 + 3 通过；nutrition.py 100%、database.py 100%、app.py 0%、src/ 合计 28%）。Docker build 和 GitHub Actions 在本机无法执行，一律标"未验证"，不写任何想象的数字。
