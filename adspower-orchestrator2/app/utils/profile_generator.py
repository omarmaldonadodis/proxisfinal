# app/utils/profile_generator.py
"""
Profile Generator - Genera configuraciones realistas de perfiles para AdsPower
"""
import random
import string
from typing import Dict, List, Optional
from datetime import datetime


class ProfileGenerator:
    """Generador de perfiles con fingerprints realistas"""
    
    # Nombres por género
    MALE_NAMES = [
        "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
        "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
        "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
        "George", "Edward", "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan", "Jacob"
    ]
    
    FEMALE_NAMES = [
        "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
        "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
        "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
        "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon"
    ]
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young"
    ]
    
    # Dispositivos móviles
    MOBILE_DEVICES = [
        {
            "name": "iPhone 14 Pro",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "resolution": "1179x2556",
            "viewport": "393x852",
            "pixel_ratio": "3",
            "platform": "iPhone"
        },
        {
            "name": "iPhone 13",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "resolution": "1170x2532",
            "viewport": "390x844",
            "pixel_ratio": "3",
            "platform": "iPhone"
        },
        {
            "name": "Samsung Galaxy S23",
            "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            "resolution": "1080x2340",
            "viewport": "360x780",
            "pixel_ratio": "3",
            "platform": "Linux armv81"
        },
        {
            "name": "Samsung Galaxy S22",
            "user_agent": "Mozilla/5.0 (Linux; Android 12; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36",
            "resolution": "1080x2340",
            "viewport": "360x780",
            "pixel_ratio": "3",
            "platform": "Linux armv81"
        },
        {
            "name": "Google Pixel 7",
            "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            "resolution": "1080x2400",
            "viewport": "360x800",
            "pixel_ratio": "3",
            "platform": "Linux armv81"
        },
        {
            "name": "OnePlus 11",
            "user_agent": "Mozilla/5.0 (Linux; Android 13; CPH2449) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            "resolution": "1440x3216",
            "viewport": "480x1072",
            "pixel_ratio": "3",
            "platform": "Linux armv81"
        }
    ]
    
    # Dispositivos desktop
    DESKTOP_CONFIGS = [
        {
            "name": "MacBook Pro 16",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "resolution": "1728x1117",
            "viewport": "1728x1117",
            "pixel_ratio": "2",
            "platform": "MacIntel",
            "hardware_concurrency": 10,
            "device_memory": 16
        },
        {
            "name": "Windows Desktop",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "resolution": "1920x1080",
            "viewport": "1920x1080",
            "pixel_ratio": "1",
            "platform": "Win32",
            "hardware_concurrency": 8,
            "device_memory": 8
        },
        {
            "name": "MacBook Air",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "resolution": "1440x900",
            "viewport": "1440x900",
            "pixel_ratio": "2",
            "platform": "MacIntel",
            "hardware_concurrency": 8,
            "device_memory": 8
        }
    ]
    
    # Timezones por país
    TIMEZONES = {
        "US": ["America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver"],
        "GB": ["Europe/London"],
        "CA": ["America/Toronto", "America/Vancouver"],
        "AU": ["Australia/Sydney", "Australia/Melbourne"],
        "DE": ["Europe/Berlin"],
        "FR": ["Europe/Paris"],
        "ES": ["Europe/Madrid"],
        "IT": ["Europe/Rome"],
        "BR": ["America/Sao_Paulo"],
        "MX": ["America/Mexico_City"],
        "AR": ["America/Argentina/Buenos_Aires"],
        "JP": ["Asia/Tokyo"],
        "KR": ["Asia/Seoul"],
        "IN": ["Asia/Kolkata"],
    }
    
    # Idiomas por país
    LANGUAGES = {
        "US": "en-US",
        "GB": "en-GB",
        "CA": "en-CA",
        "AU": "en-AU",
        "DE": "de-DE",
        "FR": "fr-FR",
        "ES": "es-ES",
        "IT": "it-IT",
        "BR": "pt-BR",
        "MX": "es-MX",
        "AR": "es-AR",
        "JP": "ja-JP",
        "KR": "ko-KR",
        "IN": "en-IN",
    }
    
    # Intereses realistas
    INTERESTS = [
        "technology", "sports", "travel", "food", "fashion", "music", "movies",
        "gaming", "fitness", "photography", "art", "books", "cooking", "shopping",
        "news", "business", "health", "education", "entertainment", "science"
    ]
    
    # URLs para browsing history
    POPULAR_SITES = [
        "google.com", "youtube.com", "facebook.com", "twitter.com", "instagram.com",
        "linkedin.com", "reddit.com", "wikipedia.org", "amazon.com", "netflix.com",
        "cnn.com", "bbc.com", "espn.com", "weather.com", "yahoo.com"
    ]
    
    @classmethod
    def generate_profile(
        cls,
        name: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        country: str = "US",
        city: Optional[str] = None,
        device_type: str = "mobile"
    ) -> Dict:
        """
        Genera configuración completa de perfil
        
        Args:
            name: Nombre del perfil (genera automático si None)
            age: Edad (random 25-45 si None)
            gender: male/female (random si None)
            country: Código país ISO 2 letras
            city: Ciudad (genera automática si None)
            device_type: mobile o desktop
            
        Returns:
            Dict con configuración completa del perfil
        """
        # Generar datos básicos
        if not gender:
            gender = random.choice(["male", "female"])
        
        if not name:
            first_name = random.choice(cls.MALE_NAMES if gender == "male" else cls.FEMALE_NAMES)
            last_name = random.choice(cls.LAST_NAMES)
            name = f"{first_name} {last_name}"
        
        if not age:
            age = random.randint(25, 45)
        
        if not city:
            city = cls._generate_city(country)
        
        # Timezone y language
        timezone = random.choice(cls.TIMEZONES.get(country, ["America/New_York"]))
        language = cls.LANGUAGES.get(country, "en-US")
        
        # Device fingerprint
        device_info = cls._generate_device_info(device_type)
        
        # Intereses y browsing history
        interests = random.sample(cls.INTERESTS, k=random.randint(3, 7))
        browsing_history = cls._generate_browsing_history()
        
        return {
            "name": name,
            "age": age,
            "gender": gender,
            "country": country,
            "city": city,
            "timezone": timezone,
            "language": language,
            "device_type": device_type,
            "device_name": device_info["name"],
            "user_agent": device_info["user_agent"],
            "screen_resolution": device_info["resolution"],
            "viewport": device_info["viewport"],
            "pixel_ratio": device_info["pixel_ratio"],
            "platform": device_info["platform"],
            "hardware_concurrency": device_info.get("hardware_concurrency", 4),
            "device_memory": device_info.get("device_memory", 4),
            "interests": interests,
            "browsing_history": browsing_history
        }
    
    @classmethod
    def _generate_device_info(cls, device_type: str) -> Dict:
        """Genera información de dispositivo según tipo"""
        if device_type == "mobile":
            device = random.choice(cls.MOBILE_DEVICES)
            return {
                **device,
                "hardware_concurrency": random.choice([4, 6, 8]),
                "device_memory": random.choice([4, 6, 8])
            }
        else:  # desktop
            return random.choice(cls.DESKTOP_CONFIGS)
    
    @classmethod
    def _generate_city(cls, country: str) -> str:
        """Genera ciudad según país"""
        cities = {
            "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
            "GB": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow"],
            "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa"],
            "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"],
            "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
            "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice"],
            "ES": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao"],
            "BR": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"],
            "MX": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Cancún"],
        }
        return random.choice(cities.get(country, ["City"]))
    
    @classmethod
    def _generate_browsing_history(cls) -> List[str]:
        """Genera historial de navegación realista"""
        history_size = random.randint(5, 15)
        return random.sample(cls.POPULAR_SITES, k=min(history_size, len(cls.POPULAR_SITES)))
    
    @classmethod
    def generate_fingerprint_config(cls, device_type: str = "mobile") -> Dict:
        """
        Genera configuración avanzada de fingerprint para AdsPower
        
        Args:
            device_type: mobile o desktop
            
        Returns:
            Dict con configuración de fingerprint
        """
        device_info = cls._generate_device_info(device_type)
        
        config = {
            # Screen
            "screen_resolution": device_info["resolution"],
            "viewport": device_info["viewport"],
            "pixel_ratio": device_info["pixel_ratio"],
            
            # Hardware
            "hardware_concurrency": device_info.get("hardware_concurrency", 4),
            "device_memory": device_info.get("device_memory", 4),
            "platform": device_info["platform"],
            
            # Canvas
            "canvas": {
                "mode": "noise",  # off, noise, block
                "noise": random.randint(1, 10)
            },
            
            # WebGL
            "webgl": {
                "mode": "noise",
                "vendor": "Google Inc. (Intel)" if device_type == "desktop" else "Google Inc. (ARM)",
                "renderer": cls._get_webgl_renderer(device_type)
            },
            
            # Audio
            "audio": {
                "mode": "noise",
                "noise": random.randint(1, 10)
            },
            
            # Fonts
            "fonts": {
                "mode": "custom",  # default, custom
                "families": cls._get_font_families(device_type)
            },
            
            # WebRTC
            "webrtc": {
                "mode": "proxy",  # real, fake, proxy, off
                "fill_local_ip": True
            },
            
            # Geolocation
            "geolocation": {
                "mode": "prompt",  # prompt, allow, block
                "latitude": round(random.uniform(-90, 90), 6),
                "longitude": round(random.uniform(-180, 180), 6),
                "accuracy": random.randint(10, 100)
            },
            
            # Timezone
            "timezone": {
                "fill_timezone": True
            },
            
            # Language
            "language": {
                "mode": "custom"
            },
            
            # Do Not Track
            "do_not_track": random.choice([True, False]),
            
            # Media Devices
            "media_devices": {
                "enable_audio_input": True,
                "enable_audio_output": True,
                "enable_video_input": device_type == "desktop"
            }
        }
        
        return config
    
    @classmethod
    def _get_webgl_renderer(cls, device_type: str) -> str:
        """Genera renderer WebGL realista"""
        if device_type == "mobile":
            renderers = [
                "Apple GPU",
                "Mali-G78",
                "Adreno (TM) 650",
                "PowerVR Rogue GE8320"
            ]
        else:
            renderers = [
                "ANGLE (Intel, Intel(R) Iris(TM) Plus Graphics 655 Direct3D11 vs_5_0 ps_5_0)",
                "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
                "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
                "Intel Iris OpenGL Engine"
            ]
        return random.choice(renderers)
    
    @classmethod
    def _get_font_families(cls, device_type: str) -> List[str]:
        """Genera lista de fuentes según tipo de dispositivo"""
        common_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana",
            "Georgia", "Palatino", "Garamond", "Bookman", "Comic Sans MS",
            "Trebuchet MS", "Impact"
        ]
        
        if device_type == "desktop":
            desktop_fonts = [
                "Calibri", "Cambria", "Consolas", "Lucida Console",
                "Tahoma", "MS Sans Serif", "Century Gothic"
            ]
            return common_fonts + desktop_fonts
        else:
            mobile_fonts = [
                "San Francisco", "Roboto", "Noto Sans", "Droid Sans"
            ]
            return common_fonts + mobile_fonts