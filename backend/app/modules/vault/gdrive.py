import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from sqlalchemy.orm import Session
from datetime import datetime
from . import models

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_PATH = "backend/storage/credentials.json"
APP_FOLDER_NAME = "WealthFam_Vault"

class GoogleDriveService:
    @staticmethod
    def _get_service():
        """Initialize GDrive service using service account"""
        if not os.path.exists(CREDENTIALS_PATH):
            return None
            
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH, scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)

    @staticmethod
    def get_or_create_app_folder(service) -> str:
        """Get or create the main app root folder in Drive"""
        query = f"name = '{APP_FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
            
        file_metadata = {
            'name': APP_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    @staticmethod
    def sync_to_cloud(db: Session, tenant_id: str):
        """Push local changes to Google Drive"""
        service = GoogleDriveService._get_service()
        if not service:
            return {"status": "error", "message": "GDrive credentials missing"}

        root_folder_id = GoogleDriveService.get_or_create_app_folder(service)
        
        # 1. Sync Folders first
        folders = db.query(models.DocumentVault).filter(
            models.DocumentVault.tenant_id == tenant_id,
            models.DocumentVault.is_folder == True
        ).all()
        
        folder_map = {"ROOT": root_folder_id}
        
        for folder in folders:
            # Determine parent GDrive ID
            parent_local_id = folder.parent_id or "ROOT"
            parent_gdrive_id = folder_map.get(parent_local_id)
            
            if not folder.gdrive_file_id:
                # Create on Drive
                meta = {
                    'name': folder.filename,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_gdrive_id] if parent_gdrive_id else [root_folder_id]
                }
                res = service.files().create(body=meta, fields='id').execute()
                folder.gdrive_file_id = res.get('id')
                db.commit()
            
            folder_map[folder.id] = folder.gdrive_file_id

        # 2. Sync Files
        files = db.query(models.DocumentVault).filter(
            models.DocumentVault.tenant_id == tenant_id,
            models.DocumentVault.is_folder == False
        ).all()

        for doc in files:
            if not doc.file_path or not os.path.exists(doc.file_path):
                continue
                
            parent_gdrive_id = folder_map.get(doc.parent_id) if doc.parent_id else root_folder_id
            
            media = MediaFileUpload(doc.file_path, mimetype=doc.mime_type, resumable=True)
            
            if not doc.gdrive_file_id:
                # Upload new
                file_metadata = {
                    'name': doc.filename,
                    'parents': [parent_gdrive_id]
                }
                res = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                doc.gdrive_file_id = res.get('id')
                doc.last_synced_at = datetime.utcnow()
                db.commit()
            else:
                # Update existing
                service.files().update(fileId=doc.gdrive_file_id, media_body=media).execute()
                doc.last_synced_at = datetime.utcnow()
                db.commit()

        return {"status": "success", "message": "Sync to cloud complete"}
