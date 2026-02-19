# app/utils/mobile_devices.py - VERSIÓN EXPANDIDA CON TABLETS
"""
Base de datos expandida: 50+ dispositivos (Mobile, Tablet, Desktop)
Configuraciones ultra-realistas con diversidad máxima
"""
from typing import Dict, Optional, List
import random

# ========================================
# MOBILE DEVICES (iOS + Android)
# ========================================
MOBILE_DEVICES_DB = {
    # iPhone (iOS)
    "iphone_15_pro_max": {
        "id": "iphone_15_pro_max",
        "name": "iPhone 15 Pro Max",
        "brand": "Apple",
        "model": "iPhone15,3",
        "os": "iOS",
        "os_version": "17.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1290x2796",
        "viewport": "430x932",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 8,
        "device_type": "mobile"
    },
    "iphone_15_pro": {
        "id": "iphone_15_pro",
        "name": "iPhone 15 Pro",
        "brand": "Apple",
        "model": "iPhone15,2",
        "os": "iOS",
        "os_version": "17.1",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1179x2556",
        "viewport": "393x852",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 8,
        "device_type": "mobile"
    },
    "iphone_15": {
        "id": "iphone_15",
        "name": "iPhone 15",
        "brand": "Apple",
        "model": "iPhone15,4",
        "os": "iOS",
        "os_version": "17.0",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1179x2556",
        "viewport": "393x852",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_14_pro_max": {
        "id": "iphone_14_pro_max",
        "name": "iPhone 14 Pro Max",
        "brand": "Apple",
        "model": "iPhone14,8",
        "os": "iOS",
        "os_version": "16.6",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1290x2796",
        "viewport": "430x932",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_14_pro": {
        "id": "iphone_14_pro",
        "name": "iPhone 14 Pro",
        "brand": "Apple",
        "model": "iPhone14,7",
        "os": "iOS",
        "os_version": "16.5",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1179x2556",
        "viewport": "393x852",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_14": {
        "id": "iphone_14",
        "name": "iPhone 14",
        "brand": "Apple",
        "model": "iPhone14,5",
        "os": "iOS",
        "os_version": "16.4",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_13_pro": {
        "id": "iphone_13_pro",
        "name": "iPhone 13 Pro",
        "brand": "Apple",
        "model": "iPhone14,2",
        "os": "iOS",
        "os_version": "15.7",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.7 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_13": {
        "id": "iphone_13",
        "name": "iPhone 13",
        "brand": "Apple",
        "model": "iPhone14,5",
        "os": "iOS",
        "os_version": "15.6",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 4,
        "device_type": "mobile"
    },
    "iphone_12_pro": {
        "id": "iphone_12_pro",
        "name": "iPhone 12 Pro",
        "brand": "Apple",
        "model": "iPhone13,3",
        "os": "iOS",
        "os_version": "14.8",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.8 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 6,
        "device_type": "mobile"
    },
    "iphone_12": {
        "id": "iphone_12",
        "name": "iPhone 12",
        "brand": "Apple",
        "model": "iPhone13,2",
        "os": "iOS",
        "os_version": "14.7",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.7 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1170x2532",
        "viewport": "390x844",
        "pixel_ratio": "3",
        "platform": "iPhone",
        "hardware_concurrency": 6,
        "device_memory": 4,
        "device_type": "mobile"
    },
    
    # Samsung Galaxy (Android)
    "samsung_s24_ultra": {
        "id": "samsung_s24_ultra",
        "name": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "model": "SM-S928B",
        "os": "Android",
        "os_version": "14",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3120",
        "viewport": "480x1040",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 12,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
    },
    "samsung_s22_ultra": {
        "id": "samsung_s22_ultra",
        "name": "Samsung Galaxy S22 Ultra",
        "brand": "Samsung",
        "model": "SM-S908B",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3088",
        "viewport": "480x1029",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
    },
    
    # Google Pixel (Android)
    "pixel_8_pro": {
        "id": "pixel_8_pro",
        "name": "Google Pixel 8 Pro",
        "brand": "Google",
        "model": "Pixel 8 Pro",
        "os": "Android",
        "os_version": "14",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1344x2992",
        "viewport": "448x997",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 12,
        "device_type": "mobile"
    },
    "pixel_8": {
        "id": "pixel_8",
        "name": "Google Pixel 8",
        "brand": "Google",
        "model": "Pixel 8",
        "os": "Android",
        "os_version": "14",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
    },
    "pixel_6a": {
        "id": "pixel_6a",
        "name": "Google Pixel 6a",
        "brand": "Google",
        "model": "Pixel 6a",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1080x2400",
        "viewport": "360x800",
        "pixel_ratio": "2.75",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 6,
        "device_type": "mobile"
    },
    
    # OnePlus (Android)
    "oneplus_12": {
        "id": "oneplus_12",
        "name": "OnePlus 12",
        "brand": "OnePlus",
        "model": "CPH2583",
        "os": "Android",
        "os_version": "14",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; CPH2583) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3168",
        "viewport": "480x1056",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 12,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
    },
    
    # Xiaomi (Android)
    "xiaomi_14_pro": {
        "id": "xiaomi_14_pro",
        "name": "Xiaomi 14 Pro",
        "brand": "Xiaomi",
        "model": "23116PN5BC",
        "os": "Android",
        "os_version": "14",
        "user_agent": "Mozilla/5.0 (Linux; Android 14; 23116PN5BC) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "screen_resolution": "1440x3200",
        "viewport": "480x1067",
        "pixel_ratio": "3",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 12,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
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
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "mobile"
    },
}

