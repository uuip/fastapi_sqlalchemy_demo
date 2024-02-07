# dependency在不同位置的使用

## 对象
dependencies=[...]
这里需要列表内是对象，Depends(something)
## 类型
def update(db: DBDep)
函数定义中是类型标注，Annotated[User, Depends(get_current_user)]