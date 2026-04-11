import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user

from . import models
from .gdrive import GoogleDriveService
from .service import VaultService

router = APIRouter()

@router.post("/sync")
def trigger_sync(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger bidirectional sync with Google Drive"""
    res = GoogleDriveService.sync_to_cloud(db, str(current_user.tenant_id))
    return res

@router.get("/settings")
def get_sync_settings(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check sync configuration status"""
    return VaultService.get_sync_settings(db, str(current_user.tenant_id))

@router.post("/settings")
def save_sync_settings(
    creds: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save GDrive service account creds"""
    return VaultService.save_sync_settings(db, str(current_user.tenant_id), creds.get("credentials_json", ""))

@router.delete("/settings")
def clear_sync_settings(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear GDrive credentials"""
    return VaultService.clear_sync_settings(db, str(current_user.tenant_id))

@router.post("/settings/test")
def test_sync_connection(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify stored GDrive credentials"""
    return GoogleDriveService.test_connection(db, str(current_user.tenant_id))

@router.post("/settings/auth-url")
def get_gdrive_auth_url(
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate GDrive OAuth URL"""
    return GoogleDriveService.get_auth_url(
        db, 
        str(current_user.tenant_id), 
        data.get("client_id"), 
        data.get("client_secret")
    )

@router.post("/settings/callback")
def gdrive_callback(
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exchange code for GDrive tokens"""
    return GoogleDriveService.exchange_code(db, str(current_user.tenant_id), data.get("code"))

@router.get("/history")
def get_sync_history(
    limit: int = 10,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent sync logs"""
    items = VaultService.get_sync_history(db, str(current_user.tenant_id), limit)
    return {
        "data": items,
        "total": len(items)
    }

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    file_type: models.DocumentType = Form(models.DocumentType.OTHER),
    transaction_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    is_shared: bool = Form(True),
    description: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new document or version to the vault"""
    # Check if this filename already exists in the same folder to handle versioning
    # Actually service.py handles it by looking at parent_id + filename
    return await VaultService.upload_document(
        db=db,
        tenant_id=str(current_user.tenant_id),
        owner_id=str(current_user.id),
        file=file,
        file_type=file_type,
        transaction_id=transaction_id,
        parent_id=parent_id,
        is_shared=is_shared,
        description=description
    )

@router.post("/{document_id}/version")
async def upload_new_version(
    document_id: str,
    file: UploadFile = File(...),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force upload a new version for an existing document ID"""
    return await VaultService.upload_version(
        db=db,
        doc_id=document_id,
        tenant_id=str(current_user.tenant_id),
        file=file
    )

@router.put("/{document_id}")
def update_document(
    document_id: str,
    file_type: Optional[models.DocumentType] = Form(None),
    is_shared: Optional[bool] = Form(None),
    filename: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update metadata for an existing document"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if file_type is not None:
        doc.file_type = file_type
    if is_shared is not None:
        doc.is_shared = is_shared
    if filename is not None:
        doc.filename = filename
    if description is not None:
        doc.description = description
        
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/move")
def move_documents(
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch move documents/folders to a new parent folder"""
    doc_ids = data.get("doc_ids", [])
    target_parent_id = data.get("target_parent_id")
    
    if not doc_ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")
        
    try:
        count = VaultService.move_documents(
            db=db,
            doc_ids=doc_ids,
            tenant_id=str(current_user.tenant_id),
            target_parent_id=target_parent_id
        )
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{document_id}/link-transaction")
def link_document_to_transaction(
    document_id: str,
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link or unlink a vault document to a transaction. Pass transaction_id=null to unlink."""
    transaction_id = data.get("transaction_id")
    doc = VaultService.link_transaction(db, document_id, str(current_user.tenant_id), transaction_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/versions")
def list_document_versions(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all versions of a specific document"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    items = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.desc()).all()
    
    return {
        "data": items,
        "total": len(items)
    }

@router.post("/folders")
def create_folder(
    name: str = Form(...),
    parent_id: Optional[str] = Form(None),
    is_shared: bool = Form(True),
    description: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new folder in the vault"""
    return VaultService.create_folder(
        db=db,
        tenant_id=str(current_user.tenant_id),
        owner_id=str(current_user.id),
        name=name,
        parent_id=parent_id,
        is_shared=is_shared,
        description=description
    )

@router.get("")
@router.get("/")
def list_documents(
    transaction_id: Optional[str] = None,
    parent_id: Optional[str] = "ROOT",
    file_type: Optional[models.DocumentType] = None,
    search: Optional[str] = None,
    is_folder: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List vault documents/folders with hierarchical support"""
    items, total = VaultService.get_documents(
        db=db,
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        transaction_id=transaction_id,
        parent_id=parent_id,
        file_type=file_type,
        search=search,
        is_folder=is_folder,
        skip=skip,
        limit=limit
    )
    return {
        "data": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    version: Optional[int] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Securely stream a document version download"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.is_shared and doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = doc.file_path
    filename = doc.filename
    
    # If a specific version is requested
    if version and version != doc.current_version:
        ver_record = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == version
        ).first()
        if not ver_record:
            raise HTTPException(status_code=404, detail="Version not found")
        file_path = ver_record.file_path
        filename = ver_record.filename

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=doc.mime_type
    )

@router.get("/{document_id}/view")
def view_document(
    document_id: str,
    version: Optional[int] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve a document version for inline viewing (preview)"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.is_shared and doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = doc.file_path
    
    # If a specific version is requested
    if version and version != doc.current_version:
        ver_record = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == version
        ).first()
        if not ver_record:
            raise HTTPException(status_code=404, detail="Version not found")
        file_path = ver_record.file_path

    # Use inline disposition for previews
    return FileResponse(
        path=file_path,
        media_type=doc.mime_type,
        content_disposition_type="inline"
    )

@router.get("/{document_id}/thumbnail")
def get_thumbnail(
    document_id: str,
    version: Optional[int] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve a document thumbnail for the vault grid"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.is_shared and doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    thumb_path = doc.thumbnail_path
    
    # If a specific version is requested
    if version and version != doc.current_version:
        ver_record = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == document_id,
            models.DocumentVersion.version_number == version
        ).first()
        if ver_record:
            thumb_path = ver_record.thumbnail_path

    if not thumb_path or not os.path.exists(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(
        path=thumb_path,
        media_type="image/jpeg"
    )

@router.get("/{document_id}")
def get_document(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single document metadata"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document/folder and its history"""
    doc = VaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only the owner can delete this document")

    success = VaultService.delete_document(db, document_id, str(current_user.tenant_id))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
        
    return {"status": "success", "message": "Deleted successfully"}
