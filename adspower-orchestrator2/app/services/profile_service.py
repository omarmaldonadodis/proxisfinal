# app/services/profile_service.py - VERSIÓN CORREGIDA CON COOKIES
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime
import json

from app.models.profile import Profile, DeviceType, ProfileStatus
from app.models.computer import Computer
from app.models.proxy import Proxy
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.integrations.adspower_client import AdsPowerClient
from app.utils.profile_generator import ProfileGenerator
from loguru import logger

import time
from app.services.metrics_service import MetricsService
from app.config import settings



class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(self, profile_in: ProfileCreate) -> Profile:
        creation_start = time.time()  # ← FIX: definir aquí


        if not profile_in.proxy_id:
            raise ValueError("proxy_id is required")

        result = await self.db.execute(
            select(Proxy).where(Proxy.id == profile_in.proxy_id)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise ValueError(f"Proxy {profile_in.proxy_id} not found")

        profile_config = ProfileGenerator.generate_profile(
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_in.country or proxy.country or "EC",
            city=profile_in.city or proxy.city,
            device_type=profile_in.device_type.value,
            include_cookies=True,
            include_localstorage=True
        )

        screen_res = profile_config["screen_resolution"].replace("x", "_")

        fingerprint_config = {
            "automatic_timezone": "0",
            "timezone": profile_config["timezone"],
            "webrtc": "proxy",
            "location": "ask",
            "language": [profile_config["language"]],
            "page_language": [profile_config["language"]],
            "ua": profile_config["user_agent"],
            "screen_resolution": screen_res,
            "fonts": ["all"],
            "canvas": "1",
            "webgl_image": "1",
            "webgl": "1",
            "audio": "1",
            "do_not_track": "default",
            "hardware_concurrency": str(profile_config["hardware_concurrency"]),
            "device_memory": str(profile_config["device_memory"]),
            "flash": "block",
            "media_devices": "1",
            "client_rects": "1",
            "speech_voices": "1",
        }

        adspower_data = {
            "name": profile_in.name,
            "group_id": "0",
            "fingerprint_config": fingerprint_config,
            "remark": profile_config["remark"],
            "user_proxy_config": {
                "proxy_soft": "other",
                "proxy_type": "http",
                "proxy_host": proxy.host,
                "proxy_port": proxy.port,
                "proxy_user": proxy.username or "",
                "proxy_password": proxy.password or ""
            }
        }

        adspower_client = AdsPowerClient(
            api_url=settings.ADSPOWER_DEFAULT_API_URL,   # ← siempre la cuenta central
            api_key=settings.ADSPOWER_DEFAULT_API_KEY
        )

        adspower_start = time.time()  # ← FIX: medir tiempo de AdsPower
        adspower_response = await adspower_client.create_profile(adspower_data)
        adspower_response_time = (time.time() - adspower_start) * 1000  # ms

        if not isinstance(adspower_response, dict):
            raise RuntimeError(f"Unexpected AdsPower response: {type(adspower_response)}")

        if adspower_response.get("code") != 0:
            raise RuntimeError(f"AdsPower error: {adspower_response.get('msg')}")

        data = adspower_response.get("data")
        if not data or "id" not in data:
            raise RuntimeError(f"Invalid AdsPower response: {adspower_response}")

        adspower_id = data["id"]

        # Subir cookies
        if profile_config["cookies"]:
            try:
                await self._upload_cookies_to_profile(adspower_client, adspower_id, profile_config["cookies"])
            except Exception as e:
                logger.error(f"Error uploading cookies: {e}")

        db_profile = Profile(
            proxy_id=profile_in.proxy_id,
            adspower_id=adspower_id,
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_config["country"],
            city=profile_config["city"],
            timezone=profile_config["timezone"],
            language=profile_config["language"],
            device_type=profile_in.device_type,
            device_name=profile_config["device_name"],
            user_agent=profile_config["user_agent"],
            screen_resolution=profile_config["screen_resolution"],
            viewport=profile_config["viewport"],
            pixel_ratio=profile_config["pixel_ratio"],
            hardware_concurrency=profile_config["hardware_concurrency"],
            device_memory=profile_config["device_memory"],
            platform=profile_config["platform"],
            interests=profile_config["interests"],
            browsing_history=profile_config["browsing_history"],
            tags=profile_in.tags,
            meta_data={
                "device_brand": profile_config["device_brand"],
                "device_model": profile_config["device_model"],
                "os": profile_config["os"],
                "os_version": profile_config["os_version"],
                "cookies_count": len(profile_config["cookies"]),
                "remark": profile_config["remark"]
            },
            notes=profile_in.notes,
            status="ready",
            is_warmed=False
        )

        self.db.add(db_profile)
        await self.db.commit()
        await self.db.refresh(db_profile)

        # Métricas
        creation_duration = time.time() - creation_start
        if proxy.avg_response_time and proxy.avg_response_time > 0:
            proxy_latency = proxy.avg_response_time
        else:
            # Para proxies nuevos, medir latencia ahora
            import time, httpx as _httpx
            proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            try:
                start = time.time()
                async with _httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=8.0
                ) as _client:
                    await _client.get("https://api.ipify.org?format=json")
                proxy_latency = (time.time() - start) * 1000
                # Persistir para futuras consultas
                proxy.avg_response_time = proxy_latency
                await self.db.commit()
            except Exception:
                proxy_latency = 0.0
        try:
            metrics_service = MetricsService(self.db)
            await metrics_service.record_profile_creation(
                profile_id=db_profile.id,
                proxy_id=profile_in.proxy_id,
                creation_duration=creation_duration,
                proxy_latency=proxy_latency,
                device_info=profile_config,
                cookies_count=len(profile_config["cookies"]),
                adspower_response_time=adspower_response_time,
                success=True
            )
        except Exception as e:
            logger.warning(f"Error recording metrics (non-critical): {e}")

        logger.info(f"✅ Profile created: {db_profile.id} / AdsPower: {adspower_id}")
        return db_profile
    
    async def _upload_cookies_to_profile(
        self,
        adspower_client: AdsPowerClient,
        adspower_id: str,
        cookies: List[Dict]
    ) -> bool:
        """
        ✅ CORREGIDO FINAL: Sube cookies como lista de objetos
        
        AdsPower maneja la conversión a JSON internamente.
        Solo enviamos lista limpia de objetos.
        """
        
        # ✅ Convertir cookies al formato correcto de AdsPower
        formatted_cookies = []
        
        for cookie in cookies:
            # ✅ Crear objeto con tipos correctos
            formatted_cookie = {
                "name": str(cookie["name"]),
                "value": str(cookie["value"]),
                "domain": str(cookie["domain"]),
                "path": str(cookie.get("path", "/")),
                "httpOnly": bool(cookie.get("httpOnly", False)),
                "secure": bool(cookie.get("secure", True)),
            }
            
            # ✅ Agregar expirationDate solo si existe (debe ser int/float)
            if "expirationDate" in cookie and cookie["expirationDate"]:
                try:
                    formatted_cookie["expirationDate"] = int(cookie["expirationDate"])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid expirationDate for cookie {cookie['name']}, skipping")
            
            # ✅ Agregar sameSite solo si existe
            if "sameSite" in cookie and cookie["sameSite"]:
                formatted_cookie["sameSite"] = str(cookie["sameSite"])
            
            formatted_cookies.append(formatted_cookie)
        
        logger.info(f"Uploading {len(formatted_cookies)} cookies to profile {adspower_id}")
        
        # ✅ Log primera cookie para debugging
        if formatted_cookies:
            logger.debug(f"Sample cookie: {formatted_cookies[0]}")
        
        try:
            # ✅ Enviar como LISTA (no como string)
            # El AdsPowerClient manejará la conversión a JSON
            result = await adspower_client.update_profile(
                profile_id=adspower_id,
                profile_data={"cookie": formatted_cookies}
            )
            
            if result:
                logger.info(
                    f"✓ {len(formatted_cookies)} cookies uploaded successfully to profile {adspower_id}"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ Cookie upload returned false for profile {adspower_id}"
                )
                return False
        
        except Exception as e:
            logger.error(
                f"✗ Error uploading cookies to profile {adspower_id}: {e}"
            )
            return False
    

    async def get_profile(self, profile_id: int) -> Optional[Profile]:
        result = await self.db.execute(
            select(Profile).where(Profile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        skip: int = 0,
        limit: int = 100,
        computer_id: Optional[int] = None,
        status: Optional[ProfileStatus] = None,
        owner: Optional[str] = None,
        bookie: Optional[str] = None,
        cookie_status: Optional[str] = None,
    ) -> Tuple[List[Profile], int]:
        conditions = []
        if computer_id:   conditions.append(Profile.computer_id == computer_id)
        if status:        conditions.append(Profile.status == status)
        if owner:         conditions.append(Profile.owner == owner)
        if bookie:        conditions.append(Profile.bookie == bookie)
        if cookie_status: conditions.append(Profile.cookie_status == cookie_status)

        query = select(Profile)
        count_query = select(func.count()).select_from(Profile)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total = (await self.db.execute(count_query)).scalar()
        items = list((await self.db.execute(query.offset(skip).limit(limit))).scalars().all())
        return items, total

    async def update_profile(
        self,
        profile_id: int,
        profile_update: ProfileUpdate
    ) -> Profile:
        profile = await self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        update_data = profile_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        profile.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(profile)
        
        return profile

    async def delete_profile(self, profile_id: int) -> bool:
        profile = await self.get_profile(profile_id)
        if not profile:
            return False
        
        result = await self.db.execute(
            select(Computer).where(Computer.id == profile.computer_id)
        )
        computer = result.scalar_one_or_none()
        
        if computer:
            try:
                adspower_client = AdsPowerClient(
                    api_url=settings.ADSPOWER_DEFAULT_API_URL,  # ← API central
                    api_key=settings.ADSPOWER_DEFAULT_API_KEY
                )
                await adspower_client.delete_profile([profile.adspower_id])
            except Exception as e:
                logger.error(f"Failed to delete from AdsPower: {e}")
        
        await self.db.delete(profile)
        await self.db.commit()
        
        return True
    
    async def get_stats(self) -> Dict:
        from app.models.profile import ProfileStatus
        
        result = await self.db.execute(
            select(
                func.count(Profile.id).label('total'),
                func.count(Profile.id).filter(Profile.status == ProfileStatus.READY).label('ready'),
                func.count(Profile.id).filter(Profile.status == ProfileStatus.ACTIVE).label('active'),
                func.count(Profile.id).filter(Profile.is_warmed == True).label('warmed'),
                func.sum(Profile.total_sessions).label('total_sessions')
            )
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'ready': row.ready or 0,
            'active': row.active or 0,
            'warmed': row.warmed or 0,
            'total_sessions': row.total_sessions or 0
        }
    # En profile_service.py, agregar:
    async def set_adspower_id(self, profile_id: int, adspower_id: str) -> bool:
        profile = await self.get_profile(profile_id)
        if not profile:
            return False

        # Si ya fue procesado por otro agente, ignorar
        if not profile.adspower_id.startswith("pending-"):
            logger.warning(f"Profile {profile_id} ya tiene adspower_id real, ignorando duplicado")
            return False

        profile.adspower_id = adspower_id
        profile.status      = ProfileStatus.READY
        profile.updated_at  = datetime.utcnow()
        await self.db.commit()
        return True
