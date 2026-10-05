# walkthrough.md — FitStack 补测试与 CI：代码导读

写给你明早复习用。按**数据流**的顺序讲每个文件在做什么，最后是 8 个面试官最可能问的问题（附文件和行号）。
本次改动的全部设计决定和理由在 `DECISIONS.md`，完成情况与真实数字在 `STATUS.md`。

## 一句话总结

原项目是一个 Streamlit + Supabase 的宏量营养追踪器；这次把**数据访问**和**营养计算**从页面代码里拆成独立函数，然后围绕它们补齐了：单元测试（58）+ 真 PostgreSQL 集成测试 + Playwright E2E（3）+ GitHub Actions（postgres service container + 覆盖率）+ Dockerfile。**没有加任何新功能，界面行为不变。**

## 数据流总览

```
                ┌──────────────────────────── 运行时（生产） ───────────────────────────┐
                │                                                                      │
 docx/          │  src/app.py (Streamlit UI)                                           │
 schema.sql ────┼─▶  init_supabase() ── supabase client ──┐                             │
 (PostgreSQL    │      │ 缓存 @st.cache_data              │                             │
  建表+种子)     │      ▼                                  ▼                             │
                │  src/database.py（数据访问函数，client 作第一个参数）                    │
                │      fetch_foods / fetch_goals / fetch_todays_logs /                  │
                │      fetch_week_logs / add_food_log / delete_log / update_goals       │
                │      ▼                                                                │
                │  Supabase (REST/PostgREST) ─▶ PostgreSQL: products / daily_logs /     │
                │                                user_goals                             │
                │      ▼                                                                │
                │  src/nutrition.py（纯计算，无 IO）                                     │
                │      calc_nutrition → aggregate_nutrition/daily_totals →              │
                │      goal_progress → build_weekly_trend                               │
                │      ▼                                                                │
                │  app.py 渲染：4 个指标卡 / 今日日志 / 7 天趋势图                        │
                └──────────────────────────────────────────────────────────────────────┘

                ┌──────────────────────────── 测试（本地/CI） ──────────────────────────┐
                │  单元测试：假 client（tests/test_database_unit.py）直接喂 database.py  │
                │  集成测试：tests/postgres_client.py（psycopg 适配器，模拟 supabase    │
                │            查询接口）──▶ 真 PostgreSQL（本地 pgserver / CI container） │
                │  E2E：    tests/e2e/postgrest_stub.py（内存 PostgREST）◀── supabase-py │
                │           ◀── src/app.py（streamlit run 子进程）◀── Playwright 浏览器  │
                └──────────────────────────────────────────────────────────────────────┘
```

## 按数据流讲每个文件

### 1. `docx/schema.sql` — 数据的形状（没改）

三张表：`products`（每 100g 的营养数据）、`daily_logs`（每餐记录，`product_id` 外键 + `ON DELETE CASCADE`）、`user_goals`（每日目标，单行）。还有 24 条产品种子数据和 1 条默认目标。集成测试每个用例前会**重建这套 schema**（`tests/conftest.py:38`），所以测试永远对着仓库里真实的表结构跑。

### 2. `src/database.py` — 数据访问层（新文件，本次重构的核心）

7 个函数，每个都是原来 `app.py` 里内联的 supabase 调用，**一行查询逻辑都没变**，只是：
- **第一个参数是 `client`**（`src/database.py:25`）——生产时传 supabase client，测试时传假件或 psycopg 适配器。这就是依赖注入，是这个改动里最重要的一步：没有它，测试根本绕不开 Supabase 云服务。
- **不 import streamlit，出错就抛异常**——错误显示留在 app.py。这样这一层可以在普通 pytest 里跑，不需要启动 Streamlit。
- 读函数返回**原始数据**（list[dict]），转 DataFrame 的事交给 app.py。
- 业务校验也在这里：`add_food_log` 拒绝 qty≤0 和 qty>10000（`src/database.py:58`）；`update_goals` 是"有则更新、无则插入"的 upsert（`src/database.py:76`）；`DEFAULT_GOALS` 兜底（`src/database.py:14`）。

