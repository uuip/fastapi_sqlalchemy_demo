from .base import AsyncStorage
from .enums import StorageType


def create_storage(storage_type: StorageType | str, **config) -> AsyncStorage:
    st = StorageType(storage_type)

    match st:
        case StorageType.LOCAL:
            from .opendal_storage import AsyncOpenDALStorage

            return AsyncOpenDALStorage(scheme="fs", root=config.get("root_path", "storage"))
        case StorageType.S3:
            from .s3_storage import AsyncS3Storage

            return AsyncS3Storage(**config)
        case _:
            raise ValueError(f"Unsupported storage type: {storage_type}")
