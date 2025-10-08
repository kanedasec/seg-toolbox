# src/tests/cookie_verification.py
from typing import Dict, Any, List, Optional
import re
import sys
import requests
import time
from .base import BaseTest

def _read_multiline(prompt: str) -> str:
    print(prompt)
    lines: List[str] = []
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        raw = line.rstrip("\n")
        if raw.strip() == "":
            break
        lines.append(raw)
    return "\n".join(lines)

def _split_set_cookie_block(raw: str) -> List[str]:
    """
    Heurística para quebrar um possível bloco 'Set-Cookie' em múltiplos cookies.
    - Se já vier como lista, apenas retorna.
    - Caso venha como string única, tenta separar por linhas. Se for um único cabeçalho
      com múltiplos cookies concatenados, utiliza uma regex que tenta não cortar datas de Expires.
    Nota: não é 100% infalível para todos os servidores, mas cobre os casos comuns.
    """
    if not raw:
        return []

    # Se já parece múltiplas linhas, preserve separação por linha
    if "\n" in raw:
        parts = [ln for ln in raw.splitlines() if ln.strip()]
        if len(parts) > 1:
            return parts

    # heurística para split: split em ", " somente quando o token seguinte
    # parece ser um cookie-name (alnum or _ or -) seguido de '='
    # isso evita quebrar datas em Expires (ex: "Wed, 21 Oct 2020 07:28:00 GMT")
    pattern = re.compile(r", (?=[A-Za-z0-9_\-]+\=)")
    parts = pattern.split(raw)
    # strip e filtrar vazios
    return [p.strip() for p in parts if p.strip()]

def _parse_set_cookie(header_value: str) -> Dict[str, Any]:
    """
    Recebe uma única string de Set-Cookie (ex: 'NAME=val; Path=/; Secure; HttpOnly; SameSite=Lax')
    e retorna um dict com name, value, atributos e flags booleans.
    """
    parts = [p.strip() for p in header_value.split(";")]
    if not parts:
        return {}

    # primeiro pedaço normalmente é "NAME=VALUE" (mas verifique)
    first = parts[0]
    if "=" in first:
        name, value = first.split("=", 1)
        name = name.strip()
        value = value.strip()
    else:
        name = first.strip()
        value = ""

    attrs = {}
    flags = {
        "secure": False,
        "httponly": False,
        "samesite": None  # pode ser 'Lax', 'Strict', 'None' ou None
    }

    # iterar pelas demais partes para extrair atributos
    for attr in parts[1:]:
        if not attr:
            continue
        if "=" in attr:
            k, v = attr.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            attrs[k] = v
            if k == "samesite":
                flags["samesite"] = v
            # store expires/domain/path as attrs (lowercase keys)
        else:
            token = attr.strip().lower()
            if token == "secure":
                flags["secure"] = True
            elif token == "httponly":
                flags["httponly"] = True
            else:
                # outros tokens (ex: SameSite sem valor) — ignorar ou armazenar
                pass

    # também pegar domínio/path/expires se presentes nos attrs com as chaves originais
    domain = attrs.get("domain")
    path = attrs.get("path")
    expires = attrs.get("expires") if "expires" in attrs else None

    return {
        "raw": header_value,
        "name": name,
        "value": value,
        "domain": domain,
        "path": path,
        "expires": expires,
        "flags": flags,
        "attrs": attrs,
    }

