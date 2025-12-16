# app/services/profile_service.py - VERSIÓN ULTRA-REALISTA
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime

from app.models.profile import Profile, DeviceType
from app.models.computer import Computer
from app.models.proxy import Proxy
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.integrations.adspower_client import AdsPowerClient
from app.utils.profile_generator import ProfileGenerator  # ✅ NUEVO
from loguru import logger


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(self, profile_in: ProfileCreate) -> Profile:
        """
        Create profile with HYPER-REALISTIC fingerprinting
        
        Incluye:
        - 50+ dispositivos (mobile, tablet, desktop)
        - Cookies pre-cargadas
        - LocalStorage/SessionStorage
        - Remarks ultra-variados
        """
        
        # ========================================
        # 1. VALIDACIONES INICIALES
        # ========================================
        
        # Get computer
        result = await self.db.execute(
            select(Computer).where(Computer.id == profile_in.computer_id)
        )
        computer = result.scalar_one_or_none()
        if not computer:
            raise ValueError(f"Computer {profile_in.computer_id} not found")
        
        # Get proxy - ES OBLIGATORIO
        if not profile_in.proxy_id:
            raise ValueError("proxy_id is required - AdsPower profiles need a proxy")
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == profile_in.proxy_id)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            raise ValueError(f"Proxy {profile_in.proxy_id} not found")
        
        # ========================================
        # 2. GENERAR FINGERPRINT ULTRA-REALISTA
        # ========================================
        
        profile_config = ProfileGenerator.generate_profile(
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_in.country or proxy.country or "EC",
            city=profile_in.city or proxy.city,
            device_type=profile_in.device_type.value,  # mobile, tablet, desktop
            include_cookies=True,  # ✅ INCLUIR COOKIES
            include_localstorage=True  # ✅ INCLUIR LOCALSTORAGE
        )
        
        logger.info(
            f"Generated profile config: {profile_config['name']}, "
            f"Device: {profile_config['device_name']}, "
            f"Cookies: {len(profile_config['cookies'])}"
        )
        
        # ========================================
        # 3. CONFIGURAR FINGERPRINT PARA ADSPOWER
        # ========================================
        
        # Convertir resolución al formato AdsPower (1920x1080 -> 1920_1080)
        screen_res = profile_config["screen_resolution"].replace("x", "_")
        
        fingerprint_config = {
            # Timezone
            "automatic_timezone": "0",  # Manual
            "timezone": profile_config["timezone"],
            
            # WebRTC
            "webrtc": "proxy",  # Usar IP del proxy
            
            # Geolocation
            "location": "ask",  # Preguntar al usuario
            
            # Language
            "language": [profile_config["language"]],
            "page_language": [profile_config["language"]],
            
            # User Agent
            "ua": profile_config["user_agent"],
            
            # Screen
            "screen_resolution": screen_res,
            
            # Fonts
            "fonts": ["all"],
            
            # Canvas & WebGL (noise para anti-detección)
            "canvas": "1",  # Noise mode
            "webgl_image": "1",  # Noise mode
            "webgl": "1",  # Noise mode
            
            # Audio
            "audio": "1",  # Noise mode
            
            # Do Not Track
            "do_not_track": "default",
            
            # Hardware
            "hardware_concurrency": str(profile_config["hardware_concurrency"]),
            "device_memory": str(profile_config["device_memory"]),
            
            # Flash (bloqueado por defecto)
            "flash": "block",
            
            # Media Devices
            "media_devices": "1",  # Random
            
            # Client Rects
            "client_rects": "1",  # Noise
            
            # Speech Voices
            "speech_voices": "1",  # Noise
        }
        
        # ========================================
        # 4. PREPARAR DATOS PARA ADSPOWER API
        # ========================================
        
        adspower_data = {
            "name": profile_in.name,
            "group_id": getattr(profile_in, 'group_id', "0"),
            "fingerprint_config": fingerprint_config,
            
            # ✅ REMARK ULTRA-VARIADO
            "remark": profile_config["remark"],
            
            # ✅ COOKIES PRE-CARGADAS
            "cookies": profile_config["cookies"],
            
            # ✅ LOCALSTORAGE PRE-CARGADO (si AdsPower lo soporta)
            # Nota: AdsPower puede no soportar LocalStorage directo,
            # pero podemos inyectarlo después con extensión/script
            "user_data": {
                "localstorage": profile_config["localstorage"],
                "sessionstorage": profile_config["sessionstorage"]
            }
        }
        
        # Tags (usar intereses como tags)
        if profile_in.tags and len(profile_in.tags) > 0:
            adspower_data["remark"] += " | Tags: " + ", ".join(profile_in.tags)
        
        # ========================================
        # 5. CONFIGURAR PROXY (SOAX)
        # ========================================
        
        proxy_type_map = {
            "http": "http",
            "https": "https",
            "socks5": "socks5",
            "mobile": "http",
            "residential": "http",
            "datacenter": "http"
        }
        
        adspower_data["user_proxy_config"] = {
            "proxy_soft": "other",
            "proxy_type": proxy_type_map.get(proxy.proxy_type, "http"),
            "proxy_host": proxy.host,
            "proxy_port": proxy.port,
            "proxy_user": proxy.username or "",
            "proxy_password": proxy.password or ""
        }
        
        # ========================================
        # 6. CREAR PROFILE EN ADSPOWER
        # ========================================
        
        adspower_client = AdsPowerClient(
            api_url=computer.adspower_api_url,
            api_key=computer.adspower_api_key
        )
        
        adspower_response = await adspower_client.create_profile(adspower_data)
        
        # Validar respuesta
        if isinstance(adspower_response, str):
            raise RuntimeError(f"AdsPower returned error: {adspower_response}")
        
        if not isinstance(adspower_response, dict):
            raise RuntimeError(f"Unexpected AdsPower response type: {type(adspower_response)}")
        
        if adspower_response.get("code") != 0:
            error_msg = adspower_response.get("msg", "Unknown error")
            raise RuntimeError(f"Failed to create profile in AdsPower: {error_msg}")
        
        # Obtener AdsPower ID
        data = adspower_response.get("data")
        if not data or "id" not in data:
            raise RuntimeError(f"Invalid AdsPower response: {adspower_response}")
        
        adspower_id = data["id"]
        
        logger.info(
            f"✓ Profile created in AdsPower: {adspower_id}, "
            f"Cookies: {len(profile_config['cookies'])}, "
            f"Device: {profile_config['device_name']}"
        )
        
        # ========================================
        # 7. GUARDAR EN BASE DE DATOS
        # ========================================
        
        db_profile = Profile(
            computer_id=profile_in.computer_id,
            proxy_id=profile_in.proxy_id,
            adspower_id=adspower_id,
            
            # Datos básicos
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_config["country"],
            city=profile_config["city"],
            timezone=profile_config["timezone"],
            language=profile_config["language"],
            
            # Device info
            device_type=profile_in.device_type,
            device_name=profile_config["device_name"],
            user_agent=profile_config["user_agent"],
            screen_resolution=profile_config["screen_resolution"],
            viewport=profile_config["viewport"],
            pixel_ratio=profile_config["pixel_ratio"],
            hardware_concurrency=profile_config["hardware_concurrency"],
            device_memory=profile_config["device_memory"],
            platform=profile_config["platform"],
            
            # Profile data
            interests=profile_config["interests"],
            browsing_history=profile_config["browsing_history"],
            
            # Metadata
            tags=profile_in.tags,
            meta_data={
                "device_brand": profile_config["device_brand"],
                "device_model": profile_config["device_model"],
                "os": profile_config["os"],
                "os_version": profile_config["os_version"],
                "cookies_count": len(profile_config["cookies"]),
                "localstorage_keys": len(profile_config["localstorage"]),
                "remark": profile_config["remark"]
            },
            notes=profile_in.notes,
            
            # Status
            status="ready",
            is_warmed=False
        )
        
        self.db.add(db_profile)
        await self.db.commit()
        await self.db.refresh(db_profile)
        
        logger.info(
            f"✓ Profile saved in DB: ID={db_profile.id}, "
            f"AdsPower ID={adspower_id}, "
            f"Device={profile_config['device_name']}"
        )
        
        return db_profile

    async def get_profile(self, profile_id: int) -> Optional[Profile]:
        result = await self.db.execute(
            select(Profile).where(Profile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        computer_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Profile], int]:
        query = select(Profile)
        count_query = select(func.count()).select_from(Profile)
        
        conditions = []
        if computer_id:
            conditions.append(Profile.computer_id == computer_id)
        if status:
            conditions.append(Profile.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
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
                    api_url=computer.adspower_api_url,
                    api_key=computer.adspower_api_key
                )
                await adspower_client.delete_profile([profile.adspower_id])
            except Exception as e:
                logger.error(f"Failed to delete from AdsPower: {e}")
        
        await self.db.delete(profile)
        await self.db.commit()
        
        return True
    
    async def get_stats(self) -> Dict:
        """Obtiene estadísticas de profiles"""
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