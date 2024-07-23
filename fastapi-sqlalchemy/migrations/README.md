## 生成 alembic 目录
```shell
alembic init migrations
```

## 编辑env.py

```python
from model import Base

target_metadata = Base.metadata

from config import settings

config.set_main_option('sqlalchemy.url', settings.db)
```

## 生成模型变动
```shell
alembic revision --autogenerate
```

## 应用
```shell
alembic upgrade head
```