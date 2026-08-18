from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterator
from urllib.parse import quote


class ObjectStorageError(RuntimeError):
    pass


class LocalObjectStorage:
    kind = "local"

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, locator: str) -> Path:
        raw = str(locator)
        if raw.startswith("local://"):
            raw = raw[len("local://"):]
        path = (self.root / raw).resolve()
        if path != self.root and self.root not in path.parents:
            raise ObjectStorageError("Đường dẫn storage không hợp lệ.")
        return path

    def put_bytes(self, key: str, content: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return "local://" + str(path.relative_to(self.root)).replace("\\", "/")

    def read_bytes(self, locator: str) -> bytes:
        return self._path(locator).read_bytes()

    def exists(self, locator: str) -> bool:
        return self._path(locator).is_file()

    def delete(self, locator: str) -> None:
        self._path(locator).unlink(missing_ok=True)

    def signed_download_url(self, locator: str, *, filename: str = "download", as_attachment: bool = True) -> str | None:
        return None

    @contextmanager
    def materialize(self, locator: str, suffix: str = "") -> Iterator[Path]:
        yield self._path(locator)


class R2ObjectStorage:
    kind = "r2"

    def __init__(self, *, bucket: str, client: Any, presign_ttl: int = 600):
        self.bucket = str(bucket)
        self.client = client
        self.presign_ttl = max(60, min(int(presign_ttl), 3600))

    @staticmethod
    def _key(locator: str) -> str:
        raw = str(locator)
        return raw[len("r2://"):] if raw.startswith("r2://") else raw

    def put_bytes(self, key: str, content: bytes, content_type: str) -> str:
        clean_key = str(key).lstrip("/")
        self.client.put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
        return f"r2://{clean_key}"

    def read_bytes(self, locator: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(locator))
        return response["Body"].read()

    def exists(self, locator: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(locator))
            return True
        except Exception:
            return False

    def delete(self, locator: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(locator))

    def signed_download_url(self, locator: str, *, filename: str = "download", as_attachment: bool = True) -> str:
        disposition_type = "attachment" if as_attachment else "inline"
        disposition = f"{disposition_type}; filename*=UTF-8''{quote(str(filename))}"
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": self._key(locator),
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=self.presign_ttl,
        )

    @contextmanager
    def materialize(self, locator: str, suffix: str = "") -> Iterator[Path]:
        temp = NamedTemporaryFile(delete=False, suffix=suffix)
        path = Path(temp.name)
        try:
            temp.write(self.read_bytes(locator))
            temp.close()
            yield path
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def storage_from_env(local_root: str | Path):
    bucket = str(os.getenv("R2_BUCKET", "") or "").strip()
    account_id = str(os.getenv("R2_ACCOUNT_ID", "") or "").strip()
    access_key = str(os.getenv("R2_ACCESS_KEY_ID", "") or "").strip()
    secret_key = str(os.getenv("R2_SECRET_ACCESS_KEY", "") or "").strip()
    if not all((bucket, account_id, access_key, secret_key)):
        if str(os.getenv("REQUIRE_R2_STORAGE", "false")).lower() in {"1", "true", "yes"}:
            raise RuntimeError("Production yêu cầu Cloudflare R2 nhưng thông tin R2 chưa đầy đủ.")
        return LocalObjectStorage(local_root)
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("R2 đã được cấu hình nhưng chưa cài boto3.") from exc
    client = boto3.client(
        service_name="s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return R2ObjectStorage(
        bucket=bucket,
        client=client,
        presign_ttl=int(os.getenv("R2_PRESIGN_TTL", "600")),
    )