class CookieVerificationTest(BaseTest):
    @property
    def name(self) -> str:
        return "cookie-verification"

    @property
    def description(self) -> str:
        return "Faz request e analisa os cookies retornados em Set-Cookie, extraindo Secure/HttpOnly/SameSite."

    @property
    def requires(self) -> Dict[str, str]:
        return {
            "target": "URL alvo (ex: https://example.com/path): ",
            "method": "Método HTTP (GET or POST) [GET]: ",
            "timeout": "Timeout por requisição (segundos) [5]: ",
            "exclude_list": "Cookies a EXCLUIR da verificação (separados por vírgula, ex: csrftoken,jsessionid) [opcional]: "
        }

    def _read_and_parse_headers(self) -> Dict[str, str]:
        raw = _read_multiline("Cole os cabeçalhos HTTP (headers) — termine com uma linha vazia:")
        headers = {}
        if not raw:
            return headers
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # ignorar request-line se colada
            parts0 = line.split()
            if len(parts0) >= 3 and parts0[0].upper() in ("GET","POST","PUT","DELETE","HEAD","OPTIONS","PATCH") and "HTTP/" in parts0[-1].upper():
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            headers[k.strip()] = v.lstrip()
        return headers

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        target = (inputs.get("target") or "").strip()
        method = (inputs.get("method") or "GET").strip().upper()
        try:
            timeout = float(inputs.get("timeout") or 5.0)
        except Exception:
            timeout = 5.0
        exclude_raw = (inputs.get("exclude_list") or "").strip()
        exclude_names = [n.strip() for n in exclude_raw.split(",") if n.strip()]
        # normalizar para comparações case-insensitive
        exclude_lower = [n.lower() for n in exclude_names]

        if not target:
            return {"error": "target (URL) não informado."}

        headers = self._read_and_parse_headers()

        result = {
            "target": target,
            "method": method,
            "timeout_seconds": timeout,
            "raw_request_headers": headers,
            "raw_set_cookie_headers": [],
            "cookies": [],
            "warnings": []
        }

        start = time.time()
        try:
            sess = requests.Session()
            # enviar requisição
            if method == "GET":
                r = sess.get(target, headers=headers, timeout=timeout, allow_redirects=True)
            elif method == "POST":
                r = sess.post(target, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                r = sess.request(method, target, headers=headers, timeout=timeout, allow_redirects=True)
        except Exception as e:
            result["error"] = f"Request failed: {e}"
            result["duration_seconds"] = round(time.time() - start, 4)
            return result

        # extrair Set-Cookie(s)
        sc_list: List[str] = []

        # 1) tentar obter vários Set-Cookie via r.raw.headers.get_all (mais robusto)
        try:
            raw_headers_container = getattr(r, "raw", None)
            if raw_headers_container is not None:
                raw_h = getattr(raw_headers_container, "headers", None)
                if raw_h is not None and hasattr(raw_h, "get_all"):
                    got = raw_h.get_all("Set-Cookie")
                    if got:
                        sc_list = got
        except Exception:
            pass

        # 2) fallback: requests' r.headers.get("Set-Cookie") (pode ser uma string concatenada)
        if not sc_list:
            sc_hdr = r.headers.get("Set-Cookie")
            if sc_hdr:
                # aplicar heurística para separar possiveis múltiplos cookies
                sc_list = _split_set_cookie_block(sc_hdr)

        # 3) ainda fallback: procurar todas as keys do r.headers que correspondem a Set-Cookie
        if not sc_list:
            for k, v in r.headers.items():
                if k.lower() == "set-cookie":
                    sc_list.append(v)

        result["raw_set_cookie_headers"] = sc_list

        # parsear cada Set-Cookie header
        parsed = []
        for h in sc_list:
            p = _parse_set_cookie(h)
            parsed.append(p)

        # montar warnings: cookie sem Secure/HttpOnly/SameSite (dependendo das regras)
        warnings: List[str] = []
        for cookie in parsed:
            name = cookie.get("name", "")
            lname = name.lower()
            flags = cookie.get("flags", {})
            missing = []
            # regra: se cookie NÃO está na exclude list, exigir Secure + HttpOnly + SameSite (SameSite pode ser None)
            if lname not in exclude_lower:
                if not flags.get("secure", False):
                    missing.append("Secure")
                if not flags.get("httponly", False):
                    missing.append("HttpOnly")
                # SameSite: recomendado. Considerar faltando se None
                if flags.get("samesite") is None:
                    missing.append("SameSite")
            # se houver misses, adicionar warning
            if missing:
                warnings.append(f"Cookie '{name}' missing flags: {', '.join(missing)}")

        result["cookies"] = parsed
        result["warnings"] = warnings
        result["status_code"] = r.status_code
        result["duration_seconds"] = round(time.time() - start, 4)
        return result

# instância esperada pelo loader
test = CookieVerificationTest()
