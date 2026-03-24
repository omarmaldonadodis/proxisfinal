# agent/profile_creator.py
import httpx
from loguru import logger
from typing import Optional


class ProfileCreator:

    def __init__(self, adspower_url: str, api_key: str = ""):
        self.adspower_url = adspower_url.rstrip("/")
        self.api_key = api_key

    async def create_profile(self, payload: dict) -> Optional[str]:
        """
        Usa el fingerprint_config y user_proxy_config generados por el servidor.
        No reconstruye nada — el servidor es la fuente de verdad.
        """
        name               = payload.get("name", "Profile")
        fingerprint_config = payload.get("fingerprint_config", {})
        user_proxy_config  = payload.get("user_proxy_config", {})
        cookies            = payload.get("cookies", [])
        remark             = payload.get("remark", "")


        logger.info(f"[CREATE] fingerprint_config enviado: {fingerprint_config}")  # ← AGREGAR


        adspower_data = {
            "name":               name,
            "group_id":           "8987213",
            "remark":             remark,
            "fingerprint_config": fingerprint_config,
            "user_proxy_config":  user_proxy_config,
        }

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Crear perfil
                response = await client.post(
                    f"{self.adspower_url}/api/v1/user/create",
                    json=adspower_data,
                    headers=headers
                )
                data = response.json()

                if data.get("code") != 0:
                    logger.error(f"❌ AdsPower error: {data.get('msg')}")
                    return None

                adspower_id = data["data"]["id"]
                logger.info(f"✅ Perfil creado en AdsPower: {adspower_id}")

                # Subir cookies si hay
                if cookies:
                    await self._upload_cookies(client, headers, adspower_id, cookies)

                return adspower_id

        except Exception as e:
            logger.error(f"❌ Error creando perfil en AdsPower: {e}")
            return None

    async def _upload_cookies(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        adspower_id: str,
        cookies: list
    ):
        """Sube cookies al perfil recién creado"""
        try:
            formatted = []
            for c in cookies:
                fc = {
                    "name":     str(c["name"]),
                    "value":    str(c["value"]),
                    "domain":   str(c["domain"]),
                    "path":     str(c.get("path", "/")),
                    "httpOnly": bool(c.get("httpOnly", False)),
                    "secure":   bool(c.get("secure", True)),
                }
                if c.get("expirationDate"):
                    try:
                        fc["expirationDate"] = int(c["expirationDate"])
                    except (ValueError, TypeError):
                        pass
                formatted.append(fc)

            response = await client.post(
                f"{self.adspower_url}/api/v1/user/update",
                json={"user_id": adspower_id, "cookie": formatted},
                headers=headers
            )
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"✅ {len(formatted)} cookies subidas al perfil {adspower_id}")
            else:
                logger.warning(f"⚠️ Error subiendo cookies: {result.get('msg')}")

        except Exception as e:
            logger.warning(f"⚠️ Error en _upload_cookies: {e}")