### 3. `src/nutrition.py` — 纯计算层（原有文件，扩充两个函数）

无 IO、无 UI，输入输出都是普通 dict/DataFrame：
- `calc_nutrition(food, amount)`（`src/nutrition.py:12`）：按 `amount/100` 缩放每 100g 营养值。
- `aggregate_nutrition(logs_df)`（`:21`）：把多行日志的营养值加总，自动跳过没有产品数据的行。
- `goal_progress(current, goal)`（`:45`，本次新增）：目标完成百分比，**封顶 100%**、目标非正数时返回 0——原来这段逻辑内联在 app.py 的指标卡里写了两遍条件。
- `build_weekly_trend(logs_df, end_date, days=7)`（`:52`，本次新增）：把日志按天分桶，**窗口内每天都有一行（缺数据的天补零）**，返回带 `date`（%m/%d）列的 DataFrame。原来这段是 app.py 图表区的一段 for 循环。

### 4. `src/app.py` — Streamlit UI（本次瘦身）

现在只负责三件事：
1. **连接与缓存**：`init_supabase()`（`src/app.py:53`）建 client；`_supabase_config()`（`:44`）先看环境变量再读 `st.secrets`——这是唯一的生产行为面改动（向后兼容：不设环境变量时行为与原来完全一致），目的是让 E2E 能把 app 指到本地 stub 而不碰 secrets.toml。Cache-Aside 在 `get_foods`（`:71`，TTL 300s）、`get_goals`（`:79`，TTL 60s）上，用 `@st.cache_data` 实现；`get_todays_logs`（`:87`）和 `get_week_data`（`:95`）**故意不缓存**，因为日志一天内会变。
2. **错误展示**：每个数据调用包 try/except，异常时 `st.error/st.warning` 并回退（空 DataFrame 或默认目标）——和重构前用户看到的完全一样。
3. **页面编排**：侧栏选日期/改目标（`:163` 调 `update_goals`，成功后 `get_goals.clear()` 再刷新）；四张指标卡用 `goal_progress`（`:195-213`）；"Add Log" 按钮调 `add_food_log`（`:256`）；日志列表带删除按钮（`:282`）；趋势图数据来自 `build_weekly_trend(week_data, today, 7)`（`:301`）。

### 5. `tests/test_nutrition.py`、`tests/test_goal_progress.py`、`tests/test_weekly_trend.py` — 单元测试（15+7+8）

第一个文件是项目里原有的（本次没动），后两个覆盖新拆出来的两个纯函数。值得看的是 `test_weekly_trend.py`：跨天分桶（`test_logs_land_on_their_own_day`）、窗口外的日志不计入（`test_log_outside_window_is_ignored`）、空数据也要产出 7 行零值（图表需要连续横轴）。

### 6. `tests/test_database_unit.py` + `FakeClient` — 数据层单元测试（14）

`FakeClient`（`tests/test_database_unit.py:22` 附近）用内存 dict 模拟 supabase 查询构造器（select/eq/gte/lte/order/limit/insert/update/delete），几十行。用来测**调用逻辑**：排序、日期过滤、数量校验不许碰库、upsert 两条路径。跑得极快（0.5s 内全部 58 个单元+集成测试的一部分）。

### 7. `tests/postgres_client.py` — psycopg 适配器（集成测试的关键）

问题：`src/database.py` 生产上走 supabase-py（HTTP/PostgREST），而本地和 CI 只有**普通 PostgreSQL**，supabase-py 连不上。解法：写一个 ~200 行的 `PostgresClient`，实现 database.py 用到的那一小撮接口，内部用 psycopg 翻译成 SQL：
- 嵌套查询 `select="*, products(name, ...)"` 用正则解析（`tests/postgres_client.py:27`），翻译成 `LEFT JOIN products p ON p.id = t.product_id`（`_FK_COLUMNS` 映射在 `:31`，join 在 `_execute_select`（`:150`）里拼装），再把产品列包成 `row["products"]` dict——和 PostgREST 返回的形状一致。
- `_jsonify`（`:43`）模拟 PostgREST 的 JSON 语义：`DECIMAL→float`、日期→ISO 字符串。
- **这是测试专用基础设施，生产代码不引用它**；好处是集成测试跑的是生产同款函数，测试结果真实可信。

