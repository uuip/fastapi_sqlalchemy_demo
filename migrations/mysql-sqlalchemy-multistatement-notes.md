# Alembic 中 MySQL 多语句 SQL 注意点

MySQL 开启 `CLIENT.MULTI_STATEMENTS` 后，允许一次 `cursor.execute()` 发送多条 SQL。
在 Alembic migration 中，不要用 `op.execute()` 执行分号拼接的 MySQL 多语句 SQL：

```python
op.execute("""
INSERT INTO t1 VALUES (...);
BROKEN SQL;
""")
```

原因：MySQL + PyMySQL 多语句会返回多个 result set，Alembic 的 `op.execute()` 底层不会主动遍历后续 result set。后续语句的错误可能不会在当前 `op.execute()` 里立即抛出，而是在连接清理或下次使用连接时才暴露。
推荐拆成单条执行：

```python
for stmt in stmts:
    op.execute(stmt)
```

如果必须一次执行 MySQL 多语句，使用原生 PyMySQL cursor，并放在 `with` 语句里：

```python
with op.get_bind().connection.cursor() as cursor:
    cursor.execute(sql)
```

原因：PyMySQL cursor 退出 `with` 时会调用 `close()`，`close()` 内部会排空剩余 result set。后续语句的错误会在这个清理过程中暴露。
使用 ORM `Session` 时，`session.flush()` 发出的是单语句执行单元或 `executemany` / batching，不是分号拼接的 MySQL 多语句 SQL：

```python
SessionMaker = sessionmaker(bind=op.get_bind())

with SessionMaker() as session:
    session.add(obj)
    session.flush()
```

这类 migration 能正常暴露错误的根因不是 `flush()` 有特殊清理能力，而是没有执行分号拼接的 MySQL 多语句 SQL。`flush()` 只是触发 ORM 发 SQL，并用于获取自增主键、提前暴露约束错误。
PostgreSQL + psycopg 不受这个问题影响，因为 psycopg 会在 `execute()` 内部完整处理多语句执行过程，后续语句错误会立即抛出。
