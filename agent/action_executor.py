# agent/action_executor.py
from typing import Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from loguru import logger
import asyncio
import random
import time

class HumanBehavior:
    """Comportamiento humano para acciones"""
    
    @staticmethod
    def random_delay(min_ms: int = 100, max_ms: int = 300):
        """Delay aleatorio en milisegundos"""
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
    
    @staticmethod
    def typing_speed() -> float:
        """Velocidad de tipeo aleatoria"""
        return random.uniform(0.05, 0.15)
    
    @staticmethod
    def mouse_movement_speed() -> float:
        """Velocidad de movimiento de mouse"""
        return random.uniform(0.5, 1.5)
    
    @staticmethod
    def scroll_amount() -> int:
        """Cantidad de scroll aleatorio"""
        return random.randint(100, 400)

class ActionExecutor:
    """Ejecutor de acciones en navegadores"""
    
    def __init__(self, config):
        self.config = config
        self.behavior = HumanBehavior()
    
    async def execute_action(
        self,
        driver: webdriver.Chrome,
        action: Dict[str, Any]
    ) -> bool:
        """Ejecuta una acción en el navegador"""
        
        action_type = action.get("type")
        params = action.get("params", {})
        
        logger.debug(f"Executing action: {action_type}")
        
        try:
            # Ejecutar según tipo
            if action_type == "navigate":
                return await self._navigate(driver, params)
            
            elif action_type == "click":
                return await self._click(driver, params)
            
            elif action_type == "type":
                return await self._type(driver, params)
            
            elif action_type == "scroll":
                return await self._scroll(driver, params)
            
            elif action_type == "wait":
                return await self._wait(driver, params)
            
            elif action_type == "wait_element":
                return await self._wait_element(driver, params)
            
            elif action_type == "hover":
                return await self._hover(driver, params)
            
            elif action_type == "select":
                return await self._select(driver, params)
            
            elif action_type == "press_key":
                return await self._press_key(driver, params)
            
            elif action_type == "screenshot":
                return await self._screenshot(driver, params)
            
            elif action_type == "switch_tab":
                return await self._switch_tab(driver, params)
            
            elif action_type == "close_tab":
                return await self._close_tab(driver, params)
            
            elif action_type == "execute_script":
                return await self._execute_script(driver, params)
            
            elif action_type == "random_mouse":
                return await self._random_mouse_movement(driver, params)
            
            elif action_type == "human_typing":
                return await self._human_typing(driver, params)
            
            elif action_type == "search_google":
                return await self._search_google(driver, params)
            
            elif action_type == "login":
                return await self._login(driver, params)
            
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False
        
        except Exception as e:
            logger.error(f"Action failed ({action_type}): {e}")
            return False
    
    async def _navigate(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Navega a una URL"""
        url = params.get("url")
        if not url:
            return False
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        driver.get(url)
        await asyncio.sleep(random.uniform(2, 4))
        return True
    
    async def _click(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Hace click en un elemento"""
        selector = params.get("selector")
        by_type = params.get("by", "css")
        human = params.get("human", True)
        
        if not selector:
            return False
        
        # Obtener tipo de selector
        by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
        
        # Encontrar elemento
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((by, selector))
        )
        
        if human:
            # Scroll al elemento
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Mover mouse al elemento
            actions = ActionChains(driver)
            actions.move_to_element(element)
            actions.pause(random.uniform(0.2, 0.5))
            actions.click()
            actions.perform()
        else:
            element.click()
        
        await asyncio.sleep(random.uniform(0.5, 1.5))
        return True
    
    async def _type(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Escribe texto en un elemento"""
        selector = params.get("selector")
        text = params.get("text", "")
        by_type = params.get("by", "css")
        human = params.get("human", True)
        clear_first = params.get("clear", True)
        
        if not selector:
            return False
        
        by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
        
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        
        # Limpiar campo si es necesario
        if clear_first:
            element.clear()
            await asyncio.sleep(0.3)
        
        # Click en el elemento
        element.click()
        await asyncio.sleep(0.3)
        
        if human:
            # Tipeo humanizado
            for char in text:
                element.send_keys(char)
                await asyncio.sleep(self.behavior.typing_speed())
        else:
            element.send_keys(text)
        
        await asyncio.sleep(random.uniform(0.3, 0.7))
        return True
    
    async def _scroll(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Hace scroll"""
        direction = params.get("direction", "down")  # down, up
        amount = params.get("amount", self.behavior.scroll_amount())
        smooth = params.get("smooth", True)
        
        if smooth:
            # Scroll suave
            if direction == "down":
                driver.execute_script(f"window.scrollBy({{top: {amount}, behavior: 'smooth'}});")
            else:
                driver.execute_script(f"window.scrollBy({{top: -{amount}, behavior: 'smooth'}});")
        else:
            if direction == "down":
                driver.execute_script(f"window.scrollBy(0, {amount});")
            else:
                driver.execute_script(f"window.scrollBy(0, -{amount});")
        
        await asyncio.sleep(random.uniform(1, 2))
        return True
    
    async def _wait(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Espera un tiempo"""
        duration = params.get("duration", 1)  # segundos
        await asyncio.sleep(duration)
        return True
    
    async def _wait_element(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Espera a que aparezca un elemento"""
        selector = params.get("selector")
        by_type = params.get("by", "css")
        timeout = params.get("timeout", 10)
        
        if not selector:
            return False
        
        by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
        
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return True
    
    async def _hover(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Pasa el mouse sobre un elemento"""
        selector = params.get("selector")
        by_type = params.get("by", "css")
        duration = params.get("duration", 1)
        
        if not selector:
            return False
        
        by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
        
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        
        actions = ActionChains(driver)
        actions.move_to_element(element)
        actions.pause(duration)
        actions.perform()
        
        return True
    
    async def _select(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Selecciona opción en dropdown"""
        selector = params.get("selector")
        value = params.get("value")
        by_type = params.get("by", "css")
        
        if not selector or not value:
            return False
        
        by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
        
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        
        select = Select(element)
        
        # Intentar seleccionar por valor, texto o índice
        try:
            select.select_by_value(value)
        except:
            try:
                select.select_by_visible_text(value)
            except:
                select.select_by_index(int(value))
        
        await asyncio.sleep(0.5)
        return True
    
    async def _press_key(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Presiona una tecla"""
        key = params.get("key", "ENTER")
        selector = params.get("selector")
        
        key_mapping = {
            "ENTER": Keys.ENTER,
            "TAB": Keys.TAB,
            "ESCAPE": Keys.ESCAPE,
            "SPACE": Keys.SPACE,
            "ARROW_UP": Keys.ARROW_UP,
            "ARROW_DOWN": Keys.ARROW_DOWN,
            "ARROW_LEFT": Keys.ARROW_LEFT,
            "ARROW_RIGHT": Keys.ARROW_RIGHT,
        }
        
        key_obj = key_mapping.get(key.upper(), Keys.ENTER)
        
        if selector:
            by_type = params.get("by", "css")
            by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
            element = driver.find_element(by, selector)
            element.send_keys(key_obj)
        else:
            actions = ActionChains(driver)
            actions.send_keys(key_obj)
            actions.perform()
        
        await asyncio.sleep(0.5)
        return True
    
    async def _screenshot(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Toma screenshot"""
        filename = params.get("filename", f"screenshot_{int(time.time())}.png")
        driver.save_screenshot(filename)
        return True
    
    async def _switch_tab(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Cambia de pestaña"""
        index = params.get("index", 0)
        handles = driver.window_handles
        
        if index < len(handles):
            driver.switch_to.window(handles[index])
            await asyncio.sleep(0.5)
            return True
        return False
    
    async def _close_tab(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Cierra pestaña actual"""
        driver.close()
        
        # Cambiar a primera pestaña disponible
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[0])
        
        await asyncio.sleep(0.5)
        return True
    
    async def _execute_script(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Ejecuta JavaScript"""
        script = params.get("script")
        if not script:
            return False
        
        driver.execute_script(script)
        await asyncio.sleep(0.5)
        return True
    
    async def _random_mouse_movement(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Movimiento aleatorio de mouse"""
        movements = params.get("movements", 3)
        
        actions = ActionChains(driver)
        
        for _ in range(movements):
            x_offset = random.randint(-200, 200)
            y_offset = random.randint(-200, 200)
            
            actions.move_by_offset(x_offset, y_offset)
            actions.pause(random.uniform(0.5, 1.5))
        
        actions.perform()
        return True
    
    async def _human_typing(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Tipeo ultra humanizado con errores y correcciones"""
        selector = params.get("selector")
        text = params.get("text", "")
        error_rate = params.get("error_rate", 0.05)  # 5% de error
        
        if not selector:
            return False
        
        by = By.CSS_SELECTOR
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((by, selector))
        )
        
        element.click()
        await asyncio.sleep(0.3)
        
        for i, char in enumerate(text):
            # Posibilidad de error
            if random.random() < error_rate:
                # Escribir tecla incorrecta
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                element.send_keys(wrong_char)
                await asyncio.sleep(self.behavior.typing_speed())
                
                # Borrar
                element.send_keys(Keys.BACKSPACE)
                await asyncio.sleep(self.behavior.typing_speed())
            
            # Escribir caracter correcto
            element.send_keys(char)
            
            # Variación en velocidad
            if char == " ":
                await asyncio.sleep(random.uniform(0.15, 0.3))
            elif char in ",.;:":
                await asyncio.sleep(random.uniform(0.2, 0.4))
            else:
                await asyncio.sleep(self.behavior.typing_speed())
        
        return True
    
    async def _search_google(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Búsqueda completa en Google"""
        query = params.get("query", "")
        
        if not query:
            return False
        
        # Navegar a Google
        driver.get("https://www.google.com")
        await asyncio.sleep(random.uniform(2, 3))
        
        # Buscar campo de búsqueda
        search_selectors = [
            "textarea[name='q']",
            "input[name='q']",
            "textarea[title='Search']"
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue
        
        if not search_box:
            return False
        
        # Click y escribir
        search_box.click()
        await asyncio.sleep(0.5)
        
        # Tipeo humanizado
        for char in query:
            search_box.send_keys(char)
            await asyncio.sleep(self.behavior.typing_speed())
        
        # Enter
        search_box.send_keys(Keys.ENTER)
        await asyncio.sleep(random.uniform(3, 5))
        
        return True
    
    async def _login(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Login genérico en servicios"""
        service = params.get("service", "generic")
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return False
        
        # Implementar según servicio
        if service == "facebook":
            return await self._login_facebook(driver, username, password)
        elif service == "twitter":
            return await self._login_twitter(driver, username, password)
        elif service == "instagram":
            return await self._login_instagram(driver, username, password)
        else:
            # Login genérico
            return await self._login_generic(driver, username, password, params)
    
    async def _login_generic(
        self,
        driver: webdriver.Chrome,
        username: str,
        password: str,
        params: Dict
    ) -> bool:
        """Login genérico"""
        
        username_selector = params.get("username_selector", "input[type='email']")
        password_selector = params.get("password_selector", "input[type='password']")
        submit_selector = params.get("submit_selector", "button[type='submit']")
        
        try:
            # Username
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, username_selector))
            )
            username_field.click()
            await asyncio.sleep(0.5)
            
            for char in username:
                username_field.send_keys(char)
                await asyncio.sleep(self.behavior.typing_speed())
            
            await asyncio.sleep(1)
            
            # Password
            password_field = driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.click()
            await asyncio.sleep(0.5)
            
            for char in password:
                password_field.send_keys(char)
                await asyncio.sleep(self.behavior.typing_speed())
            
            await asyncio.sleep(1)
            
            # Submit
            submit_button = driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_button.click()
            
            await asyncio.sleep(random.uniform(3, 5))
            return True
        
        except Exception as e:
            logger.error(f"Generic login failed: {e}")
            return False
    
    async def _login_facebook(self, driver: webdriver.Chrome, email: str, password: str) -> bool:
        """Login específico de Facebook"""
        # Implementación específica para Facebook
        pass
    
    async def _login_twitter(self, driver: webdriver.Chrome, username: str, password: str) -> bool:
        """Login específico de Twitter/X"""
        # Implementación específica para Twitter
        pass
    
    async def _login_instagram(self, driver: webdriver.Chrome, username: str, password: str) -> bool:
        """Login específico de Instagram"""
        # Implementación específica para Instagram
        pass