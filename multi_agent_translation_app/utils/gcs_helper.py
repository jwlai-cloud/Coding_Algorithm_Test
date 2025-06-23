"""Google Cloud Storage helper utilities."""

import os
from typing import List, Optional
from google.cloud import storage
from loguru import logger

from config.settings import get_gcs_config


class GCSHelper:
    """Helper class for Google Cloud Storage operations."""
    
    def __init__(self):
        self.client = storage.Client()
        self.config = get_gcs_config()
        self.bucket = self.client.bucket(self.config["bucket_name"])
        
    def upload_file(self, local_path: str, gcs_path: str) -> str:
        """Upload a file to GCS and return the GCS URI."""
        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)
            
            gcs_uri = f"gs://{self.config['bucket_name']}/{gcs_path}"
            logger.info(f"Uploaded file to GCS: {gcs_uri}")
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {str(e)}")
            raise
            
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """Download a file from GCS to local path."""
        try:
            blob = self.bucket.blob(gcs_path)
            blob.download_to_filename(local_path)
            
            logger.info(f"Downloaded file from GCS: {gcs_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download file from GCS: {str(e)}")
            raise
            
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in GCS bucket with optional prefix."""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            file_paths = [blob.name for blob in blobs]
            
            logger.info(f"Listed {len(file_paths)} files with prefix: {prefix}")
            return file_paths
            
        except Exception as e:
            logger.error(f"Failed to list files in GCS: {str(e)}")
            raise
            
    def delete_file(self, gcs_path: str) -> bool:
        """Delete a file from GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            blob.delete()
            
            logger.info(f"Deleted file from GCS: {gcs_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from GCS: {str(e)}")
            return False
            
    def file_exists(self, gcs_path: str) -> bool:
        """Check if a file exists in GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
            
        except Exception as e:
            logger.error(f"Failed to check file existence in GCS: {str(e)}")
            return False
            
    def get_file_info(self, gcs_path: str) -> Optional[dict]:
        """Get file information from GCS."""
        try:
            blob = self.bucket.blob(gcs_path)
            if not blob.exists():
                return None
                
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created,
                "updated": blob.updated,
                "etag": blob.etag
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info from GCS: {str(e)}")
            return None
            
    def create_signed_url(self, gcs_path: str, expiration_minutes: int = 60) -> str:
        """Create a signed URL for temporary access to a GCS file."""
        try:
            from datetime import datetime, timedelta
            
            blob = self.bucket.blob(gcs_path)
            expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            signed_url = blob.generate_signed_url(expiration=expiration)
            
            logger.info(f"Created signed URL for: {gcs_path}")
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to create signed URL: {str(e)}")
            raise

