"""File storage service using Google Cloud Storage."""

import io
from typing import Optional
from functools import lru_cache

from google.cloud import storage
from fastapi import UploadFile

from ..core import get_logger, settings, FileProcessingError

logger = get_logger(__name__)


class FileStorageService:
    """Service for file storage operations using Google Cloud Storage."""
    
    def __init__(self):
        """Initialize the file storage service."""
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
    
    @property
    def client(self) -> storage.Client:
        """Get or create Google Cloud Storage client."""
        if self._client is None:
            try:
                self._client = storage.Client(project=settings.google_cloud_project)
                logger.info("Google Cloud Storage client initialized")
            except Exception as exc:
                logger.error("Failed to initialize GCS client", error=str(exc))
                raise FileProcessingError(f"Failed to initialize storage service: {str(exc)}") from exc
        return self._client
    
    @property 
    def bucket(self) -> storage.Bucket:
        """Get the storage bucket."""
        if self._bucket is None:
            try:
                self._bucket = self.client.bucket(settings.google_cloud_storage_bucket)
                logger.info("Storage bucket accessed", bucket=settings.google_cloud_storage_bucket)
            except Exception as exc:
                logger.error("Failed to access storage bucket", error=str(exc))
                raise FileProcessingError(f"Failed to access storage bucket: {str(exc)}") from exc
        return self._bucket
    
    async def upload_file(self, file: UploadFile) -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            FileProcessingError: If upload fails
        """
        try:
            logger.info(
                "Uploading file to storage",
                filename=file.filename,
                content_type=file.content_type,
                size=file.size
            )
            
            # Generate unique filename
            import uuid
            from datetime import datetime
            
            file_extension = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'bin'
            unique_filename = f"tests/{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4()}.{file_extension}"
            
            # Create blob
            blob = self.bucket.blob(unique_filename)
            
            # Set content type
            if file.content_type:
                blob.content_type = file.content_type
            
            # Upload file data
            file_content = await file.read()
            blob.upload_from_string(
                file_content,
                content_type=file.content_type
            )
            
            # Make blob publicly accessible
            blob.make_public()
            
            public_url = blob.public_url
            
            logger.info(
                "File uploaded successfully",
                filename=file.filename,
                storage_path=unique_filename,
                public_url=public_url,
                size=len(file_content)
            )
            
            return public_url
            
        except Exception as exc:
            logger.error(
                "File upload failed",
                filename=file.filename,
                error=str(exc),
                exc_info=True
            )
            raise FileProcessingError(
                f"Failed to upload file {file.filename}: {str(exc)}",
                filename=file.filename
            ) from exc
    
    async def download_file(self, file_url: str) -> bytes:
        """
        Download a file from storage.
        
        Args:
            file_url: URL of the file to download
            
        Returns:
            File content as bytes
            
        Raises:
            FileProcessingError: If download fails
        """
        try:
            logger.info("Downloading file from storage", file_url=file_url)
            
            # Extract blob name from URL
            # URLs are in format: https://storage.googleapis.com/bucket-name/path/to/file
            if '/storage.googleapis.com/' in file_url:
                parts = file_url.split('/storage.googleapis.com/')[-1].split('/', 1)
                if len(parts) == 2:
                    bucket_name, blob_name = parts
                    blob = self.client.bucket(bucket_name).blob(blob_name)
                else:
                    raise ValueError("Invalid storage URL format")
            else:
                raise ValueError("Not a valid Google Cloud Storage URL")
            
            # Download blob content
            content = blob.download_as_bytes()
            
            logger.info(
                "File downloaded successfully",
                file_url=file_url,
                size=len(content)
            )
            
            return content
            
        except Exception as exc:
            logger.error(
                "File download failed",
                file_url=file_url,
                error=str(exc),
                exc_info=True
            )
            raise FileProcessingError(f"Failed to download file: {str(exc)}") from exc
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_url: URL of the file to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            FileProcessingError: If deletion fails
        """
        try:
            logger.info("Deleting file from storage", file_url=file_url)
            
            # Extract blob name from URL
            if '/storage.googleapis.com/' in file_url:
                parts = file_url.split('/storage.googleapis.com/')[-1].split('/', 1)
                if len(parts) == 2:
                    bucket_name, blob_name = parts
                    blob = self.client.bucket(bucket_name).blob(blob_name)
                else:
                    raise ValueError("Invalid storage URL format")
            else:
                raise ValueError("Not a valid Google Cloud Storage URL")
            
            # Delete blob
            blob.delete()
            
            logger.info("File deleted successfully", file_url=file_url)
            return True
            
        except Exception as exc:
            logger.error(
                "File deletion failed",
                file_url=file_url,
                error=str(exc),
                exc_info=True
            )
            # Don't raise exception for deletion failures, just log and return False
            return False
    
    async def get_file_info(self, file_url: str) -> dict:
        """
        Get information about a file in storage.
        
        Args:
            file_url: URL of the file
            
        Returns:
            Dictionary with file information
            
        Raises:
            FileProcessingError: If operation fails
        """
        try:
            # Extract blob name from URL
            if '/storage.googleapis.com/' in file_url:
                parts = file_url.split('/storage.googleapis.com/')[-1].split('/', 1)
                if len(parts) == 2:
                    bucket_name, blob_name = parts
                    blob = self.client.bucket(bucket_name).blob(blob_name)
                else:
                    raise ValueError("Invalid storage URL format")
            else:
                raise ValueError("Not a valid Google Cloud Storage URL")
            
            # Reload blob to get fresh metadata
            blob.reload()
            
            info = {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created.isoformat() if blob.time_created else None,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'public_url': blob.public_url
            }
            
            logger.info("File info retrieved", file_url=file_url, info=info)
            return info
            
        except Exception as exc:
            logger.error(
                "Failed to get file info",
                file_url=file_url,
                error=str(exc)
            )
            raise FileProcessingError(f"Failed to get file info: {str(exc)}") from exc


@lru_cache()
def get_file_storage_service() -> FileStorageService:
    """Get singleton file storage service instance."""
    return FileStorageService()