# Python 包布局与 FastAPI 应用布局

## 一、包布局

包布局适用于需要构建、安装或发布的 Python distribution package。

### 1. Src layout（推荐）

```
my-package/
├── pyproject.toml
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── module_a.py
│       └── data/
│           └── resource.txt
└── tests/
```

- 源码放在 `src/` 下，多一层隔离
- 防止开发时意外 import 未安装的本地代码（`python -c "import my_package"` 在未安装时会失败，而 flat layout 会成功）
- **uv 默认使用此布局**：`uv init --package` 生成的就是 src layout，`uv build-backend` 的 `module-root` 默认值为 `"src"`

### 2. Flat layout（次要）

```
my-package/
├── pyproject.toml
├── my_package/
│   ├── __init__.py
│   ├── module_a.py
│   └── data/
│       └── resource.txt
└── tests/
```

- 包目录与 `pyproject.toml` 同级
- 结构简单，但隔离性弱于 src layout
- uv 支持这种布局，但需显式配置：

```toml
[tool.uv.build-backend]
module-root = ""
```

---

## 二、应用布局

应用布局适用于只运行服务、不发布为 Python distribution package 的项目。本项目的 `[tool.uv] package = false` 就是这种定位。

### 1. 保留应用包目录（推荐）

```
fastapi-project/
├── pyproject.toml
├── alembic.ini
├── migrations/
├── tests/
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── api/
    ├── core/
    ├── deps/
    ├── models/
    ├── schemas/
    └── services/
```

- 顶层目录（本项目用 `app/`）是 import package，不代表项目要发布为 distribution package
- 导入路径清晰：`from app.config import settings`
- 启动路径清晰：`app.main:app`
- FastAPI 应用常用目录名：`app/`、`backend/` 或项目名

### 2. 无包应用布局

也可以把 `app/` 的内容上提一层：

```
fastapi-project/
├── pyproject.toml
├── alembic.ini
├── main.py
├── config.py
├── api/
├── core/
├── deps/
├── models/
├── schemas/
├── services/
├── migrations/
└── tests/
```

这种结构可称为 **flat application layout**。

它不是包布局里的 flat layout；这里没有顶层 import package，模块直接放在项目根目录。若采用此结构，需要同步调整：

- `app.main:app` → `main:app`
- `from app.config import settings` → `from config import settings`
- Alembic、Dockerfile、测试、迁移脚本里的导入路径

这种布局适合小型应用；本项目更适合保留应用包目录。
