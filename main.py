from __future__ import annotations

import io
import os
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Request, status
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="Uploader service", version="1.0.0")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "images")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "20971520"))

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
    config=Config(signature_version="s3v4"),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "uploader"}


@app.post("/v1/upload", status_code=status.HTTP_201_CREATED)
async def upload(request: Request) -> dict[str, str | int]:
    raw = await request.body()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty request body")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file is too large")

    try:
        with Image.open(io.BytesIO(raw)) as source:
            source.verify()
        with Image.open(io.BytesIO(raw)) as source:
            image = source.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
            payload = output.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="uploaded data is not a supported image",
        ) from exc

    object_name = f"{uuid.uuid4()}.jpg"
    try:
        s3.put_object(
            Bucket=MINIO_BUCKET,
            Key=object_name,
            Body=payload,
            ContentType="image/jpeg",
            ContentLength=len(payload),
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="object storage is unavailable",
        ) from exc

    return {
        "object": object_name,
        "url": f"/images/{object_name}",
        "size": len(payload),
    }
