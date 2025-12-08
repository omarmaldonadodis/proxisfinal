# agent/action_executor_login.py
"""
Enhanced Login Action Executor with:
- Human-like behavior
- reCAPTCHA detection
- Authentication error detection
- Multiple retry strategies
"""
from typing import Dict, Optional, Any, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger
import asyncio
import random
import time


class LoginResult:
    """Resultado de intento de login"""
    
    def __init__(
        self,
        success: bool,
        message: str,
        error_type: Optional[str] = None,
        needs_captcha: bool = False,
        needs_2fa: bool = False,
        blocked: bool = False
    ):
        self.success = success
        self.message = message
        self.error_type = error_type
        self.needs_captcha = needs_captcha
        self.needs_2fa = needs_2fa
        self.blocked = blocked
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "message": self.message,
            "error_type": self.error_type,
            "needs_captcha": self.needs_captcha,
            "needs_2fa": self.needs_2fa,
            "blocked": self.blocked
        }


class HumanizedLoginExecutor:
    """Ejecutor de login humanizado con detección de problemas"""
    
    # Detectores de reCAPTCHA
    RECAPTCHA_INDICATORS = [
        "recaptcha",
        "g-recaptcha",
        "captcha",
        "robot",
        "verify you're human",
        "i'm not a robot",
        "verificación",
        "demostrar que no eres un robot"
    ]
    
    # Detectores de errores de autenticación
    AUTH_ERROR_INDICATORS = [
        "wrong password",
        "incorrect password",
        "invalid credentials",
        "contraseña incorrecta",
        "credenciales inválidas",
        "usuario o contraseña incorrectos",
        "wrong username",
        "user not found",
        "usuario no encontrado"
    ]
    
    # Detectores de bloqueo
    BLOCKED_INDICATORS = [
        "account locked",
        "account suspended",
        "too many attempts",
        "temporarily blocked",
        "cuenta bloqueada",
        "cuenta suspendida",
        "demasiados intentos",
        "bloqueado temporalmente"
    ]
    
    # Detectores de 2FA
    TWO_FA_INDICATORS = [
        "verification code",
        "two-factor",
        "2fa",
        "código de verificación",
        "autenticación de dos factores",
        "enter code",
        "6-digit code"
    ]
    
    def __init__(self, config):
        self.config = config
    
    async def execute_login(
        self,
        driver: webdriver.Chrome,
        params: Dict[str, Any]
    ) -> LoginResult:
        """
        Ejecuta login humanizado con detección completa
        
        Params esperados:
        {
            "service": "ecuabet" | "betcris" | "generic",
            "username": "user@email.com",
            "password": "password123",
            "username_selector": "input[name='username']",
            "password_selector": "input[name='password']",
            "submit_selector": "button[type='submit']",
            "wait_after_submit": 5,
            "success_url_contains": "dashboard",
            "success_element": ".user-menu"
        }
        """
        
        service = params.get("service", "generic")
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return LoginResult(
                success=False,
                message="Username or password not provided",
                error_type="missing_credentials"
            )
        
        logger.info(f"🔐 Starting login for service: {service}")
        
        try:
            # 1. Detectar reCAPTCHA antes de empezar
            if self._detect_recaptcha(driver):
                logger.warning("⚠️ reCAPTCHA detected before login")
                return LoginResult(
                    success=False,
                    message="reCAPTCHA detected on page",
                    error_type="recaptcha",
                    needs_captcha=True
                )
            
            # 2. Esperar estabilidad de la página
            await self._wait_for_page_stability(driver)
            
            # 3. Buscar y llenar campo de usuario
            username_filled = await self._fill_username(
                driver,
                username,
                params.get("username_selector", "input[type='email'], input[name='username'], input[name='email']")
            )
            
            if not username_filled:
                return LoginResult(
                    success=False,
                    message="Could not find username field",
                    error_type="username_field_not_found"
                )
            
            # 4. Pausa humanizada
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # 5. Buscar y llenar campo de contraseña
            password_filled = await self._fill_password(
                driver,
                password,
                params.get("password_selector", "input[type='password'], input[name='password']")
            )
            
            if not password_filled:
                return LoginResult(
                    success=False,
                    message="Could not find password field",
                    error_type="password_field_not_found"
                )
            
            # 6. Pausa antes de submit
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 7. Detectar reCAPTCHA después de llenar campos
            if self._detect_recaptcha(driver):
                logger.warning("⚠