### 8. `tests/conftest.py` + `tests/test_database_integration.py` — 集成测试（14）

`pg_dsn`（`tests/conftest.py:21`）解析连接：有 `DATABASE_URL` 用它（CI 的 service container），否则 `pgserver`（pip 包，内嵌 PostgreSQL 16，只装在 .venv 里）起本地库。`db` fixture（`:38`）每个测试前 DROP + 重建仓库 schema。14 个测试覆盖：排序读全量、DECIMAL→float、嵌套产品嵌入、日期区间**闭区间**边界、写入往返（123.45g）、校验拦截、删除、目标更新/插入两条路、外键级联删除、`log_date` 默认当天。

### 9. `tests/e2e/postgrest_stub.py` — 内存版 PostgREST（E2E 用）

E2E 要真的 `streamlit run`，而 app 只会说 supabase-py 的 HTTP 协议。这个文件用标准库 `http.server` 起一个线程内 HTTP 服务，实现 app 用到的全部端点：GET 查询（支持 `eq/gte/lte` 过滤、`order=name.asc`、`limit`、`products(...)` 嵌套）、POST 插入、PATCH 更新、DELETE 删除。数据放内存，`StubState.reset()`（`tests/e2e/postgrest_stub.py:64`）让每个测试从空日志开始。已用真 supabase-py 客户端对它做过 9 类操作探针，全部通过。

### 10. `tests/e2e/conftest.py` + `tests/e2e/test_app_flows.py` — Playwright E2E（3）

conftest 做两件事：起 stub（`:32`）、以子进程跑 `streamlit run src/app.py` 并用 `SUPABASE_URL` 环境变量把 app 指向 stub（`:47-55`），然后 Playwright 开无头 Chromium 访问。3 条测试对应要求的三个流程：
1. 记录一餐 → 日志列表出现该条 + 指标变化（`test_app_flows.py:37`）；
2. 宏量更新：100g 鸡胸肉 → 指标精确变为 165 kcal / 31.0g / 0.0g / 3.6g（`:50`）；
3. 趋势图：图表渲染、目标参考线 "Goal: 2500 kcal"、当天刻度 10/05 可见（`:67`）。
一个调试时发现的行为（与改动前一致）：app 在 `st.success()` 后立刻 `st.rerun()`，成功提示一闪而过，所以断言的是**持久状态**（列表/指标/图表），见 DECISIONS.md 第 10 条。

### 11. `.github/workflows/ci.yml` — CI

单 job：起 `postgres:16` service container（`:9`），`DATABASE_URL` 指向它（`:25`），先跑单元+集成测试并产出 coverage（`:39`），再装 chromium 跑 E2E（`:48`），覆盖率写入 job summary（`:50`）并上传 artifact（`:73`）。**本机无法验证 Actions，语法已校验，标"未验证"。**

### 12. `Dockerfile`

python:3.12-slim，装依赖、拷 `src/`，`streamlit run --server.address=0.0.0.0 --server.headless=true`。凭据用 `SUPABASE_URL/SUPABASE_KEY` 环境变量传入（`_supabase_config` 的顺带好处：容器里不用挂 secrets 文件）。**本机无 docker，未验证 build。**

## 面试官最可能问的 8 个问题

1. **"你为什么要把数据库代码从页面里拆出来？怎么保证行为没变？"**
   → `src/database.py:25`（client 作参数=依赖注入）；对照 `src/app.py:71-102`（缓存+错误展示留在 UI 层）。答：可测试性（测试可以注入替身，不用连 Supabase）；行为不变靠"查询逻辑逐行照搬 + 拆分前后全部测试通过 + E2E 走真实 UI 流程"。

