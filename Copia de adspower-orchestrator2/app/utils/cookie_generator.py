# app/utils/cookie_generator.py
"""
Generador de cookies ultra-realistas para fingerprinting avanzado
Pre-carga navegadores con historial de sesiones reales
"""
import random
import string
import time
from typing import List, Dict
from datetime import datetime, timedelta


class CookieGenerator:
    """Genera cookies realistas que simulan sesiones previas"""
    
    # Sitios populares con sus cookies típicas
    POPULAR_SITES = {
        "google": {
            "domain": ".google.com",
            "cookies": [
                {"name": "NID", "value_gen": lambda: generate_hex(32), "httpOnly": True},
                {"name": "1P_JAR", "value_gen": lambda: datetime.utcnow().strftime("%Y-%m-%d-%H"), "httpOnly": False},
                {"name": "CONSENT", "value_gen": lambda: f"YES+srp.gws-{datetime.utcnow().strftime('%Y%m%d')}-0-RC2.en+FX+{random.randint(100,999)}", "httpOnly": False},
                {"name": "SOCS", "value_gen": lambda: f"CAISHAgBEhJnd3NfMjAyMzEyMDUtMF9SQzIaAmVuIAEaBgiA{generate_base64(10)}", "httpOnly": False},
            ]
        },
        "youtube": {
            "domain": ".youtube.com",
            "cookies": [
                {"name": "VISITOR_INFO1_LIVE", "value_gen": lambda: generate_alphanum(22), "httpOnly": True},
                {"name": "YSC", "value_gen": lambda: generate_alphanum(16), "httpOnly": True},
                {"name": "PREF", "value_gen": lambda: f"f4={random.randint(10000000,99999999)}&tz=America.New_York", "httpOnly": False},
            ]
        },
        "facebook": {
            "domain": ".facebook.com",
            "cookies": [
                {"name": "c_user", "value_gen": lambda: str(random.randint(100000000000, 999999999999)), "httpOnly": False},
                {"name": "xs", "value_gen": lambda: f"{generate_alphanum(8)}%3A{generate_alphanum(8)}%3A{int(time.time())}", "httpOnly": True},
                {"name": "datr", "value_gen": lambda: generate_alphanum(24), "httpOnly": True},
                {"name": "sb", "value_gen": lambda: generate_alphanum(24), "httpOnly": True},
                {"name": "fr", "value_gen": lambda: f"{generate_alphanum(10)}.{generate_alphanum(20)}.{generate_alphanum(10)}", "httpOnly": True},
            ]
        },
        "instagram": {
            "domain": ".instagram.com",
            "cookies": [
                {"name": "sessionid", "value_gen": lambda: generate_alphanum(32), "httpOnly": True},
                {"name": "csrftoken", "value_gen": lambda: generate_alphanum(32), "httpOnly": False},
                {"name": "mid", "value_gen": lambda: generate_alphanum(28), "httpOnly": False},
                {"name": "ig_did", "value_gen": lambda: generate_hex(36), "httpOnly": True},
                {"name": "rur", "value_gen": lambda: f"NAO,{random.randint(100000000, 999999999)},{int(time.time()) + 1800}", "httpOnly": True},
            ]
        },
        "twitter": {
            "domain": ".twitter.com",
            "cookies": [
                {"name": "auth_token", "value_gen": lambda: generate_hex(40), "httpOnly": True},
                {"name": "ct0", "value_gen": lambda: generate_hex(32), "httpOnly": False},
                {"name": "guest_id", "value_gen": lambda: f"v1%3A{int(time.time() * 1000)}{random.randint(100000, 999999)}", "httpOnly": False},
                {"name": "personalization_id", "value_gen": lambda: f'"{generate_hex(16)}"', "httpOnly": False},
            ]
        },
        "amazon": {
            "domain": ".amazon.com",
            "cookies": [
                {"name": "session-id", "value_gen": lambda: f"{random.randint(100,999)}-{generate_alphanum(7)}-{generate_alphanum(7)}", "httpOnly": True},
                {"name": "session-id-time", "value_gen": lambda: str(int(time.time()) * 1000), "httpOnly": False},
                {"name": "ubid-main", "value_gen": lambda: f"{random.randint(100,999)}-{generate_alphanum(7)}-{generate_alphanum(7)}", "httpOnly": False},
                {"name": "at-main", "value_gen": lambda: generate_base64(44), "httpOnly": True},
            ]
        },
        "linkedin": {
            "domain": ".linkedin.com",
            "cookies": [
                {"name": "li_at", "value_gen": lambda: generate_base64(60), "httpOnly": True},
                {"name": "JSESSIONID", "value_gen": lambda: f'"ajax:{generate_alphanum(22)}"', "httpOnly": False},
                {"name": "liap", "value_gen": lambda: "true", "httpOnly": False},
                {"name": "li_gc", "value_gen": lambda: generate_base64(24), "httpOnly": False},
            ]
        },
        "reddit": {
            "domain": ".reddit.com",
            "cookies": [
                {"name": "token_v2", "value_gen": lambda: generate_base64(48), "httpOnly": True},
                {"name": "csv", "value_gen": lambda: str(random.randint(1, 2)), "httpOnly": False},
                {"name": "edgebucket", "value_gen": lambda: generate_alphanum(16), "httpOnly": False},
                {"name": "loid", "value_gen": lambda: f"0000000000{generate_hex(10)}.{random.randint(1700000000, 1800000000)}.{random.randint(0, 100)}.0.0.0.0", "httpOnly": False},
            ]
        },
        "netflix": {
            "domain": ".netflix.com",
            "cookies": [
                {"name": "NetflixId", "value_gen": lambda: f"v={random.randint(2, 3)}&ct={generate_base64(100)}", "httpOnly": True},
                {"name": "SecureNetflixId", "value_gen": lambda: f"v={random.randint(2, 3)}&mac={generate_hex(40)}&dt={int(time.time())}", "httpOnly": True},
                {"name": "nfvdid", "value_gen": lambda: generate_base64(30), "httpOnly": False},
            ]
        },
        "github": {
            "domain": ".github.com",
            "cookies": [
                {"name": "user_session", "value_gen": lambda: generate_alphanum(40), "httpOnly": True},
                {"name": "_gh_sess", "value_gen": lambda: generate_base64(100), "httpOnly": True},
                {"name": "logged_in", "value_gen": lambda: "yes", "httpOnly": False},
                {"name": "dotcom_user", "value_gen": lambda: generate_alphanum(20), "httpOnly": False},
            ]
        }
    }
    
    # Cookies de tracking/analytics comunes
    TRACKING_COOKIES = [
        {
            "domain": ".google-analytics.com",
            "name": "_ga",
            "value_gen": lambda: f"GA1.2.{random.randint(100000000, 999999999)}.{int(time.time())}",
            "httpOnly": False
        },
        {
            "domain": ".google-analytics.com",
            "name": "_gid",
            "value_gen": lambda: f"GA1.2.{random.randint(100000000, 999999999)}.{int(time.time())}",
            "httpOnly": False
        },
        {
            "domain": ".doubleclick.net",
            "name": "IDE",
            "value_gen": lambda: generate_base64(24),
            "httpOnly": True
        },
    ]
    
    @classmethod
    def generate_realistic_cookies(
        cls,
        profile_interests: List[str] = None,
        browsing_history: List[str] = None,
        min_cookies: int = 15,
        max_cookies: int = 40
    ) -> List[Dict]:
        """
        Genera set realista de cookies basado en intereses
        
        Returns:
            Lista de cookies en formato AdsPower:
            [
                {
                    "domain": ".google.com",
                    "name": "NID",
                    "value": "abc123...",
                    "path": "/",
                    "expirationDate": 1735689600,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                }
            ]
        """
        cookies = []
        
        # 1. Cookies de sitios populares (basado en intereses)
        sites_to_use = cls._select_sites_from_interests(profile_interests, browsing_history)
        
        for site_key in sites_to_use:
            if site_key in cls.POPULAR_SITES:
                site_cookies = cls._generate_site_cookies(site_key)
                cookies.extend(site_cookies)
        
        # 2. Cookies de tracking (siempre presentes)
        for tracking_cookie in cls.TRACKING_COOKIES:
            cookies.append({
                "domain": tracking_cookie["domain"],
                "name": tracking_cookie["name"],
                "value": tracking_cookie["value_gen"](),
                "path": "/",
                "expirationDate": int(time.time()) + random.randint(7776000, 31536000),  # 3-12 meses
                "httpOnly": tracking_cookie["httpOnly"],
                "secure": True,
                "sameSite": "None"
            })
        
        # 3. Cookies genéricas de preferencias
        generic_cookies = cls._generate_generic_cookies()
        cookies.extend(generic_cookies)
        
        # 4. Ajustar al rango deseado
        if len(cookies) < min_cookies:
            # Agregar más cookies aleatorias
            while len(cookies) < min_cookies:
                site = random.choice(list(cls.POPULAR_SITES.keys()))
                additional = cls._generate_site_cookies(site)
                cookies.extend(additional)
        
        if len(cookies) > max_cookies:
            cookies = random.sample(cookies, max_cookies)
        
        return cookies
    
    @classmethod
    def _select_sites_from_interests(
        cls,
        interests: List[str] = None,
        browsing_history: List[str] = None
    ) -> List[str]:
        """Selecciona sitios según intereses del perfil"""
        sites = []
        
        # Mapeo de intereses a sitios
        interest_mapping = {
            "technology": ["github", "reddit", "twitter"],
            "gaming": ["reddit", "youtube", "twitter"],
            "social": ["facebook", "instagram", "twitter"],
            "shopping": ["amazon"],
            "professional": ["linkedin", "github"],
            "entertainment": ["youtube", "netflix", "reddit"],
            "news": ["twitter", "reddit"],
        }
        
        # Agregar sitios según intereses
        if interests:
            for interest in interests:
                if interest in interest_mapping:
                    sites.extend(interest_mapping[interest])
        
        # Agregar sitios desde browsing history
        if browsing_history:
            for url in browsing_history:
                for site_key in cls.POPULAR_SITES.keys():
                    if site_key in url:
                        sites.append(site_key)
        
        # Google y YouTube siempre presentes (universales)
        sites.extend(["google", "youtube"])
        
        # Remover duplicados y shuffle
        sites = list(set(sites))
        random.shuffle(sites)
        
        # Limitar a 6-10 sitios
        return sites[:random.randint(6, 10)]
    
    @classmethod
    def _generate_site_cookies(cls, site_key: str) -> List[Dict]:
        """Genera cookies para un sitio específico"""
        site_data = cls.POPULAR_SITES[site_key]
        cookies = []
        
        for cookie_template in site_data["cookies"]:
            # Decidir si incluir esta cookie (90% probabilidad)
            if random.random() > 0.9:
                continue
            
            cookie = {
                "domain": site_data["domain"],
                "name": cookie_template["name"],
                "value": cookie_template["value_gen"](),
                "path": "/",
                "expirationDate": int(time.time()) + random.randint(2592000, 31536000),  # 1-12 meses
                "httpOnly": cookie_template["httpOnly"],
                "secure": True,
                "sameSite": "None" if cookie_template["httpOnly"] else "Lax"
            }
            
            cookies.append(cookie)
        
        return cookies
    
    @classmethod
    def _generate_generic_cookies(cls) -> List[Dict]:
        """Genera cookies genéricas (preferencias, timezone, etc)"""
        cookies = []
        
        # Cookie de timezone
        cookies.append({
            "domain": ".example.com",
            "name": "timezone_offset",
            "value": str(random.choice([-480, -420, -360, -300, -240, -180, 0, 60, 120])),
            "path": "/",
            "expirationDate": int(time.time()) + 31536000,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax"
        })
        
        # Cookie de preferencias de idioma
        cookies.append({
            "domain": ".example.com",
            "name": "lang_pref",
            "value": random.choice(["en", "en-US", "es", "es-MX"]),
            "path": "/",
            "expirationDate": int(time.time()) + 31536000,
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax"
        })
        
        return cookies


