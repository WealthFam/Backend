from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from .service import VaultService
from .gdrive import GoogleDriveService
from . import models

router = APIRouter()

@router.post("/sync")
def trigger_sync(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger bidirectional sync with Google Drive"""
    res = GoogleDriveService.sync_to_cloud(db, str(current_user.tenant_id))
    return res

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
    """Securely upload a document to the vault with folder support"""
    try:
        doc = VaultService.upload_document(
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
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{document_id}/version")
async def update_document_version(
    document_id: str,
    file: UploadFile = File(...),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new version of an existing document"""
    try:
        return VaultService.update_document_version(
            db=db,
            doc_id=document_id,
            tenant_id=str(current_user.tenant_id),
            file=file
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    
    return db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.desc()).all()

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
    skip: int = 0,
    limit: int = 50,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List vault documents/folders with hierarchical support"""
    return VaultService.get_documents(
        db=db,
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        transaction_id=transaction_id,
        parent_id=parent_id,
        file_type=file_type,
        skip=skip,
        limit=limit
    )

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
