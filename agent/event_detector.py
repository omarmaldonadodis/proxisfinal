# agent/event_detector.py
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from loguru import logger
import uuid
from datetime import datetime

from event_types import EventType, EventSeverity
from event_model import ExecutionEvent


class UniversalEventDetector:
    """Detector universal de eventos críticos"""
    
    # Patrones de detección
    RECAPTCHA_SELECTORS = [
        "iframe[src*='recaptcha']",
        "iframe[src*='hcaptcha']",
        ".g-recaptcha",
        "#g-recaptcha"
    ]
    
    IP_BLOCKED_PATTERNS = [
        "access denied",
        "blocked",
        "banned",
        "ip address",
        "too many requests",
        "rate limit exceeded",
        "forbidden",
        "not authorized"
    ]
    
    LOGIN_FAILED_PATTERNS = [
        "wrong password",
        "incorrect password",
        "invalid credentials",
        "contraseña incorrecta",
        "credenciales inválidas",
        "usuario o contraseña incorrectos",
        "authentication failed"
    ]
    
    ALREADY_LOGGED_IN_PATTERNS = [
        "already logged in",
        "sesión activa",
        "ya has iniciado sesión",
        "logout",
        "cerrar sesión",
        "mi cuenta",
        "my account"
    ]
    
    ACCOUNT_SUSPENDED_PATTERNS = [
        "account suspended",
        "account locked",
        "cuenta bloqueada",
        "cuenta suspendida",
        "cuenta desactivada"
    ]
    
    def __init__(self, computer_id: int = None):  # ✅ Hacer opcional
        self.computer_id = computer_id
    
    async def detect_all_events(
        self,
        driver: webdriver.Chrome,
        execution_id: int,
        profile_id: int,
        computer_id: Optional[int] = None,  # ✅ NUEVO parámetro
        action_index: Optional[int] = None,
        action_type: Optional[str] = None
    ) -> List[ExecutionEvent]:
        """
        Detecta TODOS los eventos posibles en el estado actual
        """
        
        events = []
        
        if not driver:
            return events
        
        # ✅ Usar computer_id del parámetro si se proporciona
        effective_computer_id = computer_id if computer_id is not None else self.computer_id
        
        if effective_computer_id is None:
            logger.error("❌ computer_id is None - cannot create events")
            return events
        
        try:
            # Obtener contexto actual
            current_url = driver.current_url
            page_title = driver.title
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            # 1. 🔴 RECAPTCHA (CRÍTICO)
            if self._detect_recaptcha(driver):
                events.append(self._create_event(
                    event_type=EventType.RECAPTCHA_DETECTED,
                    severity=EventSeverity.CRITICAL,
                    execution_id=execution_id,
                    computer_id=effective_computer_id,  # ✅ Usar valor efectivo
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="reCAPTCHA detected - Manual intervention required",
                    details={
                        "detection_method": "iframe_visible",
                        "current_url": current_url
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=True,
                    can_retry=False,
                    screenshot_name="recaptcha_detected"
                ))
            
            # 2. 🔴 IP BLOQUEADA (CRÍTICO)
            if self._detect_ip_blocked(page_text):
                events.append(self._create_event(
                    event_type=EventType.IP_BLOCKED,
                    severity=EventSeverity.CRITICAL,
                    execution_id=execution_id,
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="IP blocked or access denied",
                    details={
                        "detection_method": "text_pattern",
                        "page_excerpt": page_text[:200]
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=True,
                    can_retry=True,  # Puede reintentar con otro proxy
                    suggested_action="Change proxy and retry",
                    screenshot_name="ip_blocked"
                ))
            
            # 3. 🟡 LOGIN FALLIDO (WARNING)
            if self._detect_login_failed(page_text):
                events.append(self._create_event(
                    event_type=EventType.LOGIN_FAILED_CREDENTIALS,
                    severity=EventSeverity.WARNING,
                    execution_id=execution_id,
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="Login failed - Invalid credentials",
                    details={
                        "detection_method": "error_message",
                        "possible_reasons": [
                            "Wrong username/password",
                            "Account locked",
                            "Credentials expired"
                        ]
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=True,
                    can_retry=False,
                    suggested_action="Verify credentials in database",
                    screenshot_name="login_failed"
                ))
            
            # 4. 🟢 YA LOGUEADO (INFO)
            if self._detect_already_logged_in(page_text, current_url):
                events.append(self._create_event(
                    event_type=EventType.ALREADY_LOGGED_IN,
                    severity=EventSeverity.INFO,
                    execution_id=execution_id,
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="User already logged in",
                    details={
                        "detection_method": "session_active",
                        "current_url": current_url
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=False,
                    can_retry=False,
                    suggested_action="Skip login, continue with warming",
                    screenshot_name="already_logged_in"
                ))
            
            # 5. 🔴 CUENTA SUSPENDIDA (CRÍTICO)
            if self._detect_account_suspended(page_text):
                events.append(self._create_event(
                    event_type=EventType.ACCOUNT_SUSPENDED,
                    severity=EventSeverity.CRITICAL,
                    execution_id=execution_id,
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="Account suspended or locked",
                    details={
                        "detection_method": "suspension_message",
                        "page_excerpt": page_text[:200]
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=True,
                    can_retry=False,
                    suggested_action="Review account status, contact support",
                    screenshot_name="account_suspended"
                ))
            
            # 6. 🟡 PÁGINA NO CARGA (WARNING)
            if self._detect_page_load_issue(driver, current_url):
                events.append(self._create_event(
                    event_type=EventType.PAGE_NOT_LOADING,
                    severity=EventSeverity.WARNING,
                    execution_id=execution_id,
                    profile_id=profile_id,
                    action_index=action_index,
                    action_type=action_type,
                    message="Page failed to load properly",
                    details={
                        "current_url": current_url,
                        "issue": "about:blank or error page"
                    },
                    current_url=current_url,
                    page_title=page_title,
                    requires_manual=False,
                    can_retry=True,
                    suggested_action="Retry navigation",
                    screenshot_name="page_load_failed"
                ))
            
            # 7. 🔴 BROWSER CRASH (CRÍTICO)
            # Este se detecta en warming_executor cuando el driver falla
            
        except Exception as e:
            logger.error(f"Error detecting events: {e}")
        
        return events
    
    def _detect_recaptcha(self, driver: webdriver.Chrome) -> bool:
        """Detecta reCAPTCHA visible"""
        try:
            for selector in self.RECAPTCHA_SELECTORS:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.size['width'] > 0:
                        return True
            return False
        except:
            return False
    
    def _detect_ip_blocked(self, page_text: str) -> bool:
        """Detecta IP bloqueada"""
        return any(pattern in page_text for pattern in self.IP_BLOCKED_PATTERNS)
    
    def _detect_login_failed(self, page_text: str) -> bool:
        """Detecta login fallido"""
        return any(pattern in page_text for pattern in self.LOGIN_FAILED_PATTERNS)
    
    def _detect_already_logged_in(self, page_text: str, url: str) -> bool:
        """Detecta si ya está logueado"""
        return any(pattern in page_text for pattern in self.ALREADY_LOGGED_IN_PATTERNS)
    
    def _detect_account_suspended(self, page_text: str) -> bool:
        """Detecta cuenta suspendida"""
        return any(pattern in page_text for pattern in self.ACCOUNT_SUSPENDED_PATTERNS)
    
    def _detect_page_load_issue(self, driver: webdriver.Chrome, url: str) -> bool:
        """Detecta problemas de carga"""
        return url in ["about:blank", ""] or "err_" in url.lower()
    
    def _create_event(
        self,
        event_type: EventType,
        severity: EventSeverity,
        execution_id: int,
        profile_id: int,
        message: str,
        details: Dict,
        current_url: str,
        page_title: str,
        requires_manual: bool,
        can_retry: bool,
        action_index: Optional[int] = None,
        action_type: Optional[str] = None,
        suggested_action: Optional[str] = None,
        screenshot_name: Optional[str] = None
    ) -> ExecutionEvent:
        """Crea evento estructurado"""
        
        # Tomar screenshot si es necesario
        screenshot_path = None
        if screenshot_name:
            # El screenshot se toma en action_executor
            screenshot_path = f"screenshots/{screenshot_name}_{int(datetime.utcnow().timestamp())}.png"
        
        return ExecutionEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            execution_id=execution_id,
            computer_id=effective_computer_id,
            profile_id=profile_id,
            action_index=action_index,
            action_type=action_type,
            message=message,
            details=details,
            current_url=current_url,
            page_title=page_title,
            screenshot_path=screenshot_path,
            timestamp=datetime.utcnow(),
            requires_manual_intervention=requires_manual,
            can_retry=can_retry,
            suggested_action=suggested_action
        )