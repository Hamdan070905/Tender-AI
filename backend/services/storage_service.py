import boto3
from backend.core.config import settings

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin'
        )
        self.bucket_name = "tenderai-documents"

    def upload_file(self, file_bytes: bytes, filename: str) -> str:
        self.s3_client.put_object(Bucket=self.bucket_name, Key=filename, Body=file_bytes)
        return f"{settings.MINIO_ENDPOINT}/{self.bucket_name}/{filename}"

    async def extract_and_store_zip(self, zip_url: str, tender_id: str) -> list[str]:
        import httpx
        import zipfile
        import io
        import uuid
        
        uploaded_urls = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(zip_url, timeout=30.0)
                if resp.status_code != 200:
                    return []
                
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    for filename in z.namelist():
                        if filename.endswith('/') or filename.startswith('__MACOSX'):
                            continue
                        file_bytes = z.read(filename)
                        safe_filename = f"{tender_id}/{uuid.uuid4().hex[:8]}_{filename.split('/')[-1]}"
                        url = self.upload_file(file_bytes, safe_filename)
                        uploaded_urls.append(url)
        except Exception as e:
            import structlog
            log = structlog.get_logger()
            log.warning("zip.extraction.failed", error=str(e), url=zip_url)
            
        return uploaded_urls

storage_service = StorageService()