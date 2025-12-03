# app/services/automation_service.py
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.profile_repository import ProfileRepository
from app.repositories.computer_repository import ComputerRepository
from app.integrations.adspower_client import AdsPowerClient
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import threading
import asyncio
from loguru import logger

class SyncBarrier:
    """Barrera de sincronización para navegadores paralelos"""
    
    def __init__(self, num_threads: int):
        self.num_threads = num_threads
        self.counter = 0
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.generation = 0
        self.active_threads = num_threads
        self.failed_threads = set()
    
    def mark_failed(self, thread_id):
        with self.lock:
            if thread_id not in self.failed_threads:
                self.failed_threads.add(thread_id)
                self.active_threads -= 1
                if self.counter >= self.active_threads and self.active_threads > 0:
                    self.counter = 0
                    self.generation += 1
                    self.event.set()
    
    def wait(self, timeout: int = 30) -> bool:
        with self.lock:
            if self.active_threads == 0:
                return False
            
            self.counter += 1
            local_gen = self.generation
            
            if self.counter >= self.active_threads:
                self.counter = 0
                self.generation += 1
                self.event.set()
                return True
        
        start_time = time.time()
        while True:
            if self.event.wait(timeout=0.1):
                with self.lock:
                    if local_gen < self.generation:
                        if self.counter == 0:
                            self.event.clear()
                        return True
            
            if time.time() - start_time > timeout:
                with self.lock:
                    self.counter = 0
                    self.generation += 1
                    self.event.set()
                return False

class HumanBehavior:
    """Comportamiento humano para automatización"""
    
    @staticmethod
    def pause_short():
        time.sleep(random.uniform(0.5, 1.5))
    
    @staticmethod
    def pause_medium():
        time.sleep(random.uniform(1.5, 3.0))
    
    @staticmethod
    def pause_long():
        time.sleep(random.uniform(3.0, 5.0))
    
    @staticmethod
    def typing_speed():
        return random.uniform(0.05, 0.15)

