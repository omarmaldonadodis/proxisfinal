from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime

from app.models.profile import Profile
from app.models.computer import Computer
from app.models.proxy import Proxy
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.integrations.adspower_client import AdsPowerClient
from app.utils.profile_generator import ProfileGenerator


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(self, profile_in: ProfileCreate) -> Profile:
        """Create a new browser profile"""
        
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
        
        # Generate profile config
        profile_config = ProfileGenerator.generate_profile(
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_in.country,
            city=profile_in.city,
            device_type=profile_in.device_type
        )
        
        # Create profile in AdsPower
        adspower_client = AdsPowerClient(
            api_url=computer.adspower_api_url,
            api_key=computer.adspower_api_key
        )
        
        # Convert screen_resolution format
        screen_res = profile_config.get("screen_resolution", "1920x1080")
        screen_res = screen_res.replace("x", "_")
        
        fingerprint_config = {
            "automatic_timezone": "1",
            "timezone": profile_config.get("timezone", "America/New_York"),
            "webrtc": "proxy",
            "location": "ask",
            "language": [profile_config.get("language", "en-US")],
            "page_language": [profile_config.get("language", "en-US")],
            "ua": profile_config.get("user_agent", ""),
            "screen_resolution": screen_res,
            "fonts": ["all"],
            "canvas": "1",
            "webgl_image": "1",
            "webgl": "1",
            "audio": "1",
            "do_not_track": "default",
            "hardware_concurrency": str(profile_config.get("hardware_concurrency", 4)),
            "device_memory": str(profile_config.get("device_memory", 4)),
            "flash": "block"
        }
        
        adspower_data = {
            "name": profile_in.name,
            "group_id": "0",
            "fingerprint_config": fingerprint_config
        }
        
        # Add proxy config
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
        
        # Create in AdsPower
        adspower_response = await adspower_client.create_profile(adspower_data)
        
        # Handle response validation
        if isinstance(adspower_response, str):
            raise RuntimeError(f"AdsPower returned error: {adspower_response}")
        
        if not isinstance(adspower_response, dict):
            raise RuntimeError(f"Unexpected AdsPower response type: {type(adspower_response)}")
        
        if adspower_response.get("code") != 0:
            error_msg = adspower_response.get("msg", "Unknown error")
            raise RuntimeError(f"Failed to create profile in AdsPower: {error_msg}")
        
        # Get profile ID from response
        data = adspower_response.get("data")
        if not data or "id" not in data:
            raise RuntimeError(f"Invalid AdsPower response: {adspower_response}")
        
        adspower_id = data["id"]  # ✅ FIX: Usar variable correcta
        
        # Create in database
        db_profile = Profile(
            computer_id=profile_in.computer_id,
            proxy_id=profile_in.proxy_id,
            adspower_id=adspower_id,  # ✅ FIX: Campo correcto
            name=profile_in.name,
            age=profile_in.age,
            gender=profile_in.gender,
            country=profile_in.country,
            city=profile_in.city,
            timezone=profile_in.timezone or profile_config.get("timezone"),
            language=profile_in.language or profile_config.get("language"),
            device_type=profile_in.device_type,
            device_name=profile_in.device_name or profile_config.get("device_name"),
            user_agent=profile_config.get("user_agent"),
            screen_resolution=profile_config.get("screen_resolution"),
            viewport=profile_config.get("viewport"),
            pixel_ratio=profile_config.get("pixel_ratio"),
            hardware_concurrency=profile_config.get("hardware_concurrency"),
            device_memory=profile_config.get("device_memory"),
            platform=profile_config.get("platform"),
            interests=profile_in.interests or profile_config.get("interests", []),
            browsing_history=profile_config.get("browsing_history", []),
            tags=profile_in.tags,
            meta_data=profile_in.meta_data,
            notes=profile_in.notes,
            status="ready",  # ✅ Cambiar a "ready" ya que se creó exitosamente
            is_warmed=False
        )
        
        self.db.add(db_profile)
        await self.db.commit()
        await self.db.refresh(db_profile)
        
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
                await adspower_client.delete_profile([profile.adspower_id])  # ✅ FIX
            except Exception as e:
                print(f"Failed to delete from AdsPower: {e}")
        
        await self.db.delete(profile)
        await self.db.commit()
        
        return True
