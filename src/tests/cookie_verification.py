from .base import BaseTest
from typing import Dict, Any
import requests

class CookieVerificationTest(BaseTest):
    @property
    def name(self):
        return "cookie-verification"

    @property
    def description(self):
        return "Verifica atributos de cookies (Secure, HttpOnly, SameSite) em resposta HTTP."

    @property
    def requires(self):
        return {
            "target": "URL alvo (ex: https://example.com): "
        }

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        target = inputs.get("target")
        result = {"target": target, "cookies": []}
        try:
            r = requests.get(target, timeout=10, allow_redirects=True)
            cookies = r.cookies  # cookies do requests (não contém atributos SameSite/HttpOnly)
            # para pegar atributos, devemos analisar cabeçalhos 'Set-Cookie'
            set_cookie_headers = r.headers.get("Set-Cookie")
            if not set_cookie_headers:
                # se houver múltiplos Set-Cookie, requests junta? usamos raw headers:
                set_cookie_headers = r.raw.headers.get_all('Set-Cookie') if hasattr(r.raw, 'headers') else None

            headers = r.headers.get_all('Set-Cookie') if hasattr(r.headers, 'get_all') else None

            # fallback simples: analisar header text completo
            sc_list = []
            if isinstance(set_cookie_headers, str):
                sc_list = [set_cookie_headers]
            elif isinstance(set_cookie_headers, list):
                sc_list = set_cookie_headers
            elif headers:
                sc_list = headers

            for h in sc_list:
                lower = h.lower()
                cookie_info = {
                    "raw": h,
                    "secure": "secure" in lower,
                    "httponly": "httponly" in lower,
                    "samesite": None
                }
                if "samesite=" in lower:
                    # extrair valor simples
                    try:
                        part = [p.strip() for p in h.split(";") if "samesite" in p.lower()][0]
                        cookie_info["samesite"] = part.split("=", 1)[1].strip()
                    except Exception:
                        cookie_info["samesite"] = None
                result["cookies"].append(cookie_info)
            result["status_code"] = r.status_code
        except Exception as e:
            result["error"] = str(e)
        return result

test = CookieVerificationTest()
