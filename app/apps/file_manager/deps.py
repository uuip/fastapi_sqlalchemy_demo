from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.apps.file_manager.config import FileManagerConfig
from app.apps.file_manager.config import settings as file_manager_config
from app.apps.file_manager.security import FileSigner
from app.apps.file_manager.service import AsyncFileService
from app.apps.file_manager.storage import AsyncStorage, create_storage
from app.common.db import async_session_factory


@dataclass(frozen=True)
class FileManagerContext:
    storage: AsyncStorage
    service: AsyncFileService
    signer: FileSigner


def create_file_manager_context(*, config: FileManagerConfig = file_manager_config) -> FileManagerContext:
    if config.storage_type == "local":
        storage = create_storage(config.storage_type, root_path=config.storage_local_path)
    else:
        storage = create_storage(
            config.storage_type,
            bucket_name=config.s3_bucket_name,
            region=config.s3_region,
            endpoint_url=config.s3_endpoint,
            access_key=config.s3_access_key,
            secret_key=config.s3_secret_key,
            address_style=config.s3_address_style,
            use_iam=config.s3_use_iam,
        )
    signer = FileSigner(
        secret_key=config.secret_key,
        base_url=config.files_base_url,
        access_timeout=config.files_access_timeout,
    )
    service = AsyncFileService(
        storage=storage,
        session_factory=async_session_factory,
        storage_type=config.storage_type,
    )
    return FileManagerContext(storage=storage, service=service, signer=signer)


def get_file_manager_context(request: Request) -> FileManagerContext:
    return request.app.state.file_manager_context


type FileManagerDep = Annotated[FileManagerContext, Depends(get_file_manager_context)]


def get_file_service(context: FileManagerDep) -> AsyncFileService:
    return context.service


def get_file_signer(context: FileManagerDep) -> FileSigner:
    return context.signer


type FileServiceDep = Annotated[AsyncFileService, Depends(get_file_service)]
type FileSignerDep = Annotated[FileSigner, Depends(get_file_signer)]