# ========================================
# HELPER FUNCTIONS
# ========================================

def generate_hex(length: int) -> str:
    """Genera string hexadecimal aleatorio"""
    return ''.join(random.choices('0123456789abcdef', k=length))


def generate_alphanum(length: int) -> str:
    """Genera string alfanumérico aleatorio"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_base64(length: int) -> str:
    """Genera string base64-like aleatorio"""
    chars = string.ascii_letters + string.digits + '+/'
    return ''.join(random.choices(chars, k=length))


# ========================================
# LocalStorage Generator
# ========================================

class LocalStorageGenerator:
    """Genera datos realistas para LocalStorage"""
    
    @classmethod
    def generate_localstorage_data(
        cls,
        profile_interests: List[str] = None,
        browsing_history: List[str] = None
    ) -> Dict[str, str]:
        """
        Genera datos de LocalStorage realistas
        
        Returns:
            Dict con key-value pairs para LocalStorage
        """
        storage_data = {}
        
        # 1. Preferencias de usuario
        storage_data["theme"] = random.choice(["light", "dark", "auto"])
        storage_data["fontSize"] = random.choice(["small", "medium", "large"])
        storage_data["notifications_enabled"] = random.choice(["true", "false"])
        
        # 2. Datos de sesión simulada
        storage_data["last_visit"] = (datetime.utcnow() - timedelta(hours=random.randint(1, 72))).isoformat()
        storage_data["visit_count"] = str(random.randint(5, 150))
        
        # 3. Analytics/tracking IDs
        storage_data["ga_client_id"] = f"{random.randint(100000000, 999999999)}.{int(time.time())}"
        storage_data["amplitude_device_id"] = generate_hex(32)
        
        # 4. Preferencias de sitios específicos (según intereses)
        if profile_interests:
            if "technology" in profile_interests or "gaming" in profile_interests:
                storage_data["reddit_theme"] = random.choice(["dark", "light"])
                storage_data["reddit_feed_pref"] = random.choice(["card", "classic"])
            
            if "shopping" in profile_interests:
                storage_data["amazon_recent_searches"] = ",".join(random.sample([
                    "laptop", "headphones", "keyboard", "mouse", "monitor", "webcam"
                ], k=3))
        
        # 5. Viewport/screen data
        storage_data["viewport_width"] = str(random.choice([360, 390, 393, 414, 428]))
        storage_data["viewport_height"] = str(random.choice([640, 844, 852, 896, 926]))
        
        return storage_data
    
    @classmethod
    def generate_sessionstorage_data(cls) -> Dict[str, str]:
        """Genera datos de SessionStorage realistas"""
        storage_data = {}
        
        # Datos de sesión actual
        storage_data["session_start"] = datetime.utcnow().isoformat()
        storage_data["pages_viewed"] = str(random.randint(1, 8))
        storage_data["scroll_depth"] = str(random.randint(20, 90))
        
        return storage_data