2. **"Cache-Aside 是什么？为什么 daily_logs 不缓存？"**
   → `src/app.py:36-37`（两个 TTL）、`:71`/`:79`（缓存装饰器）、`:87`（注释"故意不缓存"）。答：读时先查缓存、miss 才查库，TTL 过期失效；产品/目标变化慢所以缓存，日志一天内多次变化所以不缓存，且 `update_goals` 成功后主动 `get_goals.clear()`（`src/app.py:164`）。

3. **"supabase-py 连不上普通 PostgreSQL，你的集成测试怎么连真库的？"**
   → `tests/postgres_client.py:27`（嵌套查询解析）、`:150`（`_execute_select` 拼 SQL）、`:43`（`_jsonify` 模拟 JSON 语义）。答：测试专用 psycopg 适配器实现同一小撮查询接口，生产函数零改动直接换客户端，测试跑的就是生产代码。

4. **"PostgREST 的嵌套查询 `*, products(...)` 你是怎么翻译成 SQL 的？"**
   → `tests/postgres_client.py:31`（`_FK_COLUMNS`）、`:173` 附近的 LEFT JOIN 拼装；表结构 `docx/schema.sql:24-27`（外键）。答：正则取出嵌入表和列 → 按外键 `product_id` LEFT JOIN → 产品列聚合成 `row["products"]` dict，无匹配为 null，和 PostgREST 返回形状一致。

5. **"7 天趋势图的数据是怎么聚合的？缺数据的天怎么办？"**
   → `src/nutrition.py:52-77`（`build_weekly_trend`）、调用点 `src/app.py:301`。答：从 end_date 往回逐天分桶，每天用 `aggregate_nutrition` 求和；**每天都产出一行、缺数据补零**，否则柱状图横轴会断；窗口外日期天然不匹配。测试见 `tests/test_weekly_trend.py`。

6. **"目标进度为什么要 cap 到 100%？为什么 goal≤0 特判？"**
   → `src/nutrition.py:45-49`；使用点 `src/app.py:195-213`。答：Streamlit 的 `st.progress` 只接受 0~1，超了会崩（原代码注释就写着这个坑）；goal≤0 时除零，返回 0 最合理。抽成纯函数后这两条规则第一次有了自己的测试（`tests/test_goal_progress.py`）。

7. **"E2E 为什么用 stub 而不是真数据库？怎么让 app 在测试里不读 secrets？"**
   → `src/app.py:44-49`（环境变量优先的 `_supabase_config`）、`tests/e2e/conftest.py:47-55`（子进程启动并把 URL 指向 stub）、`tests/e2e/postgrest_stub.py:71`（stub 的查询实现）。答：E2E 的职责是 UI 流程，数据库层已有真 Postgres 集成测试兜底；stub 让测试自包含、离线、可重复。环境变量优先是向后兼容的超集，正常用户无感知。

8. **"CI 怎么跑需要 PostgreSQL 的测试？覆盖率报告里 app.py 0% 怎么解释？"**
   → `.github/workflows/ci.yml:9-22`（postgres service container + 健康检查）、`:25`（DATABASE_URL）、`:50`（覆盖率进 job summary）。答：service container 起一个真 PG，集成测试用 `DATABASE_URL` 连它；本地则用 pgserver（pip 内嵌 PG），同一个 fixture 自动二选一（`tests/conftest.py:21`）。app.py 是纯 Streamlit UI，导入即执行页面代码，不适合单测，如实报 0%；业务逻辑两个模块都是 100%。

## 一分钟版本（背下来）

把 supabase 调用从 `app.py` 挪进 `database.py` 并让 client 变成参数（依赖注入），把两段内联的百分比/趋势逻辑抽成 `nutrition.py` 的纯函数；单元测试用假 client，集成测试用 psycopg 适配器把生产函数直接跑在真 PostgreSQL（仓库 schema）上，E2E 用内存 PostgREST stub 加 Playwright 走真实浏览器流程；CI 用 postgres service container 跑全套并报覆盖率。61 个测试全部通过，Docker 和 Actions 本机无法执行、如实标"未验证"。
