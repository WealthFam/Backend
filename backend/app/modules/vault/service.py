import os
import shutil
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from . import models

STORAGE_BASE_PATH = "data/vault"

class VaultService:
    @staticmethod
    def _get_storage_path(tenant_id: str, doc_id: str, version: int = 1) -> str:
        """Helper to get the physical storage path for a file version"""
        path = os.path.join(STORAGE_BASE_PATH, tenant_id, doc_id)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return os.path.join(path, f"v{version}")

    @staticmethod
    def upload_document(
        db: Session,
        tenant_id: str,
        owner_id: str,
        file,  # UploadFile from fastapi
        file_type: models.DocumentType = models.DocumentType.OTHER,
        transaction_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        is_shared: bool = True,
        description: Optional[str] = None
    ) -> models.DocumentVault:
        """Handle file upload and metadata creation with versioning"""
        
        # 0. Check for filename collision in the same parent folder
        query = db.query(models.DocumentVault).filter(
            models.DocumentVault.tenant_id == tenant_id,
            models.DocumentVault.filename == file.filename,
            models.DocumentVault.parent_id == parent_id,
            models.DocumentVault.is_folder == False
        )
        
        existing_doc = query.first()
        if existing_doc:
            return VaultService.update_document_version(db, existing_doc.id, tenant_id, file)

        # 1. Generate ID and prepare path
        doc_id = str(uuid.uuid4())
        file_path = VaultService._get_storage_path(tenant_id, doc_id, version=1)
        
        # 2. Save physical file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise Exception(f"Failed to save file to storage: {str(e)}")

        file_size = os.path.getsize(file_path)

        # 3. Create database record
        try:
            doc_meta = models.DocumentVault(
                id=doc_id,
                tenant_id=tenant_id,
                owner_id=owner_id,
                filename=file.filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                mime_type=file.content_type,
                transaction_id=transaction_id,
                parent_id=parent_id,
                is_folder=False,
                is_shared=is_shared,
                description=description,
                current_version=1
            )
            db.add(doc_meta)
            
            # Create first version record
            first_version = models.DocumentVersion(
                document_id=doc_id,
                version_number=1,
                file_path=file_path,
                file_size=file_size,
                filename=file.filename
            )
            db.add(first_version)
            
            db.commit()
            db.refresh(doc_meta)
            return doc_meta
        except Exception as e:
            # Cleanup file if DB insert fails
            if os.path.exists(os.path.dirname(file_path)):
                shutil.rmtree(os.path.dirname(file_path))
            db.rollback()
            raise Exception(f"Failed to create document record: {str(e)}")

    @staticmethod
    def update_document_version(
        db: Session,
        doc_id: str,
        tenant_id: str,
        file
    ) -> models.DocumentVault:
        """Upload a new version of an existing document"""
        doc = VaultService.get_document_by_id(db, doc_id, tenant_id)
        if not doc or doc.is_folder:
            raise Exception("Document not found or is a folder")

        new_version_num = int(doc.current_version) + 1
        file_path = VaultService._get_storage_path(tenant_id, doc_id, version=new_version_num)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_size = os.path.getsize(file_path)
            
            # Update Document record
            doc.file_path = file_path
            doc.file_size = file_size
            doc.current_version = new_version_num
            doc.filename = file.filename # Update filename to latest if changed
            doc.mime_type = file.content_type
            
            # Create Version record
            new_ver = models.DocumentVersion(
                document_id=doc.id,
                version_number=new_version_num,
                file_path=file_path,
                file_size=file_size,
                filename=file.filename
            )
            db.add(new_ver)
            
            db.commit()
            db.refresh(doc)
            return doc
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            db.rollback()
            raise Exception(f"Failed to update document version: {str(e)}")

    @staticmethod
    def create_folder(
        db: Session,
        tenant_id: str,
        owner_id: str,
        name: str,
        parent_id: Optional[str] = None,
        is_shared: bool = True,
        description: Optional[str] = None
    ) -> models.DocumentVault:
        """Create a virtual folder in the vault"""
        folder = models.DocumentVault(
            tenant_id=tenant_id,
            owner_id=owner_id,
            filename=name,
            file_type=models.DocumentType.OTHER,
            is_folder=True,
            parent_id=parent_id,
            is_shared=is_shared,
            description=description,
            file_size=0,
            current_version=0
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)
        return folder

    @staticmethod
    def get_documents(
        db: Session,
        tenant_id: str,
        user_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        parent_id: Optional[str] = "ROOT",
        file_type: Optional[models.DocumentType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[models.DocumentVault]:
        """List documents with tenant and owner isolation"""
        query = db.query(models.DocumentVault).filter(
            models.DocumentVault.tenant_id == tenant_id
        )
        
        if parent_id == "ROOT":
            query = query.filter(models.DocumentVault.parent_id == None)
        elif parent_id:
            query = query.filter(models.DocumentVault.parent_id == parent_id)

        if transaction_id:
            query = query.filter(models.DocumentVault.transaction_id == transaction_id)
        if file_type:
            query = query.filter(models.DocumentVault.file_type == file_type)
            
        if user_id:
            query = query.filter(
                or_(
                    models.DocumentVault.owner_id == user_id,
                    models.DocumentVault.is_shared == True
                )
            )
            
        return query.order_by(models.DocumentVault.is_folder.desc(), models.DocumentVault.filename.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_document_by_id(db: Session, doc_id: str, tenant_id: str) -> Optional[models.DocumentVault]:
        return db.query(models.DocumentVault).filter(
            models.DocumentVault.id == doc_id,
            models.DocumentVault.tenant_id == tenant_id
        ).first()

    @staticmethod
    def delete_document(db: Session, doc_id: str, tenant_id: str) -> bool:
        """Recursive delete for folders and physical file cleanup"""
        doc = VaultService.get_document_by_id(db, doc_id, tenant_id)
        if not doc:
            return False
            
        if doc.is_folder:
            children = db.query(models.DocumentVault).filter(models.DocumentVault.parent_id == doc.id).all()
            for child in children:
                VaultService.delete_document(db, child.id, tenant_id)
        else:
            # Delete physical directory containing all versions
            if doc.file_path:
                doc_dir = os.path.dirname(doc.file_path)
                if os.path.exists(doc_dir):
                    try:
                        shutil.rmtree(doc_dir)
                    except Exception as e:
                        print(f"Error removing directory {doc_dir}: {e}")
                
        db.delete(doc)
        db.commit()
        return True

    @staticmethod
    def get_sync_history(db: Session, tenant_id: str, limit: int = 10):
        """Get recent sync logs for the vault"""
        return db.query(models.VaultSyncHistory).filter(
            models.VaultSyncHistory.tenant_id == tenant_id
        ).order_by(models.VaultSyncHistory.started_at.desc()).limit(limit).all()

    @staticmethod
    def save_sync_settings(db: Session, tenant_id: str, credentials_json: str):
        """Save GDrive service account JSON to DB"""
        from backend.app.modules.auth.models import TenantSetting
        import json
        
        # Validate JSON
        try:
            json.loads(credentials_json)
        except:
            raise Exception("Invalid JSON formatting for credentials")

        setting = db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == "vault_gdrive_config"
        ).first()
        
        if not setting:
            setting = TenantSetting(
                tenant_id=tenant_id,
                key="vault_gdrive_config",
                value=credentials_json
            )
            db.add(setting)
        else:
            setting.value = credentials_json
            
        db.commit()
        return {"status": "success"}

    @staticmethod
    def get_sync_settings(db: Session, tenant_id: str):
        """Check if sync is configured and return meta"""
        from backend.app.modules.auth.models import TenantSetting
        setting = db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == "vault_gdrive_config"
        ).first()
        
        return {
            "configured": setting is not None and setting.value is not None,
            "last_updated": setting.updated_at if setting else None
        }

    @staticmethod
    def clear_sync_settings(db: Session, tenant_id: str):
        """Remove GDrive credentials from DB"""
        from backend.app.modules.auth.models import TenantSetting
        db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == "vault_gdrive_config"
        ).delete()
        db.commit()
        return {"status": "success"}
