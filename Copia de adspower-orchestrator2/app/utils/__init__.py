# app/utils/__init__.py - VERSIÓN ACTUALIZADA
from app.utils.profile_generator import ProfileGenerator
from app.utils.mobile_devices import (
    get_random_device,
    get_device_by_id,
    get_all_devices,
    get_devices_by_type,
    get_devices_by_brand,
    get_devices_by_os,
    get_device_ids,
    get_device_stats,
    # Legacy
    get_random_mobile_device,
    get_mobile_device
)
from app.utils.cookie_generator import CookieGenerator, LocalStorageGenerator
from app.utils.soax_cities_manager import SOAXCitiesManager
__all__ = [
    # Profile Generator
    "ProfileGenerator",
    
    # Device Management
    "get_random_device",
    "get_device_by_id",
    "get_all_devices",
    "get_devices_by_type",
    "get_devices_by_brand",
    "get_devices_by_os",
    "get_device_ids",
    "get_device_stats",
    
    # Legacy compatibility
    "get_random_mobile_device",
    "get_mobile_device",
    
    # Cookie & Storage
    "CookieGenerator",
    "LocalStorageGenerator",

    # SOAX Cities Manager
    "SOAXCitiesManager"
]