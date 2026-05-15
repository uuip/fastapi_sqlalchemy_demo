# FastAPI 示例

* token认证<br> [deps.py](app/apps/accounts/deps.py), [services/auth.py](app/apps/accounts/services/auth.py)
* 分页<br> [deps/pagination/](app/common/deps/pagination)
* SQLAlchemy集成<br> [db.py](app/common/db.py), [deps/db.py](app/common/deps/db.py)
* 业务服务层<br> [services/](app/apps/accounts/services)
* response_model<br> [response.py](app/common/schemas/response.py)
* Pydantic序列化示例<br> [schemas/account.py](app/apps/accounts/schemas/account.py)
* .env支持<br> [config.py](app/common/config.py)
* migrations<br> [README.md](migrations/README.md)
* 单元测试 / 集成测试<br> common/main 测试在 [tests/](tests/)，app 专属测试在各 app 的 `tests/`，例如 [accounts/tests](app/apps/accounts/tests), [examples/tests](app/apps/examples/tests), [file_manager/tests](app/apps/file_manager/tests)
