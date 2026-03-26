# agent/profile_verifier.py


import asyncio
import json
import httpx
import websockets
from loguru import logger
from typing import Optional

FINGERPRINT_JS = """
(function() {
    const fp = {};

    // === IDENTIDAD BÁSICA ===
    fp.userAgent            = navigator.userAgent;
    fp.platform             = navigator.platform;
    fp.language             = navigator.language;
    fp.languages            = Array.from(navigator.languages || []);
    fp.hardwareConcurrency  = navigator.hardwareConcurrency;
    fp.deviceMemory         = navigator.deviceMemory || null;
    fp.cookieEnabled        = navigator.cookieEnabled;
    fp.doNotTrack           = navigator.doNotTrack;

    // === PANTALLA ===
    fp.screenWidth   = screen.width;
    fp.screenHeight  = screen.height;
    fp.screenDepth   = screen.colorDepth;
    fp.pixelRatio    = window.devicePixelRatio;
    fp.innerWidth    = window.innerWidth;
    fp.innerHeight   = window.innerHeight;

    // === TIMEZONE ===
    fp.timezone       = Intl.DateTimeFormat().resolvedOptions().timeZone;
    fp.timezoneOffset = new Date().getTimezoneOffset();

    // === WEBRTC LEAK CHECK ===
    fp.webrtcLeak = false;
    fp.webrtcIPs  = [];
    try {
        const pc = new RTCPeerConnection({iceServers: []});
        pc.createDataChannel('');
        pc.createOffer().then(offer => pc.setLocalDescription(offer));
        pc.onicecandidate = (ice) => {
            if (ice && ice.candidate && ice.candidate.candidate) {
                const match = ice.candidate.candidate.match(/(\\d{1,3}\\.){3}\\d{1,3}/);
                if (match && !match[0].startsWith('192.168') && !match[0].startsWith('10.')) {
                    fp.webrtcLeak = true;
                    fp.webrtcIPs.push(match[0]);
                }
            }
        };
        setTimeout(() => { try { pc.close(); } catch(e) {} }, 500);
    } catch(e) { fp.webrtcError = e.message; }

    // === CANVAS ===
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 200; canvas.height = 50;
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillStyle = '#f60';
        ctx.fillRect(125, 1, 62, 20);
        ctx.fillStyle = '#069';
        ctx.fillText('FP Test 2025', 2, 15);
        fp.canvasHash    = canvas.toDataURL().length;
        fp.canvasEnabled = true;
    } catch(e) { fp.canvasEnabled = false; }

    // === WEBGL ===
    try {
        const gl = document.createElement('canvas').getContext('webgl');
        if (gl) {
            fp.webglVendor   = gl.getParameter(gl.VENDOR);
            fp.webglRenderer = gl.getParameter(gl.RENDERER);
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            if (ext) {
                fp.webglUnmaskedVendor   = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                fp.webglUnmaskedRenderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
            }
        }
    } catch(e) { fp.webglError = e.message; }

    // === FUENTES ===
    try {
        const fontTest = ['Arial', 'Times New Roman', 'Courier New', 'Georgia', 'Verdana'];
        fp.fontsDetected = fontTest.filter(font => {
            const s = document.createElement('span');
            s.style.cssText = 'position:absolute;font-family:' + font + ',monospace;';
            s.innerHTML = 'mmmmm';
            document.body.appendChild(s);
            const w = s.offsetWidth;
            document.body.removeChild(s);
            return w !== 0;
        });
    } catch(e) { fp.fontsDetected = []; }

    // === PLUGINS ===
    fp.pluginCount = navigator.plugins ? navigator.plugins.length : 0;
    fp.plugins     = Array.from(navigator.plugins || []).map(p => p.name);

    // === AUTOMATIZACIÓN ===
    fp.webdriver       = !!navigator.webdriver;
    fp.automationProps = [];
    const autoProps = [
        '__webdriver_evaluate', '__selenium_evaluate', '__webdriver_script_fn',
        '__driver_evaluate', '__webdriver_unwrapped',
        '$cdc_asdjflasutopfhvcZLmcfl_', '$chrome_asyncScriptInfo',
        '__$webdriverAsyncExecutor'
    ];
    autoProps.forEach(p => { if (window[p] !== undefined) fp.automationProps.push(p); });
    fp.chromeRuntime = !!(window.chrome && window.chrome.runtime);

    // === COOKIES — con try/catch para evitar SecurityError en páginas restringidas ===
    try {
        fp.cookieCount = document.cookie
            ? document.cookie.split(';').filter(c => c.trim().length > 0).length
            : 0;
        fp.hasCookies = fp.cookieCount > 0;
    } catch(e) {
        fp.cookieCount = navigator.cookieEnabled ? -1 : 0;
        fp.hasCookies  = navigator.cookieEnabled;
        fp.cookieNote  = 'verificado via cookieEnabled';
    }

    return JSON.stringify(fp);
})();
"""


