import uuid
from typing import Optional

import httpx

from ..config import settings


async def upload_to_r2(video_url: str, file_key: Optional[str] = None) -> str:
    if not all([settings.r2_access_key_id, settings.r2_secret_access_key, settings.r2_bucket, settings.r2_endpoint]):
        return video_url

    try:
        import boto3

        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.get(video_url)
            resp.raise_for_status()
            video_bytes = resp.content

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
        )

        key = file_key or f"renders/{uuid.uuid4()}.mp4"
        content_type = "video/mp4"

        s3.put_object(
            Bucket=settings.r2_bucket,
            Key=key,
            Body=video_bytes,
            ContentType=content_type,
            ACL="public-read",
        )

        return f"{settings.r2_endpoint.rstrip('/')}/{settings.r2_bucket}/{key}"
    except ImportError:
        return video_url
    except Exception:
        return video_url
