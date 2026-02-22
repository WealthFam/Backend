import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from sqlalchemy.orm import Session
from datetime import datetime
import json
from . import models
from backend.app.modules.auth.models import TenantSetting

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_PATH = "backend/storage/credentials.json"
APP_FOLDER_NAME = "WealthFam_Vault"

class GoogleDriveService:
    @staticmethod
    def _get_service(db: Session, tenant_id: str):
        """Initialize GDrive service using credentials from DB"""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        setting = db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == "vault_gdrive_config"
        ).first()
        
        if not setting or not setting.value:
            return None
            
        try:
            config = json.loads(setting.value)
            
            # 1. If we already have a refresh token, use it
            if config.get("refresh_token") and config.get("client_id") and config.get("client_secret"):
                creds = Credentials(
                    token=None,
                    refresh_token=config["refresh_token"],
                    client_id=config["client_id"],
                    client_secret=config["client_secret"],
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=SCOPES
                )
                
                if not creds.valid:
                    creds.refresh(Request())
                    # Update saved config with potentially new tokens
                    config["refresh_token"] = creds.refresh_token or config["refresh_token"]
                    setting.value = json.dumps(config)
                    db.commit()
                
                return build('drive', 'v3', credentials=creds)
            
            # 2. Fallback to Service Account if JSON is in the old format
            if config.get("type") == "service_account":
                creds = service_account.Credentials.from_service_account_info(
                    config, scopes=SCOPES
                )
                return build('drive', 'v3', credentials=creds)
                
            return None
        except Exception as e:
            print(f"Failed to initialize GDrive service: {e}")
            return None

    @staticmethod
    def get_auth_url(db: Session, tenant_id: str, client_id: str, client_secret: str):
        """Generate Authorization URL for the user to visit"""
        from google_auth_oauthlib.flow import Flow
        
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost:8000/api/v1/finance/vault/callback"]
            }
        }
        
        # We use 'offline' access to get a refresh token
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        # Save temporary partial config
        from .service import VaultService
        VaultService.save_sync_settings(db, tenant_id, json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "pending_auth": True
        }))
        
        return {"auth_url": auth_url}

    @staticmethod
    def exchange_code(db: Session, tenant_id: str, code: str):
        """Exchange auth code for tokens"""
        from google_auth_oauthlib.flow import Flow
        
        setting = db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == "vault_gdrive_config"
        ).first()
        
        if not setting or not setting.value:
            raise Exception("Configuration not found")
            
        config = json.loads(setting.value)
        
        client_config = {
            "web": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        final_config = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": creds.refresh_token,
            "token": creds.token
        }
        
        setting.value = json.dumps(final_config)
        db.commit()
        
        return {"status": "success", "message": "Tokens successfully exchanged"}

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
        """Push local changes to Google Drive with history tracking"""
        # Create history entry
        history = models.VaultSyncHistory(
            tenant_id=tenant_id, 
            status="running",
            message="Starting cloud sync..."
        )
        db.add(history)
        db.commit() # Save initial status
        
        try:
            service = GoogleDriveService._get_service(db, tenant_id)
            if not service:
                raise Exception("GDrive credentials missing or invalid")

            root_folder_id = GoogleDriveService.get_or_create_app_folder(service)
            
            # 1. Fetch all vault items to memory to handle them cleanly
            vault_items = db.query(models.DocumentVault).filter(
                models.DocumentVault.tenant_id == tenant_id
            ).all()
            
            folders = [f for f in vault_items if f.is_folder]
            files = [f for f in vault_items if not f.is_folder]
            
            # Simple hierarchical sort for folders (Parents before children)
            # This ensures parents are created on Drive before we try to put children in them
            folders.sort(key=lambda x: 0 if x.parent_id is None else 1)
            
            folder_map = {"ROOT": root_folder_id}
            items_count = 0
            
            # 2. Sync Folders
            for folder in folders:
                parent_local_id = folder.parent_id or "ROOT"
                parent_gdrive_id = folder_map.get(parent_local_id) or root_folder_id
                
                if not folder.gdrive_file_id:
                    meta = {
                        'name': folder.filename,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_gdrive_id]
                    }
                    res = service.files().create(body=meta, fields='id').execute()
                    folder.gdrive_file_id = res.get('id')
                
                folder_map[folder.id] = folder.gdrive_file_id
            
            # Use flush instead of commit to avoid DuckDB FK issues during the loop
            db.flush()

            # 3. Sync Files
            for doc in files:
                if not doc.file_path or not os.path.exists(doc.file_path):
                    continue
                    
                parent_gdrive_id = folder_map.get(doc.parent_id) or root_folder_id
                media = MediaFileUpload(doc.file_path, mimetype=doc.mime_type, resumable=True)
                
                if not doc.gdrive_file_id:
                    # Upload new
                    file_metadata = {
                        'name': doc.filename,
                        'parents': [parent_gdrive_id]
                    }
                    res = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                    doc.gdrive_file_id = res.get('id')
                else:
                    # Update existing content
                    service.files().update(fileId=doc.gdrive_file_id, media_body=media).execute()

                doc.last_synced_at = datetime.utcnow()
                items_count += 1

            # Success! Commit everything
            db.commit()

            # Refresh history record
            db.expire(history) # history might be in a different transaction state
            history = db.query(models.VaultSyncHistory).get(history.id)
            if history:
                history.status = "success"
                history.message = "Sync to cloud complete"
                history.items_processed = items_count
                history.completed_at = datetime.utcnow()
                db.commit()

            return {"status": "success", "message": "Sync to cloud complete"}
            
        except Exception as e:
            # IMPORTANT: Rollback the main transaction first
            db.rollback()
            
            # Try to log the error in a fresh transaction
            try:
                # We can't use the 'history' object if the session rolled back
                # Let's create a new record or find the old one
                error_history = models.VaultSyncHistory(
                    tenant_id=tenant_id,
                    status="error",
                    message=f"Sync failed: {str(e)}",
                    error_details=str(e),
                    completed_at=datetime.utcnow()
                )
                db.add(error_history)
                db.commit()
            except:
                pass
                
            return {"status": "error", "message": str(e)}

    @staticmethod
    def test_connection(db: Session, tenant_id: str):
        """Verify credentials and return account info"""
        service = GoogleDriveService._get_service(db, tenant_id)
        if not service:
            return {"status": "error", "message": "Credentials invalid or missing"}
        
        try:
            about = service.about().get(fields="user(displayName, emailAddress)").execute()
            return {
                "status": "success", 
                "account": about.get("user", {}).get("emailAddress"),
                "name": about.get("user", {}).get("displayName")
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