class ProfileVerifier:

    def __init__(self, adspower_url: str, api_key: str = ""):
        self.adspower_url = adspower_url.rstrip("/")
        self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def verify(self, adspower_id: str, db_data: dict) -> dict:
        # Esperar un poco si el perfil fue recientemente actualizado
        # (proxy puede estar en proceso de aplicarse)
        await asyncio.sleep(2)
        
        browser_info = await self._open_browser(adspower_id)
        if not browser_info.get("success"):
            logger.error(
                f"❌ No se pudo abrir browser para {adspower_id}: "
                f"{browser_info.get('error')}"
            )
            return self._error_result(browser_info.get("error"), db_data)

        try:
            fp_data = await self._extract_fingerprint_cdp(
                browser_info["debug_address"]
            )
            if not fp_data:
                return self._error_result(
                    "No se pudo extraer fingerprint via CDP", db_data
                )
            return self._analyze(fp_data, db_data)
        finally:
            await self._close_browser(adspower_id)

    async def _open_browser(self, adspower_id: str, retries: int = 3) -> dict:
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.get(
                        f"{self.adspower_url}/api/v1/browser/start",
                        params={
                            "user_id": adspower_id,
                            "open_urls": "https://www.google.com",
                            "ip_tab": 0,
                            "new_first_tab": 1,
                        },
                        headers=self._headers,
                    )
                    data = r.json()

                    if data.get("code") != 0:
                        error_msg = data.get("msg", "Error AdsPower")
                        logger.warning(
                            f"⚠️ Intento {attempt + 1}/{retries} fallido: {error_msg}"
                        )
                        if attempt < retries - 1:
                            await asyncio.sleep(5)
                        continue

                    bdata = data["data"]
                    selenium_ws = bdata.get("ws", {}).get("selenium", "")
                    debug_address = (
                        selenium_ws.replace("ws://", "").split("/devtools/")[0]
                        if selenium_ws else None
                    )

                    logger.info(f"✅ Browser abierto — debug_address={debug_address}")
                    return {"success": True, "debug_address": debug_address}

            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt + 1}/{retries} excepción: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(5)

        return {"success": False, "error": f"No se pudo abrir el browser tras {retries} intentos"}

    async def _extract_fingerprint_cdp(self, debug_address: str) -> Optional[dict]:
        if not debug_address:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"http://{debug_address}/json")
                targets = r.json()

            page_target = None
            for t in targets:
                if t.get("type") == "page":
                    ws_url = t.get("webSocketDebuggerUrl")
                    if ws_url:
                        page_target = ws_url
                        if "google.com" in t.get("url", ""):
                            break

            if not page_target:
                logger.warning("No se encontró target de página en CDP")
                return None

            logger.info(f"🔌 Conectando CDP a: {page_target}")

            async with websockets.connect(
                page_target,
                ping_interval=None,
                open_timeout=10
            ) as ws:
                # Navegar explícitamente para evitar about:blank
                await ws.send(json.dumps({
                    "id": 0,
                    "method": "Page.navigate",
                    "params": {"url": "https://www.google.com"}
                }))
                await asyncio.sleep(4)

                msg_id = 1
                payload = {
                    "id": msg_id,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": FINGERPRINT_JS,
                        "returnByValue": True,
                        "awaitPromise": False,
                    }
                }
                await ws.send(json.dumps(payload))

                # Reemplazar asyncio.timeout() con wait_for()
                async def _wait_for_result():
                    while True:
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        if msg.get("id") == msg_id:
                            return (
                                msg.get("result", {})
                                .get("result", {})
                                .get("value")
                            )

                result_str = await asyncio.wait_for(_wait_for_result(), timeout=15.0)

            if result_str:
                fp = json.loads(result_str)
                logger.info(
                    f"✅ Fingerprint extraído — "
                    f"webdriver={fp.get('webdriver')} "
                    f"cookies={fp.get('cookieCount')} "
                    f"tz={fp.get('timezone')}"
                )
                return fp

        except asyncio.TimeoutError:
            logger.error("⏱ Timeout extrayendo fingerprint via CDP")
        except Exception as e:
            logger.error(f"Error CDP: {e}")

        return None

    async def _close_browser(self, adspower_id: str):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.get(
                    f"{self.adspower_url}/api/v1/browser/stop",
                    params={"user_id": adspower_id},
                    headers=self._headers,
                )
        except Exception as e:
            logger.warning(f"Error cerrando browser: {e}")

    def _error_result(self, error: str, db_data: dict) -> dict:
        return {
            "error": error,
            "browser_score": 0,
            "fingerprint_score": 0,
            "cookie_status": db_data.get("cookie_status", "MISSING"),
            "has_cookies": False,
            "cookie_count": 0,
            "grade": "DÉBIL",
            "issues": [error or "Error desconocido"],
            "warnings": [],
            "breakdown": {},
            "raw_fingerprint": {},
        }


    def _analyze(self, fp: dict, db: dict) -> dict:
        issues   = []
        warnings = []
        score    = 100

        # ── 1. AUTOMATIZACIÓN (el riesgo mayor) ───────────────────────────────
        if fp.get("webdriver"):
            issues.append("navigator.webdriver = true — detectado como bot automáticamente")
            score -= 40

        if fp.get("automationProps"):
            issues.append(
                f"Propiedades de automatización expuestas: {fp['automationProps']}"
            )
            score -= 30

        # ── 2. WEBRTC LEAK ────────────────────────────────────────────────────
        if fp.get("webrtcLeak"):
            issues.append(
                f"WebRTC leak — IP real expuesta: {fp.get('webrtcIPs', [])}"
            )
            score -= 25
        # (si NO hay leak es correcto, no penalizar)

        # ── 3. TIMEZONE ───────────────────────────────────────────────────────
        expected_tz = db.get("timezone", "")
        actual_tz   = fp.get("timezone", "")
        if expected_tz and actual_tz and expected_tz != actual_tz:
            issues.append(
                f"Timezone inconsistente: perfil='{expected_tz}', browser='{actual_tz}'"
            )
            score -= 15

        # ── 4. HARDWARE CONCURRENCY ───────────────────────────────────────────
        expected_hc = db.get("hardware_concurrency")
        actual_hc   = fp.get("hardwareConcurrency")
        if expected_hc and actual_hc and int(expected_hc) != int(actual_hc):
            warnings.append(
                f"hardware_concurrency inconsistente: BD={expected_hc}, real={actual_hc}"
            )
            score -= 8

        # ── 5. WEBGL RENDERER (VM/software renderer) ──────────────────────────
        renderer = (
            fp.get("webglUnmaskedRenderer") or
            fp.get("webglRenderer") or ""
        )
        virtual_renderers = ["SwiftShader", "llvmpipe", "softpipe", "Mesa"]
        if any(vr in renderer for vr in virtual_renderers):
            issues.append(f"WebGL renderer virtual detectado: '{renderer}'")
            score -= 20

        # ── 6. PLUGINS ────────────────────────────────────────────────────────
        if fp.get("pluginCount", 0) == 0:
            warnings.append(
                "Sin plugins — navegador headless o perfil muy limpio"
            )
            score -= 5

        # ── 7. CANVAS ─────────────────────────────────────────────────────────
        if not fp.get("canvasEnabled"):
            warnings.append("Canvas bloqueado — algunos sitios detectan esto")
            score -= 5

        # ── 8. COOKIES ────────────────────────────────────────────────────────
        cookie_count  = fp.get("cookieCount", 0)
        # cookieCount = -1 significa que se usó cookieEnabled como fallback
        has_cookies   = cookie_count > 0 or (cookie_count == -1 and fp.get("hasCookies"))
        cookie_status = "OK" if has_cookies else db.get("cookie_status", "MISSING")

        if not has_cookies:
            issues.append("Sin cookies en el browser — perfil sin historial")
            score -= 10
        elif cookie_count != -1 and cookie_count < 5:
            warnings.append(
                f"Pocas cookies ({cookie_count}) — perfil con poco historial"
            )
            score -= 3

        score = max(0, score)

        # ── fingerprint_score: solo la parte de huella digital ─────────────
        fp_score = 100
        if fp.get("webdriver"):            fp_score -= 50
        if fp.get("automationProps"):      fp_score -= 30
        if any(vr in renderer for vr in virtual_renderers): fp_score -= 20
        fp_score = max(0, fp_score)

        grade = (
            "EXCELENTE" if score >= 85 else
            "BUENO"     if score >= 65 else
            "REGULAR"   if score >= 45 else
            "DÉBIL"
        )

        return {
            "browser_score":     score,
            "fingerprint_score": fp_score,
            "cookie_status":     cookie_status,
            "has_cookies":       has_cookies,
            "cookie_count":      cookie_count if cookie_count != -1 else 0,
            "grade":             grade,
            "issues":            issues,
            "warnings":          warnings,
            "raw_fingerprint": {
                "userAgent":           fp.get("userAgent"),
                "platform":            fp.get("platform"),
                "timezone":            fp.get("timezone"),
                "hardwareConcurrency": fp.get("hardwareConcurrency"),
                "deviceMemory":        fp.get("deviceMemory"),
                "webdriver":           fp.get("webdriver"),
                "webrtcLeak":          fp.get("webrtcLeak"),
                "webrtcIPs":           fp.get("webrtcIPs", []),
                "webglRenderer":       renderer,
                "pluginCount":         fp.get("pluginCount"),
                "screenRes":           f"{fp.get('screenWidth')}x{fp.get('screenHeight')}",
                "pixelRatio":          fp.get("pixelRatio"),
                "automationProps":     fp.get("automationProps", []),
                "cookieCount":         cookie_count,
            },
            "breakdown": {
                "automation_clean": not fp.get("webdriver") and not fp.get("automationProps"),
                "webrtc_clean":     not fp.get("webrtcLeak"),
                "timezone_match":   (expected_tz == actual_tz) if expected_tz else None,
                "webgl_real":       not any(vr in renderer for vr in virtual_renderers),
                "has_plugins":      fp.get("pluginCount", 0) > 0,
                "has_cookies":      has_cookies,
            },
        }