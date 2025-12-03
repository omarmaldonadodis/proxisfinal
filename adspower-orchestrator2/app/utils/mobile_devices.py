# app/utils/mobile_devices.py
"""
Mobile Devices Database - Configuraciones realistas de dispositivos móviles
"""
from typing import Dict, Optional, List
import random


# Base de datos completa de dispositivos móviles
MOBILE_DEVICES_DB = {
    "iphone_14_pro": {
        "id": "iphone_14_pro",
        "name": "iPhone 14 Pro",
        "brand": "Apple",
        "model": "iPhone 14 Pro",
        "os": "iOS",
        "os_version": "16.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1179x2556",
        "viewport": "393x852",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU"
    },
    "iphone_14": {
        "id": "iphone_14",
        "name": "iPhone 14",
        "brand": "Apple",
        "model": "iPhone 14",
        "os": "iOS",
        "os_version": "16.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU"
    },
    "iphone_13_pro": {
        "id": "iphone_13_pro",
        "name": "iPhone 13 Pro",
        "brand": "Apple",
        "model": "iPhone 13 Pro",
        "os": "iOS",
        "os_version": "15.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU"
    },
    "iphone_13": {
        "id": "iphone_13",
        "name": "iPhone 13",
        "brand": "Apple",
        "model": "iPhone 13",
        "os": "iOS",
        "os_version": "15.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU"
    },
    "iphone_12": {
        "id": "iphone_12",
        "name": "iPhone 12",
        "brand": "Apple",
        "model": "iPhone 12",
        "os": "iOS",
        "os_version": "14.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 4,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple GPU"
    },
    "samsung_s23_ultra": {
        "id": "samsung_s23_ultra",
        "name": "Samsung Galaxy S23 Ultra",
        "brand": "Samsung",
        "model": "SM-S918B",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3088",
        "viewport": "480x1029",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 740"
    },
    "samsung_s23": {
        "id": "samsung_s23",
        "name": "Samsung Galaxy S23",
        "brand": "Samsung",
        "model": "SM-S911B",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2340",
        "viewport": "360x780",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 730"
    },
    "samsung_s22": {
        "id": "samsung_s22",
        "name": "Samsung Galaxy S22",
        "brand": "Samsung",
        "model": "SM-S901B",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2340",
        "viewport": "360x780",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 730"
    },
    "samsung_s21": {
        "id": "samsung_s21",
        "name": "Samsung Galaxy S21",
        "brand": "Samsung",
        "model": "SM-G991B",
        "os": "Android",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 660"
    },
    "pixel_7_pro": {
        "id": "pixel_7_pro",
        "name": "Google Pixel 7 Pro",
        "brand": "Google",
        "model": "Pixel 7 Pro",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3120",
        "viewport": "480x1040",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Google",
        "webgl_renderer": "Mali-G710"
    },
    "pixel_7": {
        "id": "pixel_7",
        "name": "Google Pixel 7",
        "brand": "Google",
        "model": "Pixel 7",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Google",
        "webgl_renderer": "Mali-G710"
    },
    "pixel_6": {
        "id": "pixel_6",
        "name": "Google Pixel 6",
        "brand": "Google",
        "model": "Pixel 6",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Google",
        "webgl_renderer": "Mali-G78"
    },
    "oneplus_11": {
        "id": "oneplus_11",
        "name": "OnePlus 11",
        "brand": "OnePlus",
        "model": "CPH2449",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; CPH2449) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3216",
        "viewport": "480x1072",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 740"
    },
    "oneplus_10_pro": {
        "id": "oneplus_10_pro",
        "name": "OnePlus 10 Pro",
        "brand": "OnePlus",
        "model": "NE2213",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; NE2213) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3216",
        "viewport": "480x1072",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 730"
    },
    "xiaomi_13_pro": {
        "id": "xiaomi_13_pro",
        "name": "Xiaomi 13 Pro",
        "brand": "Xiaomi",
        "model": "2210132C",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; 2210132C) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3200",
        "viewport": "480x1067",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 740"
    },
    "xiaomi_12": {
        "id": "xiaomi_12",
        "name": "Xiaomi 12",
        "brand": "Xiaomi",
        "model": "2201123G",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; 2201123G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "3",
        "platform": "Linux armv81",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 730"
    }
}


def get_all_devices() -> List[Dict]:
    """Retorna lista de todos los dispositivos"""
    return list(MOBILE_DEVICES_DB.values())


def get_device_by_id(device_id: str) -> Optional[Dict]:
    """
    Obtiene dispositivo por ID
    
    Args:
        device_id: ID del dispositivo (ej: "iphone_14_pro")
        
    Returns:
        Dict con configuración del dispositivo o None si no existe
    """
    return MOBILE_DEVICES_DB.get(device_id)


def get_random_mobile_device(brand: Optional[str] = None, os: Optional[str] = None) -> Dict:
    """
    Obtiene dispositivo móvil aleatorio
    
    Args:
        brand: Filtrar por marca (Apple, Samsung, Google, OnePlus, Xiaomi)
        os: Filtrar por OS (iOS, Android)
        
    Returns:
        Dict con configuración del dispositivo
    """
    devices = list(MOBILE_DEVICES_DB.values())
    
    # Filtrar por marca si se especifica
    if brand:
        devices = [d for d in devices if d["brand"].lower() == brand.lower()]
    
    # Filtrar por OS si se especifica
    if os:
        devices = [d for d in devices if d["os"].lower() == os.lower()]
    
    if not devices:
        # Si no hay resultados, devolver cualquier dispositivo
        devices = list(MOBILE_DEVICES_DB.values())
    
    return random.choice(devices)


def get_devices_by_brand(brand: str) -> List[Dict]:
    """
    Obtiene todos los dispositivos de una marca
    
    Args:
        brand: Marca (Apple, Samsung, Google, OnePlus, Xiaomi)
        
    Returns:
        Lista de dispositivos de esa marca
    """
    return [d for d in MOBILE_DEVICES_DB.values() if d["brand"].lower() == brand.lower()]


def get_devices_by_os(os: str) -> List[Dict]:
    """
    Obtiene todos los dispositivos de un OS
    
    Args:
        os: Sistema operativo (iOS, Android)
        
    Returns:
        Lista de dispositivos con ese OS
    """
    return [d for d in MOBILE_DEVICES_DB.values() if d["os"].lower() == os.lower()]


def get_device_ids() -> List[str]:
    """Retorna lista de IDs de dispositivos disponibles"""
    return list(MOBILE_DEVICES_DB.keys())


# Compatibilidad con código legacy
def get_mobile_device(device_id: Optional[str] = None) -> Dict:
    """
    Obtiene dispositivo por ID o aleatorio
    
    Args:
        device_id: ID del dispositivo (opcional)
        
    Returns:
        Dict con configuración del dispositivo
    """
    if device_id and device_id in MOBILE_DEVICES_DB:
        return MOBILE_DEVICES_DB[device_id]
    return get_random_mobile_device()