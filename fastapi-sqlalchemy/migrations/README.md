## 生成 alembic 目录
```shell
alembic init migrations
```

## 编辑env.py

```python
from model import Base
from config import settings

# env.py 24行左右
target_metadata = Base.metadata
config.set_main_option('sqlalchemy.url', settings.db)

def load_module(paths: list, prefix=""):
    # 如果有多个模型目录或者模型定义与Base没有在一起，需要先导入模型使alembic发现。
    for module_finder, name, ispkg in pkgutil.walk_packages(paths, prefix):
        import_module(name)
        
# 可选启用        
# load_module(["model"], "model.")
```

## 生成模型变动
```shell
alembic revision --autogenerate
```

## 应用
```shell
alembic upgrade head
```