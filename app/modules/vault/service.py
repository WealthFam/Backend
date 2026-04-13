import logging
import os
import shutil
import uuid
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from . import models

logger = logging.getLogger(__name__)

STORAGE_BASE_PATH = "data/vault"
THUMBNAIL_SIZE = (256, 256)

class VaultService:
    @staticmethod
    def _get_storage_path(tenant_id: str, doc_id: str, version: int = 1) -> str:
        """Helper to get the physical storage path for a file version"""
        path = os.path.join(STORAGE_BASE_PATH, tenant_id, doc_id)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return os.path.join(path, f"v{version}")

    @staticmethod
    def _generate_thumbnail(file_path: str, content_type: str) -> Optional[str]:
        """Generate a 256x256 thumbnail for images and PDFs"""
        try:
            import mimetypes
            
            # 0. Robust Content Type detection
            if not content_type or content_type == "application/octet-stream":
                guessed, _ = mimetypes.guess_type(file_path)
                if guessed:
                    content_type = guessed
            
            logger.info(f"Generating thumbnail for {file_path} (Type: {content_type})")
            thumb_path = f"{file_path}_thumb.jpg"
            
            # 1. Handle Images
            if content_type and content_type.startswith("image/"):
                # Deferred import to avoid mandatory dependency on libraries in environments not processing images
                from PIL import Image
                with Image.open(file_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE)
                    if img.mode in ("RGBA", "P"):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        try:
                            # Try to use transparency mask
                            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
                        except:
                            background.paste(img)
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(thumb_path, "JPEG", quality=85)
                logger.info(f"  Image thumbnail created: {thumb_path}")
                return thumb_path
                
            # 2. Handle PDFs
            elif content_type and (content_type == "application/pdf" or "pdf" in content_type):
                try:
                    # Deferred import to avoid mandatory dependency on PyMuPDF (fitz)
                    import fitz  # PyMuPDF
                    doc = fitz.open(file_path)
                    if doc.page_count > 0:
                        page = doc.load_page(0)  # first page
                        pix = page.get_pixmap(matrix=fitz.Matrix(THUMBNAIL_SIZE[0]/page.rect.width, THUMBNAIL_SIZE[0]/page.rect.width))
                        pix.save(thumb_path)
                        doc.close()
                        logger.info(f"  PDF thumbnail created: {thumb_path}")
                        return thumb_path
                except Exception as pdf_err:
                    logger.error(f"  PDF thumbnail generation failed: {pdf_err}")
            
            logger.info(f"  No thumbnail generator for type: {content_type}")
            return None
        except Exception as e:
            logger.error(f"  Thumbnail generation error for {file_path}: {e}")
            return None

    @staticmethod
    async def upload_document(
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
        if parent_id == "":
            parent_id = None
        
        # 0. Check for filename collision in the same parent folder
        query = db.query(models.DocumentVault).filter(
            models.DocumentVault.tenant_id == tenant_id,
            models.DocumentVault.filename == file.filename,
            models.DocumentVault.parent_id == parent_id,
            models.DocumentVault.is_folder == False
        )
        
        existing_doc = query.first()
        if existing_doc:
            return await VaultService.upload_version(db, existing_doc.id, tenant_id, file, transaction_id=transaction_id)

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
        thumbnail_path = VaultService._generate_thumbnail(file_path, file.content_type)

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
                thumbnail_path=thumbnail_path,
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
                filename=file.filename,
                thumbnail_path=thumbnail_path
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
    async def upload_version(
        db: Session,
        doc_id: str,
        tenant_id: str,
        file,
        transaction_id: Optional[str] = None
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
            thumbnail_path = VaultService._generate_thumbnail(file_path, file.content_type)
            
            # Update Document record
            doc.file_path = file_path
            doc.file_size = file_size
            doc.current_version = new_version_num
            doc.filename = file.filename # Update filename to latest if changed
            doc.mime_type = file.content_type
            doc.thumbnail_path = thumbnail_path
            
            if transaction_id:
                doc.transaction_id = transaction_id
            
            # Create Version record
            new_ver = models.DocumentVersion(
                document_id=doc.id,
                version_number=new_version_num,
                file_path=file_path,
                file_size=file_size,
                filename=file.filename,
                thumbnail_path=thumbnail_path
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
        if parent_id == "":
            parent_id = None
            
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
        search: Optional[str] = None,
        is_folder: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[models.DocumentVault], int]:
        """List documents with tenant and owner isolation"""
        query = db.query(models.DocumentVault).options(
            joinedload(models.DocumentVault.transaction)
        ).filter(
            models.DocumentVault.tenant_id == tenant_id
        )

        # When searching by text or transaction, ignore folder hierarchy
        if search:
            query = query.filter(models.DocumentVault.filename.ilike(f"%{search}%"))
            
        if transaction_id:
            query = query.filter(
                models.DocumentVault.transaction_id == transaction_id,
                models.DocumentVault.is_folder == False
            )
        
        # Folder hierarchy (only if not searching/filtering by transaction)
        if not search and not transaction_id:
            if parent_id == "ALL":
                pass # No parent filter
            elif parent_id == "ROOT":
                query = query.filter(models.DocumentVault.parent_id == None)
            elif parent_id:
                query = query.filter(models.DocumentVault.parent_id == parent_id)

        if transaction_id:
            query = query.filter(models.DocumentVault.transaction_id == transaction_id)
        if file_type:
            query = query.filter(
                or_(
                    models.DocumentVault.file_type == file_type,
                    models.DocumentVault.is_folder == True
                )
            )
        if is_folder is not None:
            query = query.filter(models.DocumentVault.is_folder == is_folder)
            
        if user_id:
            query = query.filter(
                or_(
                    models.DocumentVault.owner_id == user_id,
                    models.DocumentVault.is_shared == True
                )
            )
            
        total = query.count()
        items = query.order_by(models.DocumentVault.is_folder.desc(), models.DocumentVault.filename.asc()).offset(skip).limit(limit).all()
        return items, total

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
    def link_transaction(db: Session, doc_id: str, tenant_id: str, transaction_id: Optional[str]) -> models.DocumentVault:
        """Link or unlink a document to a transaction"""
        doc = VaultService.get_document_by_id(db, doc_id, tenant_id)
        if not doc:
            return None
            
        doc.transaction_id = transaction_id
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def move_documents(db: Session, doc_ids: List[str], tenant_id: str, target_parent_id: Optional[str]) -> int:
        """Batch move documents/folders to a new parent folder"""
        if target_parent_id == "ROOT" or target_parent_id == "":
            target_parent_id = None
            
        # Verify target exists and is a folder
        if target_parent_id:
            target = VaultService.get_document_by_id(db, target_parent_id, tenant_id)
            if not target or not target.is_folder:
                raise Exception("Target parent is not a folder")

        count = 0
        for doc_id in doc_ids:
            # Prevent moving a folder into itself
            if doc_id == target_parent_id:
                continue
                
            doc = VaultService.get_document_by_id(db, doc_id, tenant_id)
            if doc:
                doc.parent_id = target_parent_id
                count += 1
        
        db.commit()
        return count

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
