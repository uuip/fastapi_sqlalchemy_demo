## 生成 alembic 目录

```shell
alembic init migrations
```

## 编辑env.py

下面是示例片段（用于说明思路；其中 `config`/`pkgutil`/`import_module`/`op`/`sql` 等符号需要你按实际文件上下文自行补全导入或变量）。

```python
# 示例（伪代码/片段）：
import pkgutil
from importlib import import_module
from fastapi_sqlalchemy.model import Base
from fastapi_sqlalchemy.config import settings

# env.py 24 行左右
target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.db_url)


def load_module(paths: list, prefix=""):
    # 如果有多个模型目录或者模型定义与 Base 没有在一起，需要先导入模型使 alembic 发现。
    for module_finder, name, ispkg in pkgutil.walk_packages(paths, prefix):
        print(name)
        import_module(name)


load_module(["fastapi_sqlalchemy"], "fastapi_sqlalchemy.")
```

## 生成模型变动

```shell
alembic revision --autogenerate
```

## 应用

```shell
alembic upgrade head
```

## alembic 执行SQL

```python
# 示例（在 alembic migration 脚本里）：
# 这一条适用mysql, mysql+sqlalchemy的组合里,若不这么执行raw sql错误要在commit时抛出
with op.get_bind().connection.cursor() as cursor:
    cursor.execute(sql)
# 常规写法
# op.get_bind().exec_driver_sql(sql)
```