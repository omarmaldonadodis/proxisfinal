# agent/main.py
import asyncio
import sys
import os
import signal
from loguru import logger
from datetime import datetime

# Importar componentes del agente
from config import AgentConfig
from websocket_client import WebSocketClient
from browser_controller import BrowserController
from warming_executor import WarmingExecutor
from auto_config import AutoConfig

class AdsPowerAgent:
    """Agente AdsPower para ejecución distribuida"""
    
    def __init__(self):
        # Cargar configuración
        self.config = AgentConfig()

        hw = AutoConfig.get_hardware_info(self.config)
        self.config.ADSPOWER_API_URL = hw["adspower_api_url"]
        
        # Setup logging
        self._setup_logging()
        
        # Inicializar componentes
        self.browser_controller = BrowserController(self.config)
        self.warming_executor = WarmingExecutor(
            self.config,
            self.browser_controller
        )
        self.websocket_client = WebSocketClient(
            self.config,
            self.warming_executor
        )
        
        # Estado
        self.running = False
        self.start_time = None
        
    def _setup_logging(self):
        """Configura logging"""
        # Crear directorio de logs
        os.makedirs(self.config.LOG_PATH, exist_ok=True)
        
        # Remover handlers por defecto
        logger.remove()
        
        # Console handler
        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level=self.config.LOG_LEVEL,
            colorize=True
        )
        
        # File handler
        logger.add(
            os.path.join(self.config.LOG_PATH, "agent_{time:YYYY-MM-DD}.log"),
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Error file handler
        logger.add(
            os.path.join(self.config.LOG_PATH, "agent_errors_{time:YYYY-MM-DD}.log"),
            rotation="1 day",
            retention="90 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )

    async def start(self):
        '''Inicia el agente'''
        self.running = True
        self.start_time = datetime.utcnow()
        
        logger.info("=" * 60)
        logger.info(f"🤖 AdsPower Agent Starting")
        logger.info(f"Computer Name: {self.config.COMPUTER_NAME}")
        logger.info(f"Orchestrator: {self.config.ORCHESTRATOR_URL}")
        logger.info("=" * 60)
        
        try:
            # ✅ 1. REGISTRO AUTOMÁTICO
            from registration_client import RegistrationClient
            
            registration_client = RegistrationClient(
                self.config.ORCHESTRATOR_URL,
                self.config
            )
            
            # Intentar usar token guardado
            saved_token = registration_client.load_token()
            saved_registration = registration_client.load_registration()
            
            if saved_token and saved_registration:
                logger.info("🔑 Found saved token, validating...")
                validation = await registration_client.validate_token(saved_token)
                
                if validation.get("valid"):
                    logger.info("✅ Token valid, using existing registration")
                    self.config.set_computer_id(validation["computer_id"])
                else:
                    logger.warning("❌ Saved token invalid, re-registering...")
                    saved_token = None
            
            if not saved_token:
                logger.info("📝 Registering with orchestrator...")
                result = await registration_client.register()
                self.config.set_computer_id(result["computer_id"])
            
            # ✅ 2. VERIFICAR QUE TENEMOS COMPUTER_ID
            if not self.config.COMPUTER_ID:
                raise Exception("Failed to obtain Computer ID from orchestrator")
            
            logger.info(f"✅ Computer ID: {self.config.COMPUTER_ID}")
            
            # ✅ 3. CONECTAR AL WEBSOCKET
            logger.info("Connecting to orchestrator via WebSocket...")
            await self.websocket_client.connect()
            
            logger.info("✅ Agent started successfully!")
            logger.info("Waiting for commands from orchestrator...")
            
            # Mantener agente corriendo
            while self.running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
            await self.stop()
        
        except Exception as e:
            logger.error(f"Agent error: {e}")
            import traceback
            traceback.print_exc()
            await self.stop() 
    
    async def stop(self):
        """Detiene el agente"""
        if not self.running:
            return
        
        logger.info("Stopping agent...")
        self.running = False
        
        # Cerrar navegadores
        await self.browser_controller.close_all_browsers()
        
        # Desconectar WebSocket
        await self.websocket_client.disconnect()
        
        # Calcular uptime
        if self.start_time:
            uptime = datetime.utcnow() - self.start_time
            logger.info(f"Agent uptime: {uptime}")
        
        logger.info("✅ Agent stopped")
    
    def handle_signal(self, signum, frame):
        """Maneja señales del sistema"""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.stop())


async def main():
    """Función principal"""
    agent = AdsPowerAgent()
    
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, agent.handle_signal)
    signal.signal(signal.SIGTERM, agent.handle_signal)
    
    # Iniciar agente
    await agent.start()


if __name__ == "__main__":
    # Ejecutar agente
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)