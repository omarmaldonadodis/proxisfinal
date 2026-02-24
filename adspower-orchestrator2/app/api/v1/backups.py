# app/api/v1/backups.py
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Path
from app.config import settings

router = APIRouter(prefix="/backups", tags=["💾 Backups"])


@router.get("/")
async def list_backups():
    backup_dir = settings.BACKUP_PATH
    if not os.path.exists(backup_dir):
        return {"total": 0, "items": []}

    items = []
    for filename in os.listdir(backup_dir):
        if not filename.endswith(".sql"):
            continue
        full_path = os.path.join(backup_dir, filename)
        stat = os.stat(full_path)
        items.append({
            "filename": filename,
            "size_mb": round(stat.st_size / (1024 ** 2), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"total": len(items), "items": items}


@router.post("/trigger", status_code=202)
async def trigger_backup():
    try:
        from app.tasks.backup_tasks import backup_database_task
        task = backup_database_task.delay()
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo iniciar backup: {e}")


@router.delete("/{filename}", status_code=204)
async def delete_backup(filename: str = Path(...)):
    safe_name = os.path.basename(filename)
    full_path = os.path.join(settings.BACKUP_PATH, safe_name)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    os.remove(full_path)