import logging
from collections.abc import AsyncIterator
from typing import Any

import aiofiles
from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from .base import AsyncStorage

logger = logging.getLogger(__name__)
_MULTIPART_CHUNK_SIZE = 5 * 1024 * 1024


def _client_error_code(ex: ClientError) -> str:
    return str(ex.response.get("Error", {}).get("Code", ""))


def _is_not_found_error(ex: ClientError) -> bool:
    return _client_error_code(ex) in {"404", "NoSuchKey", "NotFound"}


async def _iter_multipart_chunks(chunks: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    buffer = bytearray()
    async for chunk in chunks:
        if not chunk:
            continue
        offset = 0
        while offset < len(chunk):
            available = _MULTIPART_CHUNK_SIZE - len(buffer)
            buffer.extend(chunk[offset : offset + available])
            offset += available
            if len(buffer) == _MULTIPART_CHUNK_SIZE:
                yield bytes(buffer)
                buffer.clear()
    if buffer:
        yield bytes(buffer)


class AsyncS3Storage(AsyncStorage):
    def __init__(
        self,
        *,
        bucket_name: str,
        region: str = "",
        endpoint_url: str | None = None,
        access_key: str = "",
        secret_key: str = "",
        address_style: str = "auto",
        use_iam: bool = False,
    ):
        self.bucket_name = bucket_name
        self._bucket_checked = False
        self._session = get_session()
        self._client_kwargs: dict[str, Any] = {"service_name": "s3", "region_name": region}

        if not use_iam:
            self._client_kwargs.update(
                aws_secret_access_key=secret_key,
                aws_access_key_id=access_key,
                endpoint_url=endpoint_url,
                config=AioConfig(s3={"addressing_style": address_style}),
            )

    def _client(self):
        return self._session.create_client(**self._client_kwargs)

    async def ensure_bucket(self) -> None:
        if self._bucket_checked:
            return
        async with self._client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket_name)
                self._bucket_checked = True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code == "404":
                    await client.create_bucket(Bucket=self.bucket_name)
                    self._bucket_checked = True
                elif code == "403":
                    self._bucket_checked = True
                else:
                    raise

    async def save(self, filename: str, data: bytes) -> None:
        await self.ensure_bucket()
        async with self._client() as client:
            await client.put_object(Bucket=self.bucket_name, Key=filename, Body=data)

    async def save_stream(self, filename: str, chunks: AsyncIterator[bytes]) -> None:
        await self.ensure_bucket()
        async with self._client() as client:
            upload_id: str | None = None
            parts: list[dict[str, Any]] = []
            part_number = 1
            try:
                part_iter = _iter_multipart_chunks(chunks)
                first_part = await anext(part_iter, b"")
                second_part = await anext(part_iter, b"")
                if not second_part:
                    await client.put_object(Bucket=self.bucket_name, Key=filename, Body=first_part)
                    return

                for part in (first_part, second_part):
                    if upload_id is None:
                        response = await client.create_multipart_upload(Bucket=self.bucket_name, Key=filename)
                        upload_id = response["UploadId"]
                    response = await client.upload_part(
                        Bucket=self.bucket_name,
                        Key=filename,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=part,
                    )
                    parts.append({"ETag": response["ETag"], "PartNumber": part_number})
                    part_number += 1

                async for part in part_iter:
                    response = await client.upload_part(
                        Bucket=self.bucket_name,
                        Key=filename,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=part,
                    )
                    parts.append({"ETag": response["ETag"], "PartNumber": part_number})
                    part_number += 1
                await client.complete_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=filename,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except Exception:
                if upload_id is not None:
                    await client.abort_multipart_upload(Bucket=self.bucket_name, Key=filename, UploadId=upload_id)
                raise

    async def load_once(self, filename: str) -> bytes:
        await self.ensure_bucket()
        try:
            async with self._client() as client:
                response = await client.get_object(Bucket=self.bucket_name, Key=filename)
                async with response["Body"] as stream:
                    return await stream.read()
        except ClientError as ex:
            if _is_not_found_error(ex):
                raise FileNotFoundError(f"File not found: {filename}") from ex
            raise

    async def load_stream(self, filename: str) -> AsyncIterator[bytes]:
        await self.ensure_bucket()
        try:
            async with self._client() as client:
                response = await client.get_object(Bucket=self.bucket_name, Key=filename)
                body = response["Body"]
                async with body:
                    async for chunk in body.iter_chunks(4096):
                        yield chunk
        except ClientError as ex:
            if _is_not_found_error(ex):
                raise FileNotFoundError(f"File not found: {filename}") from ex
            raise

    async def download(self, filename: str, target_filepath: str) -> None:
        async with aiofiles.open(target_filepath, "wb") as f:
            async for chunk in self.load_stream(filename):
                await f.write(chunk)

    async def exists(self, filename: str) -> bool:
        await self.ensure_bucket()
        try:
            async with self._client() as client:
                await client.head_object(Bucket=self.bucket_name, Key=filename)
            return True
        except ClientError as ex:
            if _is_not_found_error(ex):
                return False
            raise

    async def delete(self, filename: str) -> None:
        await self.ensure_bucket()
        async with self._client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=filename)

    async def scan(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        raise NotImplementedError("This storage backend doesn't support scanning")
