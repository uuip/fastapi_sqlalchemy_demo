## 生成 alembic 目录

```shell
alembic init migrations
```

## 编辑 env.py

下面是本项目 `migrations/env.py` 中关键片段的对照说明（实际代码以仓库内 `env.py` 为准）。

```python
# migrations/env.py 关键片段
import pkgutil
from importlib import import_module

from app.config import settings
from app.models import Base
from migrations.ensure_db import ensure_sync_driver

# autogenerate 需要的元数据
target_metadata = Base.metadata

# alembic 使用 % 插值，% 需要转义
db_url = ensure_sync_driver(settings.db_url).replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url)


def load_module(paths: list, prefix=""):
    # 模型分散在 app/models 子模块时，需要逐个 import 触发注册到 Base.metadata
    for module_finder, name, ispkg in pkgutil.walk_packages(paths, prefix):
        import_module(name)


load_module(["app/models"], "app.models.")
```

## 生成模型变动

```shell
alembic revision --autogenerate
```

## 应用

```shell
alembic upgrade head
```
