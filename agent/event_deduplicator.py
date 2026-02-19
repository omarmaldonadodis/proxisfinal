# agent/event_deduplicator.py
"""
Sistema de deduplicación de eventos para evitar reportar el mismo error múltiples veces
"""
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from loguru import logger
from event_types import EventType, EventSeverity


class EventDeduplicator:
    """
    Deduplica eventos basándose en:
    - execution_id
    - event_type
    - página actual (URL)
    - tiempo (ventana de deduplicación)
    """
    
    def __init__(self, dedup_window_seconds: int = 30):
        """
        Args:
            dedup_window_seconds: Ventana de tiempo para considerar eventos duplicados
        """
        self.dedup_window = timedelta(seconds=dedup_window_seconds)
        
        # Almacena eventos recientes: key -> timestamp
        # Key format: "execution_id:event_type:url_hash"
        self._recent_events: Dict[str, datetime] = {}
        
        # Eventos que SIEMPRE deben reportarse (aunque sean duplicados)
        self.always_report = {
            EventType.EXECUTION_STARTED,
            EventType.EXECUTION_COMPLETED,
            EventType.EXECUTION_FAILED,
            EventType.EXECUTION_PROGRESS,
        }
        
        # Límite de almacenamiento (auto-limpieza)
        self.max_stored_events = 1000
    
    def should_report(
        self,
        execution_id: int,
        event_type: EventType,
        current_url: Optional[str] = None,
        severity: Optional[EventSeverity] = None
    ) -> bool:
        """
        Determina si un evento debe reportarse o es duplicado
        """
        
        # 1. SIEMPRE reportar eventos de ciclo de vida
        if event_type in self.always_report:
            return True
        
        # 2. SIEMPRE reportar eventos CRÍTICOS
        if severity == EventSeverity.CRITICAL:
            return self._should_report_critical(execution_id, event_type)
        
        # ✅ 3. SIEMPRE reportar errores de login (SIN deduplicación)
        if event_type == EventType.LOGIN_FAILED_CREDENTIALS:
            logger.debug(f"LOGIN ERROR - reporting without deduplication")
            return True
        
        # 4. Construir clave de deduplicación
        event_key = self._build_key(execution_id, event_type, current_url)
        
        # 5. Verificar cache
        if event_key in self._recent_events:
            last_reported = self._recent_events[event_key]
            time_since_last = datetime.utcnow() - last_reported
            
            if time_since_last < self.dedup_window:
                logger.debug(
                    f"Event deduplicated: {event_type} "
                    f"(last reported {time_since_last.seconds}s ago)"
                )
                return False
        
        # 6. Registrar y permitir
        self._recent_events[event_key] = datetime.utcnow()
        
        # 7. Auto-limpieza
        if len(self._recent_events) > self.max_stored_events:
            self._cleanup_old_events()
        
        return True
    
    def _should_report_critical(
        self,
        execution_id: int,
        event_type: EventType
    ) -> bool:
        """
        Para eventos CRÍTICOS: máximo 1 por minuto
        """
        event_key = f"{execution_id}:CRITICAL:{event_type}"
        
        if event_key in self._recent_events:
            last_reported = self._recent_events[event_key]
            time_since_last = datetime.utcnow() - last_reported
            
            # Ventana de 60 segundos para CRÍTICOS
            if time_since_last < timedelta(seconds=60):
                return False
        
        self._recent_events[event_key] = datetime.utcnow()
        return True
    
    def _build_key(
        self,
        execution_id: int,
        event_type: EventType,
        url: Optional[str]
    ) -> str:
        """
        Construye clave única para deduplicación
        
        Incluye URL para detectar si el mismo error ocurre en páginas diferentes
        """
        # Hash simple de URL (primeros 50 chars)
        url_hash = ""
        if url:
            # Normalizar URL (remover query params y fragments)
            base_url = url.split('?')[0].split('#')[0]
            url_hash = base_url[-50:]  # Últimos 50 chars
        
        return f"{execution_id}:{event_type}:{url_hash}"
    
    def _cleanup_old_events(self):
        """
        Limpia eventos antiguos (fuera de ventana de deduplicación)
        """
        now = datetime.utcnow()
        cutoff = now - (self.dedup_window * 2)  # Doble de la ventana
        
        # Filtrar eventos recientes
        self._recent_events = {
            key: timestamp
            for key, timestamp in self._recent_events.items()
            if timestamp > cutoff
        }
        
        logger.debug(f"Cleaned old events, kept {len(self._recent_events)}")
    
    def mark_execution_completed(self, execution_id: int):
        """
        Marca una ejecución como completada y limpia sus eventos
        
        Llamar cuando una ejecución termine para liberar memoria
        """
        keys_to_remove = [
            key for key in self._recent_events.keys()
            if key.startswith(f"{execution_id}:")
        ]
        
        for key in keys_to_remove:
            del self._recent_events[key]
        
        logger.debug(f"Cleared {len(keys_to_remove)} events for execution {execution_id}")
    
    def reset(self):
        """Resetea completamente el deduplicador"""
        self._recent_events.clear()
        logger.info("Event deduplicator reset")
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del deduplicador"""
        return {
            "stored_events": len(self._recent_events),
            "max_capacity": self.max_stored_events,
            "dedup_window_seconds": self.dedup_window.total_seconds()
        }


class ExecutionEventCache:
    """
    Cache específico por ejecución para rastrear qué eventos ya ocurrieron
    Útil para eventos que solo deben reportarse UNA VEZ por ejecución
    """
    
    def __init__(self):
        # execution_id -> Set[EventType]
        self._execution_events: Dict[int, Set[EventType]] = {}
        
        # Eventos que solo deben ocurrir UNA VEZ por ejecución
        self.once_per_execution = {
            EventType.RECAPTCHA_DETECTED,
            EventType.IP_BLOCKED,
            EventType.ACCOUNT_SUSPENDED,
            EventType.ALREADY_LOGGED_IN,
        }
    
    def should_report_once(
        self,
        execution_id: int,
        event_type: EventType
    ) -> bool:
        """
        Verifica si un evento "once-per-execution" debe reportarse
        """
        if event_type not in self.once_per_execution:
            return True  # No aplica restricción
        
        # Verificar si ya ocurrió en esta ejecución
        if execution_id not in self._execution_events:
            self._execution_events[execution_id] = set()
        
        if event_type in self._execution_events[execution_id]:
            logger.debug(f"Event {event_type} already reported for execution {execution_id}")
            return False
        
        # Marcar como reportado
        self._execution_events[execution_id].add(event_type)
        return True
    
    def clear_execution(self, execution_id: int):
        """Limpia eventos de una ejecución completada"""
        if execution_id in self._execution_events:
            del self._execution_events[execution_id]
    
    def reset(self):
        """Resetea todo el cache"""
        self._execution_events.clear()


# ============================================
# EJEMPLO DE USO
# ============================================

if __name__ == "__main__":
    from event_types import EventType, EventSeverity
    import time
    
    # Crear deduplicador
    dedup = EventDeduplicator(dedup_window_seconds=30)
    exec_cache = ExecutionEventCache()
    
    execution_id = 123
    url = "https://example.com/login"
    
    print("=== Test 1: Mismo evento repetido ===")
    for i in range(5):
        should_report = dedup.should_report(
            execution_id,
            EventType.LOGIN_FAILED_CREDENTIALS,
            url,
            EventSeverity.WARNING
        )
        print(f"Attempt {i+1}: {'REPORT' if should_report else 'SKIP (duplicate)'}")
        time.sleep(0.5)
    
    print("\n=== Test 2: Evento crítico repetido ===")
    for i in range(3):
        should_report = dedup.should_report(
            execution_id,
            EventType.RECAPTCHA_DETECTED,
            url,
            EventSeverity.CRITICAL
        )
        print(f"Attempt {i+1}: {'REPORT' if should_report else 'SKIP (duplicate)'}")
        time.sleep(1)
    
    print("\n=== Test 3: Once-per-execution ===")
    for i in range(3):
        should_report = exec_cache.should_report_once(
            execution_id,
            EventType.ALREADY_LOGGED_IN
        )
        print(f"Attempt {i+1}: {'REPORT' if should_report else 'SKIP (already reported)'}")
    
    print("\n=== Stats ===")
    print(dedup.get_stats())