class AutomationService:
    """Servicio para automatización de navegadores"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_repo = ProfileRepository(db)
        self.computer_repo = ComputerRepository(db)
    
    async def parallel_search(
        self,
        profile_ids: List[int],
        search_query: str,
        max_parallel: int = 5
    ) -> Dict:
        """Búsqueda paralela sincronizada"""
        
        # Obtener profiles con relaciones
        profiles_data = []
        for profile_id in profile_ids:
            profile = await self.profile_repo.get_with_relations(profile_id)
            if not profile:
                logger.warning(f"Profile {profile_id} not found")
                continue
            profiles_data.append(profile)
        
        if not profiles_data:
            raise ValueError("No valid profiles found")
        
        # Ejecutar en thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._execute_parallel_search,
            profiles_data,
            search_query,
            max_parallel
        )
        
        return result
    
    def _execute_parallel_search(
        self,
        profiles_data: List,
        search_query: str,
        max_parallel: int
    ) -> Dict:
        """Ejecuta búsqueda paralela (sync)"""
        
        results = {
            'total': len(profiles_data),
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        # Agrupar por computer
        profiles_by_computer = {}
        for profile in profiles_data:
            computer_id = profile.computer_id
            if computer_id not in profiles_by_computer:
                profiles_by_computer[computer_id] = []
            profiles_by_computer[computer_id].append(profile)
        
        # Abrir navegadores
        drivers = {}
        for profile in profiles_data:
            try:
                driver = self._open_browser_sync(profile)
                if driver:
                    drivers[profile.id] = {
                        'driver': driver,
                        'profile': profile
                    }
            except Exception as e:
                logger.error(f"Failed to open browser for profile {profile.id}: {e}")
                results['results'].append({
                    'profile_id': profile.id,
                    'profile_name': profile.name,
                    'success': False,
                    'error': str(e)
                })
                results['failed'] += 1
        
        if not drivers:
            return results
        
        # Crear barreras de sincronización
        num_browsers = len(drivers)
        barriers = {
            'locate': SyncBarrier(num_browsers),
            'click': SyncBarrier(num_browsers),
            'type': SyncBarrier(num_browsers),
            'submit': SyncBarrier(num_browsers),
            'verify': SyncBarrier(num_browsers),
        }
        
        # Ejecutar búsqueda paralela con threads
        import concurrent.futures
        
        def search_task(profile_id, driver_data):
            driver = driver_data['driver']
            profile = driver_data['profile']
            
            start_time = time.time()
            success = False
            error = None
            
            try:
                success = self._synchronized_search(
                    driver,
                    profile.id,
                    profile.name,
                    search_query,
                    barriers
                )
            except Exception as e:
                logger.error(f"Search failed for profile {profile.id}: {e}")
                error = str(e)
                for barrier in barriers.values():
                    barrier.mark_failed(profile.id)
            finally:
                try:
                    driver.quit()
                except:
                    pass
            
            duration = time.time() - start_time
            
            return {
                'profile_id': profile.id,
                'profile_name': profile.name,
                'success': success,
                'duration_seconds': round(duration, 2),
                'error': error
            }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_parallel, num_browsers)) as executor:
            futures = {
                executor.submit(search_task, pid, data): pid
                for pid, data in drivers.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results['results'].append(result)
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
        
        return results
    
    def _open_browser_sync(self, profile) -> Optional[webdriver.Chrome]:
        """Abre navegador (sync)"""
        try:
            # Crear cliente AdsPower
            import requests
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {profile.computer.adspower_api_key}'
            }
            
            # Abrir navegador
            response = requests.get(
                f"{profile.computer.adspower_api_url}/api/v1/browser/start",
                params={"user_id": profile.adspower_id},
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to open browser: {response.text}")
            
            result = response.json()
            if result.get('code') != 0:
                raise Exception(f"AdsPower error: {result.get('msg')}")
            
            debug_port = result['data']['debug_port']
            
            # Conectar Selenium
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
            chrome_options.add_argument('--log-level=3')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # Preparar navegador
            if not self._prepare_browser(driver, profile.adspower_id):
                driver.quit()
                return None
            
            return driver
            
        except Exception as e:
            logger.error(f"Error opening browser: {e}")
            return None
    
    def _prepare_browser(self, driver, profile_id: str) -> bool:
        """Prepara navegador (cierra pestañas extra, navega a Google)"""
        try:
            logger.info(f"[{profile_id}] Preparing browser...")
            
            # Obtener handles
            all_handles = driver.window_handles
            
            # Cerrar DevTools
            for handle in list(all_handles):
                try:
                    driver.switch_to.window(handle)
                    time.sleep(0.2)
                    current_url = driver.current_url
                    if "devtools://" in current_url:
                        driver.close()
                        time.sleep(0.3)
                except:
                    pass
            
            # Actualizar handles
            time.sleep(0.5)
            all_handles = driver.window_handles
            
            # Si no hay handles, crear uno
            if not all_handles:
                driver.execute_script("window.open('about:blank');")
                time.sleep(1)
                all_handles = driver.window_handles
            
            # Cerrar pestañas extra
            if len(all_handles) > 1:
                keep_handle = all_handles[0]
                for handle in all_handles[1:]:
                    try:
                        driver.switch_to.window(handle)
                        time.sleep(0.1)
                        driver.close()
                        time.sleep(0.2)
                    except:
                        pass
                
                time.sleep(0.5)
                driver.switch_to.window(keep_handle)
                time.sleep(0.3)
            
            # Navegar a Google
            for attempt in range(3):
                try:
                    driver.get("https://www.google.com")
                    time.sleep(2)
                    
                    current_url = driver.current_url
                    if "google" in current_url.lower():
                        logger.info(f"[{profile_id}] Browser ready")
                        return True
                    
                    if attempt < 2:
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"[{profile_id}] Navigation attempt {attempt+1} failed: {e}")
                    if attempt < 2:
                        time.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"[{profile_id}] Browser preparation failed: {e}")
            return False
    
    def _synchronized_search(
        self,
        driver,
        profile_id: int,
        profile_name: str,
        search_query: str,
        barriers: Dict
    ) -> bool:
        """Ejecuta búsqueda sincronizada"""
        try:
            behavior = HumanBehavior()
            
            # PASO 1: Localizar campo
            if not barriers['locate'].wait(timeout=30):
                logger.warning(f"[{profile_id}] Timeout in locate barrier")
                return False
            
            search_box = None
            selectors = [
                ("name", "q"),
                ("css", "textarea[name='q']"),
                ("css", "input[name='q']"),
            ]
            
            for selector_type, selector_value in selectors:
                try:
                    if selector_type == "name":
                        search_box = driver.find_element(By.NAME, selector_value)
                    else:
                        search_box = driver.find_element(By.CSS_SELECTOR, selector_value)
                    
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                logger.error(f"[{profile_id}] Search box not found")
                return False
            
            # PASO 2: Click
            if not barriers['click'].wait(timeout=30):
                logger.warning(f"[{profile_id}] Timeout in click barrier")
                return False
            
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", search_box)
                time.sleep(0.5)
                driver.execute_script("arguments[0].focus();", search_box)
                driver.execute_script("arguments[0].click();", search_box)
                behavior.pause_short()
            except:
                search_box.click()
                behavior.pause_short()
            
            # PASO 3: Escribir
            if not barriers['type'].wait(timeout=30):
                logger.warning(f"[{profile_id}] Timeout in type barrier")
                return False
            
            try:
                driver.execute_script("arguments[0].value = '';", search_box)
            except:
                pass
            
            for i, char in enumerate(search_query):
                current_text = search_query[:i+1]
                try:
                    driver.execute_script(f"arguments[0].value = '{current_text}';", search_box)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_box)
                except:
                    break
                time.sleep(behavior.typing_speed())
            
            # PASO 4: Submit
            if not barriers['submit'].wait(timeout=30):
                logger.warning(f"[{profile_id}] Timeout in submit barrier")
                return False
            
            behavior.pause_short()
            driver.execute_script("""
                var form = arguments[0].closest('form');
                if (form) { form.submit(); }
            """, search_box)
            behavior.pause_long()
            
            # PASO 5: Verificar
            if not barriers['verify'].wait(timeout=30):
                logger.warning(f"[{profile_id}] Timeout in verify barrier")
                return False
            
            current_url = driver.current_url
            if "search" in current_url or "q=" in current_url:
                logger.info(f"[{profile_id}] Search completed successfully")
                return True
            
            logger.info(f"[{profile_id}] Search completed (URL check inconclusive)")
            return True
            
        except Exception as e:
            logger.error(f"[{profile_id}] Search error: {e}")
            for barrier in barriers.values():
                barrier.mark_failed(profile_id)
            return False
    
    async def parallel_navigation(
        self,
        profile_ids: List[int],
        urls: List[str],
        stay_duration_min: int,
        stay_duration_max: int,
        max_parallel: int = 5,
        randomize_order: bool = True
    ) -> Dict:
        """Navegación paralela a múltiples URLs"""
        
        # Obtener profiles
        profiles_data = []
        for profile_id in profile_ids:
            profile = await self.profile_repo.get_with_relations(profile_id)
            if profile:
                profiles_data.append(profile)
        
        if not profiles_data:
            raise ValueError("No valid profiles found")
        
        # Ejecutar en thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._execute_parallel_navigation,
            profiles_data,
            urls,
            stay_duration_min,
            stay_duration_max,
            max_parallel,
            randomize_order
        )
        
        return result
    
    def _execute_parallel_navigation(
        self,
        profiles_data: List,
        urls: List[str],
        stay_duration_min: int,
        stay_duration_max: int,
        max_parallel: int,
        randomize_order: bool
    ) -> Dict:
        """Ejecuta navegación paralela (sync)"""
        
        results = {
            'total': len(profiles_data),
            'successful': 0,
            'failed': 0,
            'results': []
        }
        
        import concurrent.futures
        
        def navigation_task(profile):
            start_time = time.time()
            success = False
            error = None
            sites_visited = 0
            
            try:
                # Abrir navegador
                driver = self._open_browser_sync(profile)
                if not driver:
                    raise Exception("Failed to open browser")
                
                # Preparar lista de URLs
                urls_to_visit = urls.copy()
                if randomize_order:
                    random.shuffle(urls_to_visit)
                
                # Visitar cada URL
                for url in urls_to_visit:
                    try:
                        if not url.startswith('http'):
                            url = f'https://{url}'
                        
                        driver.get(url)
                        time.sleep(2)
                        
                        # Tiempo de permanencia
                        stay_time = random.uniform(stay_duration_min, stay_duration_max)
                        time.sleep(stay_time)
                        
                        sites_visited += 1
                        
                    except Exception as e:
                        logger.warning(f"[{profile.id}] Failed to visit {url}: {e}")
                        continue
                
                driver.quit()
                success = sites_visited > 0
                
            except Exception as e:
                logger.error(f"Navigation failed for profile {profile.id}: {e}")
                error = str(e)
            
            duration = time.time() - start_time
            
            return {
                'profile_id': profile.id,
                'profile_name': profile.name,
                'success': success,
                'sites_visited': sites_visited,
                'duration_seconds': round(duration, 2),
                'error': error
            }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {executor.submit(navigation_task, profile): profile for profile in profiles_data}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results['results'].append(result)
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
        
        return results