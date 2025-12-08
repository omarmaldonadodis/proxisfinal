# agent/login_detector.py
"""
Detector inteligente de problemas en procesos de login
Identifica: reCAPTCHA, errores de credenciales, bloqueos, etc.
"""
from typing import Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
import asyncio
import time


class LoginIssue:
    """Tipos de problemas de login"""
    RECAPTCHA = "recaptcha"
    WRONG_CREDENTIALS = "wrong_credentials"
    ACCOUNT_BLOCKED = "account_blocked"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"
    SUCCESS = "success"


class LoginDetector:
    """Detector de problemas en login"""
    
    # Patrones comunes de elementos de reCAPTCHA
    RECAPTCHA_PATTERNS = [
        "iframe[src*='recaptcha']",
        "iframe[title*='recaptcha']",
        ".g-recaptcha",
        "#g-recaptcha",
        "div[class*='recaptcha']",
        "[data-sitekey]",
        "iframe[src*='hcaptcha']",
        ".h-captcha",
        "#h-captcha"
    ]
    
    # Patrones de errores de credenciales (español)
    CREDENTIAL_ERROR_TEXTS = [
        "contraseña incorrecta",
        "usuario incorrecto",
        "credenciales inválidas",
        "credenciales incorrectas",
        "usuario o contraseña incorrectos",
        "email o contraseña incorrectos",
        "datos incorrectos",
        "acceso denegado",
        "usuario no encontrado",
        "correo no registrado",
        "wrong password",
        "invalid credentials",
        "incorrect username",
        "login failed",
        "authentication failed"
    ]
    
    # Patrones de cuenta bloqueada
    ACCOUNT_BLOCKED_TEXTS = [
        "cuenta bloqueada",
        "cuenta suspendida",
        "cuenta desactivada",
        "acceso restringido",
        "usuario bloqueado",
        "demasiados intentos",
        "intenta más tarde",
        "account blocked",
        "account suspended",
        "too many attempts",
        "temporarily blocked"
    ]
    
    # Patrones de éxito en login
    SUCCESS_PATTERNS = [
        "bienvenido",
        "welcome",
        "mi cuenta",
        "perfil",
        "saldo",
        "balance",
        "logout",
        "cerrar sesión",
        "dashboard",
        "mis apuestas",
        "my bets"
    ]
    
    def __init__(self):
        self.detection_timeout = 10  # segundos
    
    async def detect_login_issues(
        self,
        driver: webdriver.Chrome,
        expected_success_url: Optional[str] = None
    ) -> Dict:
        """
        Detecta problemas después de un intento de login
        
        Returns:
            {
                "issue_type": "success" | "recaptcha" | "wrong_credentials" | etc,
                "detected": True/False,
                "details": {...},
                "screenshot": "path/to/screenshot.png"
            }
        """
        
        logger.info("🔍 Detecting login issues...")
        
        # Esperar un momento para que la página responda
        await asyncio.sleep(3)
        
        result = {
            "issue_type": LoginIssue.UNKNOWN_ERROR,
            "detected": False,
            "details": {},
            "screenshot": None
        }
        
        try:
            # 1. Verificar reCAPTCHA (PRIORIDAD ALTA)
            recaptcha_detected = await self._detect_recaptcha(driver)
            if recaptcha_detected:
                result["issue_type"] = LoginIssue.RECAPTCHA
                result["detected"] = True
                result["details"] = recaptcha_detected
                result["screenshot"] = self._take_screenshot(driver, "recaptcha_detected")
                logger.warning("❌ reCAPTCHA detected!")
                return result
            
            # 2. Verificar errores de credenciales
            credential_error = await self._detect_credential_error(driver)
            if credential_error:
                result["issue_type"] = LoginIssue.WRONG_CREDENTIALS
                result["detected"] = True
                result["details"] = credential_error
                result["screenshot"] = self._take_screenshot(driver, "wrong_credentials")
                logger.warning("❌ Wrong credentials detected!")
                return result
            
            # 3. Verificar cuenta bloqueada
            blocked = await self._detect_account_blocked(driver)
            if blocked:
                result["issue_type"] = LoginIssue.ACCOUNT_BLOCKED
                result["detected"] = True
                result["details"] = blocked
                result["screenshot"] = self._take_screenshot(driver, "account_blocked")
                logger.warning("❌ Account blocked detected!")
                return result
            
            # 4. Verificar éxito (cambio de URL o elementos de sesión)
            success = await self._detect_success(driver, expected_success_url)
            if success:
                result["issue_type"] = LoginIssue.SUCCESS
                result["detected"] = True
                result["details"] = success
                result["screenshot"] = self._take_screenshot(driver, "login_success")
                logger.info("✅ Login successful!")
                return result
            
            # 5. Si no detectamos nada específico después de esperar
            await asyncio.sleep(2)
            
            # Último intento de detección de éxito
            late_success = await self._detect_success(driver, expected_success_url)
            if late_success:
                result["issue_type"] = LoginIssue.SUCCESS
                result["detected"] = True
                result["details"] = late_success
                logger.info("✅ Login successful (delayed detection)")
                return result
            
            # 6. Error desconocido
            result["issue_type"] = LoginIssue.UNKNOWN_ERROR
            result["detected"] = False
            result["details"] = {
                "current_url": driver.current_url,
                "page_title": driver.title
            }
            result["screenshot"] = self._take_screenshot(driver, "unknown_state")
            logger.warning("⚠️ Unknown login state")
            
        except Exception as e:
            logger.error(f"Error during detection: {e}")
            result["details"]["error"] = str(e)
        
        return result
    
    async def _detect_recaptcha(self, driver: webdriver.Chrome) -> Optional[Dict]:
        """Detecta presencia de reCAPTCHA"""
        
        try:
            for selector in self.RECAPTCHA_PATTERNS:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Verificar que sea visible
                        for elem in elements:
                            if elem.is_displayed():
                                return {
                                    "captcha_type": "recaptcha" if "recaptcha" in selector else "hcaptcha",
                                    "selector": selector,
                                    "visible": True
                                }
                except:
                    continue
            
            # Buscar también por contenido de iframe
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    src = iframe.get_attribute("src") or ""
                    if "recaptcha" in src.lower() or "hcaptcha" in src.lower():
                        return {
                            "captcha_type": "recaptcha" if "recaptcha" in src else "hcaptcha",
                            "iframe_src": src,
                            "visible": iframe.is_displayed()
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"reCAPTCHA detection error: {e}")
            return None
    
    async def _detect_credential_error(self, driver: webdriver.Chrome) -> Optional[Dict]:
        """Detecta mensajes de error de credenciales"""
        
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            for error_text in self.CREDENTIAL_ERROR_TEXTS:
                if error_text in page_text:
                    return {
                        "error_pattern": error_text,
                        "detected_in": "page_text"
                    }
            
            # Buscar elementos de error comunes
            error_selectors = [
                ".error",
                ".alert-danger",
                ".error-message",
                "[class*='error']",
                "[class*='invalid']",
                "[role='alert']"
            ]
            
            for selector in error_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            elem_text = elem.text.lower()
                            for error_pattern in self.CREDENTIAL_ERROR_TEXTS:
                                if error_pattern in elem_text:
                                    return {
                                        "error_pattern": error_pattern,
                                        "detected_in": "error_element",
                                        "element_text": elem.text
                                    }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Credential error detection error: {e}")
            return None
    
    async def _detect_account_blocked(self, driver: webdriver.Chrome) -> Optional[Dict]:
        """Detecta mensajes de cuenta bloqueada"""
        
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            for blocked_text in self.ACCOUNT_BLOCKED_TEXTS:
                if blocked_text in page_text:
                    return {
                        "block_pattern": blocked_text,
                        "detected_in": "page_text"
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Account blocked detection error: {e}")
            return None
    
    async def _detect_success(
        self,
        driver: webdriver.Chrome,
        expected_url: Optional[str] = None
    ) -> Optional[Dict]:
        """Detecta login exitoso"""
        
        try:
            current_url = driver.current_url.lower()
            
            # 1. Verificar cambio de URL
            if expected_url:
                if expected_url.lower() in current_url:
                    return {
                        "method": "url_change",
                        "expected_url": expected_url,
                        "current_url": driver.current_url
                    }
            
            # 2. Verificar patrones de URL de éxito
            success_url_patterns = [
                "dashboard",
                "cuenta",
                "perfil",
                "home",
                "lobby",
                "sports",
                "deportes"
            ]
            
            for pattern in success_url_patterns:
                if pattern in current_url:
                    return {
                        "method": "url_pattern",
                        "pattern": pattern,
                        "current_url": driver.current_url
                    }
            
            # 3. Verificar elementos de sesión activa
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            for success_text in self.SUCCESS_PATTERNS:
                if success_text in page_text:
                    return {
                        "method": "success_text",
                        "pattern": success_text
                    }
            
            # 4. Verificar cookies de sesión
            cookies = driver.get_cookies()
            session_cookies = [
                c for c in cookies
                if any(keyword in c["name"].lower() for keyword in ["session", "token", "auth", "user"])
            ]
            
            if session_cookies:
                return {
                    "method": "session_cookies",
                    "cookies_found": len(session_cookies)
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Success detection error: {e}")
            return None
    
    def _take_screenshot(self, driver: webdriver.Chrome, prefix: str) -> str:
        """Toma screenshot para debugging"""
        
        try:
            import os
            os.makedirs("screenshots", exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"screenshots/{prefix}_{timestamp}.png"
            
            driver.save_screenshot(filename)
            logger.debug(f"Screenshot saved: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def should_retry(self, issue_type: str) -> bool:
        """Determina si se debe reintentar el login"""
        
        # NO reintentar en estos casos
        no_retry = [
            LoginIssue.RECAPTCHA,  # Requiere intervención manual
            LoginIssue.ACCOUNT_BLOCKED,  # Cuenta bloqueada
            LoginIssue.SUCCESS  # Ya tuvo éxito
        ]
        
        return issue_type not in no_retry