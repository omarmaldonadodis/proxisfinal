# app/api/v1/alerts.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert, AlertStatus, AlertSeverity

router = APIRouter(prefix="/alerts", tags=["🔔 Alerts"])


@router.get("/")
async def list_alerts(
    status: Optional[AlertStatus] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert).order_by(desc(Alert.created_at))
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    if source:
        query = query.where(Alert.source == source)
    result = await db.execute(query.limit(limit))
    alerts = result.scalars().all()
    return {"total": len(alerts), "items": alerts}


@router.post("/", status_code=201)
async def create_alert(
    title: str,
    message: Optional[str] = None,
    severity: AlertSeverity = AlertSeverity.INFO,
    source: Optional[str] = None,
    source_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    alert = Alert(
        title=title, message=message, severity=severity,
        source=source, source_id=source_id
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/ack")
async def ack_alert(
    alert_id: int,
    acknowledged_by: str = Query(default="user"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/silence")
async def silence_alert(
    alert_id: int,
    minutes: int = Query(default=60, ge=1, le=10080),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.SILENCED
    alert.silenced_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()