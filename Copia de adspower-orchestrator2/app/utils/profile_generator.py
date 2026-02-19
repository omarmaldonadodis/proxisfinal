# app/utils/profile_generator.py - VERSIÓN ULTRA-REALISTA V2
"""
Profile Generator con Fingerprinting Hiper-Realista
- 50+ dispositivos (mobile, tablet, desktop)
- Cookies pre-cargadas
- LocalStorage/SessionStorage
- Remarks ultra-variados
- Integración completa AdsPower + SOAX
"""
import random
from typing import Dict, List, Optional
from datetime import datetime

from app.utils.mobile_devices import get_random_device, get_device_by_id
from app.utils.cookie_generator import CookieGenerator, LocalStorageGenerator


class ProfileGenerator:
    """Generador de perfiles con fingerprints hiper-realistas"""
    
    # Nombres diversificados (500+ combinaciones)
    MALE_FIRST_NAMES = [
        "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
        "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
        "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
        "George", "Edward", "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan", "Jacob",
        "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
        "Brandon", "Benjamin", "Samuel", "Frank", "Gregory", "Raymond", "Alexander",
        "Patrick", "Jack", "Dennis", "Jerry", "Tyler", "Aaron", "Jose", "Adam",
        "Henry", "Nathan", "Douglas", "Zachary", "Peter", "Kyle", "Walter", "Ethan"
    ]
    
    FEMALE_FIRST_NAMES = [
        "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
        "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
        "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
        "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon",
        "Cynthia", "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela",
        "Emma", "Nicole", "Helen", "Samantha", "Katherine", "Christine", "Debra",
        "Rachel", "Carolyn", "Janet", "Catherine", "Maria", "Heather", "Diane",
        "Ruth", "Julie", "Olivia", "Joyce", "Virginia", "Victoria", "Kelly", "Lauren"
    ]
    
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
        "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy"
    ]
    
    # Intereses ultra-diversificados
    INTERESTS = [
        "technology", "artificial_intelligence", "machine_learning", "software_development",
        "sports", "basketball", "soccer", "football", "baseball", "tennis", "golf",
        "travel", "adventure_travel", "luxury_travel", "backpacking", "cruises",
        "food", "cooking", "baking", "restaurants", "food_blogging", "wine",
        "fashion", "streetwear", "luxury_fashion", "sustainable_fashion",
        "music", "rock", "pop", "hip_hop", "jazz", "classical", "electronic",
        "movies", "cinema", "tv_series", "documentaries", "anime",
        "gaming", "pc_gaming", "console_gaming", "esports", "mobile_gaming",
        "fitness", "gym", "yoga", "running", "cycling", "crossfit", "martial_arts",
        "photography", "landscape_photography", "portrait_photography", "street_photography",
        "art", "painting", "sculpture", "digital_art", "street_art",
        "books", "fiction", "non_fiction", "self_help", "biographies",
        "shopping", "online_shopping", "luxury_goods", "electronics", "fashion_shopping",
        "news", "world_news", "tech_news", "sports_news", "finance_news",
        "business", "entrepreneurship", "startups", "investing", "real_estate",
        "health", "nutrition", "mental_health", "meditation", "wellness",
        "education", "online_learning", "languages", "skills_development",
        "entertainment", "concerts", "theater", "comedy", "festivals",
        "science", "space", "physics", "biology", "chemistry",
        "environment", "sustainability", "climate_change", "conservation",
        "pets", "dogs", "cats", "exotic_pets", "pet_care",
        "home_improvement", "diy", "interior_design", "gardening",
        "automotive", "cars", "motorcycles", "electric_vehicles", "racing"
    ]
    
    # Timezones por país
    TIMEZONES = {
        "US": ["America/New_York", "America/Chicago", "America/Los_Angeles", "America/Denver", "America/Phoenix"],
        "GB": ["Europe/London"],
        "CA": ["America/Toronto", "America/Vancouver", "America/Montreal"],
        "AU": ["Australia/Sydney", "Australia/Melbourne", "Australia/Brisbane"],
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
        "EC": ["America/Guayaquil"],  # ✅ ECUADOR
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
        "EC": "es-EC",  # ✅ ECUADOR
    }
    
    # Ciudades por país
    CITIES = {
        "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"],
        "GB": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Newcastle", "Sheffield"],
        "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton", "Winnipeg"],
        "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast"],
        "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart", "Düsseldorf"],
        "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg"],
        "ES": ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Málaga"],
        "IT": ["Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa", "Bologna"],
        "BR": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza"],
        "MX": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Cancún"],
        "AR": ["Buenos Aires", "Córdoba", "Rosario", "Mendoza", "La Plata"],
        "JP": ["Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Fukuoka"],
        "KR": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon"],
        "IN": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata"],
        "EC": ["Quito", "Guayaquil", "Cuenca", "Santo Domingo", "Machala", "Ambato"],  # ✅ ECUADOR
    }
    
    @classmethod
    def generate_profile(
        cls,
        name: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        country: str = "EC",  # ✅ DEFAULT ECUADOR
        city: Optional[str] = None,
        device_type: str = "mobile",  # mobile, tablet, desktop
        device_id: Optional[str] = None,  # ID específico de dispositivo
        include_cookies: bool = True,
        include_localstorage: bool = True
    ) -> Dict:
        """
        Genera configuración completa de perfil ULTRA-REALISTA
        
        Returns:
            Dict con toda la configuración del perfil
        """
        
        # ========================================
        # 1. DATOS PERSONALES
        # ========================================
        if not gender:
            gender = random.choice(["male", "female"])
        
        if not name:
            first_name = random.choice(cls.MALE_FIRST_NAMES if gender == "male" else cls.FEMALE_FIRST_NAMES)
            last_name = random.choice(cls.LAST_NAMES)
            name = f"{first_name} {last_name}"
        
        if not age:
            age = random.randint(22, 55)
        
        if not city:
            city = random.choice(cls.CITIES.get(country, ["City"]))
        
        # Timezone y language
        timezone = random.choice(cls.TIMEZONES.get(country, ["America/Guayaquil"]))
        language = cls.LANGUAGES.get(country, "es-EC")
        
        # ========================================
        # 2. DEVICE FINGERPRINT
        # ========================================
        if device_id:
            device_info = get_device_by_id(device_id)
            if not device_info:
                device_info = get_random_device(device_type=device_type)
        else:
            device_info = get_random_device(device_type=device_type)
        
        # ========================================
        # 3. INTERESES & BROWSING HISTORY
        # ========================================
        interests = random.sample(cls.INTERESTS, k=random.randint(5, 12))
        browsing_history = cls._generate_browsing_history(interests)
        
        # ========================================
        # 4. COOKIES (ULTRA-REALISTAS)
        # ========================================
        cookies = []
        if include_cookies:
            cookies = CookieGenerator.generate_realistic_cookies(
                profile_interests=interests,
                browsing_history=browsing_history,
                min_cookies=20,
                max_cookies=45
            )
        
        # ========================================
        # 5. LOCALSTORAGE/SESSIONSTORAGE
        # ========================================
        localstorage_data = {}
        sessionstorage_data = {}
        
        if include_localstorage:
            localstorage_data = LocalStorageGenerator.generate_localstorage_data(
                profile_interests=interests,
                browsing_history=browsing_history
            )
            sessionstorage_data = LocalStorageGenerator.generate_sessionstorage_data()
        
        # ========================================
        # 6. REMARK ULTRA-VARIADO
        # ========================================
        remark = cls._generate_ultra_realistic_remark(
            name=name,
            age=age,
            gender=gender,
            country=country,
            city=city,
            interests=interests[:3],  # Top 3 intereses
            device=device_info
        )
        
        # ========================================
        # 7. RETORNAR CONFIGURACIÓN COMPLETA
        # ========================================
        return {
            # Datos básicos
            "name": name,
            "age": age,
            "gender": gender,
            "country": country,
            "city": city,
            "timezone": timezone,
            "language": language,
            
            # Device info
            "device_type": device_info["device_type"],
            "device_name": device_info["name"],
            "device_brand": device_info["brand"],
            "device_model": device_info["model"],
            "os": device_info["os"],
            "os_version": device_info["os_version"],
            "user_agent": device_info["user_agent"],
            "screen_resolution": device_info["screen_resolution"],
            "viewport": device_info["viewport"],
            "pixel_ratio": device_info["pixel_ratio"],
            "platform": device_info["platform"],
            "hardware_concurrency": device_info["hardware_concurrency"],
            "device_memory": device_info["device_memory"],
            
            # Profile data
            "interests": interests,
            "browsing_history": browsing_history,
            
            # Fingerprinting avanzado
            "cookies": cookies,
            "localstorage": localstorage_data,
            "sessionstorage": sessionstorage_data,
            
            # Remark
            "remark": remark,
            
            # Metadata
            "created_at": datetime.utcnow().isoformat()
        }
    
    @classmethod
    def _generate_browsing_history(cls, interests: List[str]) -> List[str]:
        """Genera historial de navegación basado en intereses"""
        
        # Mapeo de intereses a sitios
        interest_to_sites = {
            "technology": ["techcrunch.com", "theverge.com", "arstechnica.com", "wired.com"],
            "artificial_intelligence": ["openai.com", "deepmind.com", "anthropic.com"],
            "sports": ["espn.com", "bleacherreport.com", "sportsillustrated.com"],
            "travel": ["tripadvisor.com", "booking.com", "airbnb.com", "lonelyplanet.com"],
            "food": ["allrecipes.com", "foodnetwork.com", "seriouseats.com"],
            "fashion": ["vogue.com", "gq.com", "fashionnova.com"],
            "music": ["spotify.com", "soundcloud.com", "pitchfork.com"],
            "gaming": ["ign.com", "gamespot.com", "kotaku.com", "twitch.tv"],
            "shopping": ["amazon.com", "ebay.com", "etsy.com"],
            "news": ["cnn.com", "bbc.com", "nytimes.com", "reuters.com"],
        }
        
        sites = ["google.com", "youtube.com"]  # Siempre presentes
        
        for interest in interests:
            if interest in interest_to_sites:
                sites.extend(random.sample(interest_to_sites[interest], k=min(2, len(interest_to_sites[interest]))))
        
        # Agregar sitios genéricos
        generic_sites = ["reddit.com", "twitter.com", "instagram.com", "facebook.com", "linkedin.com"]
        sites.extend(random.sample(generic_sites, k=random.randint(2, 4)))
        
        return list(set(sites))[:random.randint(10, 20)]
    
    @classmethod
    def _generate_ultra_realistic_remark(
        cls,
        name: str,
        age: int,
        gender: str,
        country: str,
        city: str,
        interests: List[str],
        device: Dict
    ) -> str:
        """
        Genera remark ultra-variado y único
        
        Formato: "Nombre | Edad | Ciudad | Top Interés | Device"
        """
        
        # Emoji según género
        gender_emoji = "👨" if gender == "male" else "👩"
        
        # Top interés con emoji
        interest_emojis = {
            "technology": "💻",
            "sports": "⚽",
            "travel": "✈️",
            "food": "🍕",
            "fashion": "👗",
            "music": "🎵",
            "gaming": "🎮",
            "fitness": "💪",
            "photography": "📸",
            "art": "🎨",
        }
        
        top_interest = interests[0] if interests else "general"
        interest_emoji = interest_emojis.get(top_interest, "📱")
        
        # Device emoji
        device_emojis = {
            "mobile": "📱",
            "tablet": "💻",
            "desktop": "🖥️"
        }
        device_emoji = device_emojis.get(device["device_type"], "📱")
        
        # Construir remark ultra-variado
        templates = [
            f"{gender_emoji} {name} | {age}y | {city}, {country} | {interest_emoji} {top_interest.replace('_', ' ').title()} | {device_emoji} {device['brand']} {device['os']}",
            f"{name.split()[0]} from {city} | {age} | {interest_emoji} {top_interest.replace('_', ' ').title()} enthusiast | {device['brand']} user",
            f"{city}, {country} | {name} ({age}) | Interests: {', '.join(i.replace('_', ' ').title() for i in interests[:2])} | {device['name']}",
            f"{gender_emoji} {name} | {city} resident | {age}y | {device['brand']} {device['model']} | {top_interest.replace('_', ' ').title()} lover",
            f"Profile: {name} | Location: {city}, {country} | Age: {age} | Device: {device['name']} | Main interest: {top_interest.replace('_', ' ').title()}",
        ]
        
        return random.choice(templates)