# STATUS.md

日期：2026-10-05。任务：给 FitStack Macro Tracker 补测试和 CI，不加新功能。
分支：`fix/error-handling-and-nutrition-tests`（全部为本地提交，未 push）。

## 完成了什么

| 范围项 | 状态 | 说明 |
|---|---|---|
| 1. 拆分数据库读写与宏量计算 | ✅ | `src/database.py`（7 个数据访问函数，client 作参数注入）、`src/nutrition.py`（新增 `goal_progress`、`build_weekly_trend`），`src/app.py` 只剩缓存装饰、错误展示和 UI。用户界面行为不变 |
| 2. pytest 单元测试 | ✅ | 营养计算 15、目标追踪 7、7 天趋势聚合 8、数据库层（假 client）14 |
| 2. pytest 集成测试（真 PostgreSQL） | ✅ | 14 个，用仓库现有 `docx/schema.sql`（含 24 条 products 种子数据），经 `tests/postgres_client.py` 适配器跑生产同款函数 |
| 3. GitHub Actions | ✅ 已写 / ⚠️ 未验证 | `.github/workflows/ci.yml`：postgres:16 service container + 覆盖率报告（job summary + artifact）+ E2E。本机无法运行 Actions，语法已用 PyYAML 校验 |
| 4. Playwright E2E | ✅ | 3 条：记录一餐 → 日志列表与指标更新；宏量指标变成对应数值；7 天趋势图（目标参考线 + 当天刻度）。本机真实跑通（chromium headless，约 10 秒） |
| 5. Dockerfile + README Testing | ✅ 已写 / ⚠️ Docker 未验证 | `Dockerfile`（python:3.12-slim）+ `.dockerignore`；README 新增 Testing 一节和 Docker 小节 |

## 测试数量与覆盖率（改动前 → 改动后）

改动前（本机基线实测，`pytest tests/ --cov=src`）：

- 测试：**15 个**（全部是 nutrition 单元测试）
- 覆盖率：`src/app.py` 0%（189 语句）、`src/nutrition.py` 100%（21 语句）、**src/ 合计 10%**

改动后（本机实测）：

- 测试：**61 个** = 58（单元 + 集成）+ 3（E2E）
  - `tests/test_nutrition.py` 15
  - `tests/test_goal_progress.py` 7
  - `tests/test_weekly_trend.py` 8
  - `tests/test_database_unit.py` 14
  - `tests/test_database_integration.py` 14
  - `tests/e2e/test_app_flows.py` 3
- 覆盖率（58 个单元 + 集成测试，`--cov=src`）：`src/nutrition.py` 100%（37 语句）、`src/database.py` 100%（30 语句）、`src/app.py` 0%（169 语句，纯 Streamlit UI，见 DECISIONS.md 第 8 条）、**src/ 合计 28%**

## 真实结果表（全部为本机实际命令输出）

| 命令 | 结果 |
|---|---|
| `.venv/bin/python -m pytest tests --ignore=tests/e2e --cov=src --cov-report=term` | **58 passed in 1.29s**；nutrition.py 100% / database.py 100% / app.py 0% / 合计 28% |
| `PLAYWRIGHT_BROWSERS_PATH=$PWD/.playwright-browsers .venv/bin/python -m pytest tests/e2e --browser chromium` | **3 passed in 10.35s** |
| `.venv/bin/python -m pytest`（全部） | **61 passed in 11.09s** |
| pgserver 冒烟（启动内嵌 PG + 应用 schema） | PostgreSQL **16.2** (aarch64)，schema 应用成功，products=24、goals=1 |
| supabase-py 直连 E2E stub 探针 | 9 类操作（排序查询/limit/嵌套嵌入/eq/区间/插入/更新/插入目标/删除/幂等删除）全部成功 |
| `.github/workflows/ci.yml` YAML 解析 | 8 个 step、1 个 postgres service，解析通过（仅语法层面） |

环境：Python 3.12.14（Homebrew，本机已有）、macOS 15.1 arm64、`.venv`（项目内，已 gitignore）。

## 没完成什么 / 卡在哪里 / 未验证项

- **Docker build：未验证。** 本机没有 docker，规则禁止安装。Dockerfile 是按标准 python:3.12-slim 写的，但没有实际 build 过。
- **GitHub Actions：未验证。** 本机无法运行 GitHub Actions；workflow 语法已校验，逻辑与本地完全相同的测试命令（同一套 pytest 调用 + `DATABASE_URL` 指向 service container）。首次 push 后需要在 GitHub 上看第一次运行结果。
- **覆盖率总量 28% 的原因：** 不是漏测，而是 `src/app.py`（169 句，纯 UI）按设计不纳入单测；两个逻辑模块都是 100%。如需"好看的"总覆盖率可以排除 app.py，但那样就不是如实数字了。
- **Ollama / LLM：** 本任务范围（测试与 CI）不涉及任何 LLM 功能，因此不需要 Ollama，也没有安装。
- **数据下载：** 全部成功（pip 依赖、Playwright Chromium 143.x 到项目内 `.playwright-browsers/`，约 140MB，已 gitignore）。没有下载失败项，也没有使用任何假数据。
- **未触碰：** `.streamlit/secrets.toml`、`.env`、任何 Supabase 凭据、线上数据库 —— 按规则从未读取或连接。测试全部使用本地内嵌 PostgreSQL（pgserver）或内存 stub。

## 本地复现方式

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests --ignore=tests/e2e --cov=src --cov-report=term
PLAYWRIGHT_BROWSERS_PATH=$PWD/.playwright-browsers .venv/bin/playwright install chromium
.venv/bin/python -m pytest tests/e2e --browser chromium
```

集成测试优先用 `DATABASE_URL` 环境变量；没设置时自动用 pgserver（pip 包内嵌 PostgreSQL 16，仅本地开发用，CI 用 service container）。

## 提交记录（本地，未 push）

```
d7f0a62 refactor: extract data-access layer and pure nutrition logic from app
3d54599 test: unit tests for goal tracking, weekly trend and data-access layer
3488e62 test: integration tests for database layer against real PostgreSQL
1bd5c09 ci: run all tests with postgres service container and coverage report
e202591 test: Playwright E2E for record-meal, macro-update and trend flows
bd342ea docs+build: Dockerfile and README Testing section
（最后一条：文档与收尾，见 git log）
```

所有设计决定及理由见 `DECISIONS.md`；代码导读见 `walkthrough.md`。