# ========================================
# TABLET DEVICES (NEW!)
# ========================================
TABLET_DEVICES_DB = {
    # iPad (iOS)
    "ipad_pro_13": {
        "id": "ipad_pro_13",
        "name": "iPad Pro 13-inch (M4)",
        "brand": "Apple",
        "model": "iPad14,6",
        "os": "iPadOS",
        "os_version": "17.1",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "screen_resolution": "2064x2752",
        "viewport": "1024x1366",
        "pixel_ratio": "2",
        "platform": "iPad",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
    "ipad_pro_11": {
        "id": "ipad_pro_11",
        "name": "iPad Pro 11-inch",
        "brand": "Apple",
        "model": "iPad14,5",
        "os": "iPadOS",
        "os_version": "17.0",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1668x2388",
        "viewport": "834x1194",
        "pixel_ratio": "2",
        "platform": "iPad",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
    "ipad_air_5": {
        "id": "ipad_air_5",
        "name": "iPad Air (5th gen)",
        "brand": "Apple",
        "model": "iPad13,16",
        "os": "iPadOS",
        "os_version": "16.6",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1640x2360",
        "viewport": "820x1180",
        "pixel_ratio": "2",
        "platform": "iPad",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
    "ipad_10": {
        "id": "ipad_10",
        "name": "iPad (10th gen)",
        "brand": "Apple",
        "model": "iPad13,18",
        "os": "iPadOS",
        "os_version": "16.5",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1640x2360",
        "viewport": "820x1180",
        "pixel_ratio": "2",
        "platform": "iPad",
        "hardware_concurrency": 6,
        "device_memory": 4,
        "device_type": "tablet"
    },
    "ipad_mini_6": {
        "id": "ipad_mini_6",
        "name": "iPad mini (6th gen)",
        "brand": "Apple",
        "model": "iPad14,1",
        "os": "iPadOS",
        "os_version": "16.4",
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
        "screen_resolution": "1488x2266",
        "viewport": "744x1133",
        "pixel_ratio": "2",
        "platform": "iPad",
        "hardware_concurrency": 6,
        "device_memory": 4,
        "device_type": "tablet"
    },
    
    # Samsung Galaxy Tab (Android)
    "galaxy_tab_s9_ultra": {
        "id": "galaxy_tab_s9_ultra",
        "name": "Samsung Galaxy Tab S9 Ultra",
        "brand": "Samsung",
        "model": "SM-X916B",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-X916B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "screen_resolution": "1848x2960",
        "viewport": "1232x1973",
        "pixel_ratio": "2",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 12,
        "device_type": "tablet"
    },
    "galaxy_tab_s9": {
        "id": "galaxy_tab_s9",
        "name": "Samsung Galaxy Tab S9",
        "brand": "Samsung",
        "model": "SM-X710",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "screen_resolution": "1600x2560",
        "viewport": "800x1280",
        "pixel_ratio": "2",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
    "galaxy_tab_s8": {
        "id": "galaxy_tab_s8",
        "name": "Samsung Galaxy Tab S8",
        "brand": "Samsung",
        "model": "SM-X706B",
        "os": "Android",
        "os_version": "12",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; SM-X706B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "screen_resolution": "1600x2560",
        "viewport": "800x1280",
        "pixel_ratio": "2",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
    
    # Google Pixel Tablet
    "pixel_tablet": {
        "id": "pixel_tablet",
        "name": "Google Pixel Tablet",
        "brand": "Google",
        "model": "Pixel Tablet",
        "os": "Android",
        "os_version": "13",
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel Tablet) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "screen_resolution": "1600x2560",
        "viewport": "800x1280",
        "pixel_ratio": "2",
        "platform": "Linux armv8l",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "tablet"
    },
}

# ========================================
# DESKTOP DEVICES
# ========================================
DESKTOP_DEVICES_DB = {
    # MacBook Pro (macOS)
    "macbook_pro_16_m3_max": {
        "id": "macbook_pro_16_m3_max",
        "name": "MacBook Pro 16-inch (M3 Max)",
        "brand": "Apple",
        "model": "MacBookPro18,4",
        "os": "macOS",
        "os_version": "14.1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "screen_resolution": "3456x2234",
        "viewport": "1728x1117",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 16,
        "device_memory": 64,
        "device_type": "desktop"
    },
    "macbook_pro_16_m2": {
        "id": "macbook_pro_16_m2",
        "name": "MacBook Pro 16-inch (M2 Pro)",
        "brand": "Apple",
        "model": "MacBookPro18,2",
        "os": "macOS",
        "os_version": "13.6",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "screen_resolution": "3456x2234",
        "viewport": "1728x1117",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 12,
        "device_memory": 32,
        "device_type": "desktop"
    },
    "macbook_pro_14_m3": {
        "id": "macbook_pro_14_m3",
        "name": "MacBook Pro 14-inch (M3)",
        "brand": "Apple",
        "model": "MacBookPro18,3",
        "os": "macOS",
        "os_version": "14.0",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "screen_resolution": "3024x1964",
        "viewport": "1512x982",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 11,
        "device_memory": 16,
        "device_type": "desktop"
    },
    "macbook_air_15_m2": {
        "id": "macbook_air_15_m2",
        "name": "MacBook Air 15-inch (M2)",
        "brand": "Apple",
        "model": "MacBookAir10,1",
        "os": "macOS",
        "os_version": "13.5",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "screen_resolution": "2880x1864",
        "viewport": "1440x932",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 8,
        "device_memory": 16,
        "device_type": "desktop"
    },
    "macbook_air_13_m2": {
        "id": "macbook_air_13_m2",
        "name": "MacBook Air 13-inch (M2)",
        "brand": "Apple",
        "model": "MacBookAir10,1",
        "os": "macOS",
        "os_version": "13.4",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "screen_resolution": "2560x1664",
        "viewport": "1280x832",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 8,
        "device_memory": 8,
        "device_type": "desktop"
    },
    "imac_24_m3": {
        "id": "imac_24_m3",
        "name": "iMac 24-inch (M3)",
        "brand": "Apple",
        "model": "iMac21,1",
        "os": "macOS",
        "os_version": "14.1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "screen_resolution": "4480x2520",
        "viewport": "2240x1260",
        "pixel_ratio": "2",
        "platform": "MacIntel",
        "hardware_concurrency": 8,
        "device_memory": 16,
        "device_type": "desktop"
    },
    
    # Windows Desktop
    "windows_gaming_rtx4090": {
        "id": "windows_gaming_rtx4090",
        "name": "Windows Gaming PC (RTX 4090)",
        "brand": "Custom",
        "model": "Desktop",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "screen_resolution": "3840x2160",
        "viewport": "3840x2160",
        "pixel_ratio": "1",
        "platform": "Win32",
        "hardware_concurrency": 16,
        "device_memory": 64,
        "device_type": "desktop"
    },
    "windows_workstation_rtx4080": {
        "id": "windows_workstation_rtx4080",
        "name": "Windows Workstation (RTX 4080)",
        "brand": "Custom",
        "model": "Desktop",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "screen_resolution": "2560x1440",
        "viewport": "2560x1440",
        "pixel_ratio": "1",
        "platform": "Win32",
        "hardware_concurrency": 12,
        "device_memory": 32,
        "device_type": "desktop"
    },
    "windows_office_pc": {
        "id": "windows_office_pc",
        "name": "Windows Office PC",
        "brand": "Dell",
        "model": "OptiPlex 7090",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "screen_resolution": "1920x1080",
        "viewport": "1920x1080",
        "pixel_ratio": "1",
        "platform": "Win32",
        "hardware_concurrency": 8,
        "device_memory": 16,
        "device_type": "desktop"
    },
    "windows_laptop_dell": {
        "id": "windows_laptop_dell",
        "name": "Dell XPS 15",
        "brand": "Dell",
        "model": "XPS 15 9530",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "screen_resolution": "3840x2400",
        "viewport": "1920x1200",
        "pixel_ratio": "2",
        "platform": "Win32",
        "hardware_concurrency": 14,
        "device_memory": 32,
        "device_type": "desktop"
    },
    "windows_laptop_hp": {
        "id": "windows_laptop_hp",
        "name": "HP Spectre x360",
        "brand": "HP",
        "model": "Spectre x360 16",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "screen_resolution": "3072x1920",
        "viewport": "1536x960",
        "pixel_ratio": "2",
        "platform": "Win32",
        "hardware_concurrency": 12,
        "device_memory": 16,
        "device_type": "desktop"
    },
    "windows_laptop_lenovo": {
        "id": "windows_laptop_lenovo",
        "name": "Lenovo ThinkPad X1 Carbon",
        "brand": "Lenovo",
        "model": "ThinkPad X1 Carbon Gen 11",
        "os": "Windows",
        "os_version": "11",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "screen_resolution": "2560x1600",
        "viewport": "1280x800",
        "pixel_ratio": "2",
        "platform": "Win32",
        "hardware_concurrency": 12,
        "device_memory": 16,
        "device_type": "desktop"
    },
    
    # Linux Desktop
    "linux_workstation": {
        "id": "linux_workstation",
        "name": "Linux Workstation (Ubuntu)",
        "brand": "Custom",
        "model": "Desktop",
        "os": "Linux",
        "os_version": "22.04",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "screen_resolution": "2560x1440",
        "viewport": "2560x1440",
        "pixel_ratio": "1",
        "platform": "Linux x86_64",
        "hardware_concurrency": 16,
        "device_memory": 32,
        "device_type": "desktop"
    },
}

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_all_devices() -> List[Dict]:
    """Retorna TODOS los dispositivos (mobile + tablet + desktop)"""
    all_devices = []
    all_devices.extend(list(MOBILE_DEVICES_DB.values()))
    all_devices.extend(list(TABLET_DEVICES_DB.values()))
    all_devices.extend(list(DESKTOP_DEVICES_DB.values()))
    return all_devices


def get_device_by_id(device_id: str) -> Optional[Dict]:
    """Obtiene dispositivo por ID desde cualquier categoría"""
    # Buscar en mobile
    if device_id in MOBILE_DEVICES_DB:
        return MOBILE_DEVICES_DB[device_id]
    # Buscar en tablet
    if device_id in TABLET_DEVICES_DB:
        return TABLET_DEVICES_DB[device_id]
    # Buscar en desktop
    if device_id in DESKTOP_DEVICES_DB:
        return DESKTOP_DEVICES_DB[device_id]
    return None


def get_random_device(device_type: Optional[str] = None, brand: Optional[str] = None, os: Optional[str] = None) -> Dict:
    """
    Obtiene dispositivo aleatorio
    
    Args:
        device_type: "mobile", "tablet", "desktop" (None = cualquiera)
        brand: "Apple", "Samsung", "Google", etc.
        os: "iOS", "Android", "macOS", "Windows", "Linux"
    """
    devices = get_all_devices()
    
    # Filtrar por tipo
    if device_type:
        devices = [d for d in devices if d.get("device_type") == device_type]
    
    # Filtrar por marca
    if brand:
        devices = [d for d in devices if d["brand"].lower() == brand.lower()]
    
    # Filtrar por OS
    if os:
        devices = [d for d in devices if d["os"].lower() == os.lower()]
    
    if not devices:
        # Si no hay resultados, devolver cualquier dispositivo
        devices = get_all_devices()
    
    return random.choice(devices)


def get_devices_by_type(device_type: str) -> List[Dict]:
    """Obtiene todos los dispositivos de un tipo"""
    if device_type == "mobile":
        return list(MOBILE_DEVICES_DB.values())
    elif device_type == "tablet":
        return list(TABLET_DEVICES_DB.values())
    elif device_type == "desktop":
        return list(DESKTOP_DEVICES_DB.values())
    else:
        return get_all_devices()


def get_devices_by_brand(brand: str) -> List[Dict]:
    """Obtiene todos los dispositivos de una marca"""
    all_devices = get_all_devices()
    return [d for d in all_devices if d["brand"].lower() == brand.lower()]


def get_devices_by_os(os: str) -> List[Dict]:
    """Obtiene todos los dispositivos de un OS"""
    all_devices = get_all_devices()
    return [d for d in all_devices if d["os"].lower() == os.lower()]


def get_device_ids() -> List[str]:
    """Retorna lista de todos los IDs de dispositivos disponibles"""
    ids = []
    ids.extend(list(MOBILE_DEVICES_DB.keys()))
    ids.extend(list(TABLET_DEVICES_DB.keys()))
    ids.extend(list(DESKTOP_DEVICES_DB.keys()))
    return ids


def get_device_stats() -> Dict:
    """Estadísticas de dispositivos disponibles"""
    return {
        "total": len(get_all_devices()),
        "mobile": len(MOBILE_DEVICES_DB),
        "tablet": len(TABLET_DEVICES_DB),
        "desktop": len(DESKTOP_DEVICES_DB),
        "brands": len(set(d["brand"] for d in get_all_devices())),
        "os_types": len(set(d["os"] for d in get_all_devices()))
    }


# Compatibilidad con código legacy
def get_random_mobile_device(brand: Optional[str] = None, os: Optional[str] = None) -> Dict:
    """Legacy function - obtiene dispositivo móvil aleatorio"""
    return get_random_device(device_type="mobile", brand=brand, os=os)


def get_mobile_device(device_id: Optional[str] = None) -> Dict:
    """Legacy function - obtiene dispositivo por ID o aleatorio"""
    if device_id:
        device = get_device_by_id(device_id)
        if device:
            return device
    return get_random_device(device_type="mobile")