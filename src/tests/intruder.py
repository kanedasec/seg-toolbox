# src/tests/intruder.py
from typing import Dict, Any, List
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import statistics
import sys
from .base import BaseTest

_LOCK = threading.Lock()

class IntruderTest(BaseTest):
    @property
    def name(self) -> str:
        return "intruder"

    @property
    def description(self) -> str:
        return "Envia múltiplas requisições (GET/POST) concorrentes para uma URL. Cabeçalhos podem ser colados em multiline."

    @property
    def requires(self) -> Dict[str, str]:
        # Não pedimos headers aqui porque iremos capturá-los em multiline dentro de run()
        return {
            "target": "URL alvo (ex: https://example.com/path): ",
            "method": "Método HTTP (GET or POST) [GET]: ",
            "total": "Número total de requisições (ex: 100): ",
            "concurrency": "Número de requisições simultâneas (threads) (ex: 10): ",
            "timeout": "Timeout por requisição em segundos (ex: 10) [5]: ",
        }

    def _read_multiline_headers(self) -> str:
        """
        Instrui o usuário a colar headers e termina com uma linha vazia.
        Retorna o raw string (com quebras de linha).
        """
        print("\nCole os cabeçalhos HTTP (headers) — termine colando uma linha vazia e pressionando Enter:")
        lines: List[str] = []
        while True:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                raise
            if line is None:
                break
            # strip only trailing \n, keep interior whitespace
            if line.endswith("\n"):
                raw = line[:-1]
            else:
                raw = line
            # Se linha vazia -> finaliza (usuário pressionou Enter numa linha vazia)
            if raw.strip() == "":
                break
            lines.append(raw)
        return "\n".join(lines)

    def _parse_headers(self, raw: str) -> Dict[str, str]:
        """
        Converte o bloco colado de headers em um dict apropriado para requests.
        - Ignora request-line se presente (ex: 'GET /path HTTP/1.1').
        - Cada linha no formato 'Key: Value' é convertida.
        - Linhas sem ':' são ignoradas.
        """
        headers: Dict[str, str] = {}
        if not raw:
            return headers

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Ignora request-line (começa com método e termina com HTTP/x ou tem 'HTTP/')
            parts0 = line.split()
            if len(parts0) >= 3 and parts0[0].upper() in ("GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH") and "HTTP/" in parts0[-1].upper():
                # é uma request-line, pular
                continue
            # normal header parsing: key: value
            if ":" not in line:
                # ignora linhas sem ':'
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.lstrip()
            # Se header já existir, juntamos valores com ', ' (exceto Cookie — mantemos exatamente)
            if key in headers:
                if key.lower() == "cookie":
                    # juntar com '; ' é mais apropriado para cookies
                    headers[key] = headers[key].rstrip("; ") + "; " + value
                else:
                    headers[key] = headers[key] + ", " + value
            else:
                headers[key] = value
        return headers

    def _worker_request(self, url: str, method: str, headers: Dict[str, str], timeout: float, index: int) -> Dict[str, Any]:
        """
        Função executada por cada thread. Cria sua própria Session para evitar efeitos colaterais.
        Retorna um dicionário com o resultado da tentativa.
        """
        session = requests.Session()
        start = time.time()
        try:
            if method == "GET":
                r = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            elif method == "POST":
                # Sem payload por padrão — futuro: adicionar payload/body/ form
                r = session.post(url, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                # fallback: usar request genérico
                r = session.request(method, url, headers=headers, timeout=timeout, allow_redirects=True)

            elapsed = time.time() - start
            return {
                "index": index,
                "ok": True,
                "status_code": r.status_code,
                "reason": r.reason,
                "elapsed_seconds": round(elapsed, 4),
            }
        except Exception as e:
            elapsed = time.time() - start
            return {
                "index": index,
                "ok": False,
                "error": str(e),
                "elapsed_seconds": round(elapsed, 4),
            }

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # --- ler e normalizar inputs ---
        target = (inputs.get("target") or "").strip()
        method = (inputs.get("method") or "GET").strip().upper()
        try:
            total = int(inputs.get("total") or 1)
            if total < 1:
                total = 1
        except Exception:
            total = 1
        try:
            concurrency = int(inputs.get("concurrency") or 1)
            if concurrency < 1:
                concurrency = 1
        except Exception:
            concurrency = 1
        try:
            timeout = float(inputs.get("timeout") or 5.0)
            if timeout <= 0:
                timeout = 5.0
        except Exception:
            timeout = 5.0

        if not target:
            return {"error": "target (URL) não informado."}

        # pedir headers multiline diretamente aqui
        raw_headers = self._read_multiline_headers()
        headers = self._parse_headers(raw_headers)

        # summary containers
        results: List[Dict[str, Any]] = []
        status_counter: Dict[str, int] = {}
        errors = 0
        latencies: List[float] = []

        start_time = time.time()

        # Use ThreadPoolExecutor
        max_workers = min(concurrency, total)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i in range(total):
                fut = executor.submit(self._worker_request, target, method, headers, timeout, i)
                futures[fut] = i

            for fut in as_completed(futures):
                res = fut.result()
                # thread-safe append
                with _LOCK:
                    results.append(res)
                    if res.get("ok"):
                        code = res.get("status_code")
                        code_key = str(code)
                        status_counter[code_key] = status_counter.get(code_key, 0) + 1
                    else:
                        errors += 1
                    if "elapsed_seconds" in res:
                        try:
                            latencies.append(float(res["elapsed_seconds"]))
                        except Exception:
                            pass

        total_time = time.time() - start_time

        # stats
        successes = sum(1 for r in results if r.get("ok"))
        failures = sum(1 for r in results if not r.get("ok"))
        avg_latency = round(statistics.mean(latencies), 4) if latencies else None
        p50 = round(statistics.median(latencies), 4) if latencies else None
        p95 = None
        if latencies:
            try:
                lat_sorted = sorted(latencies)
                idx95 = min(len(lat_sorted)-1, int(len(lat_sorted)*0.95))
                p95 = round(lat_sorted[idx95], 4)
            except Exception:
                p95 = None

        # prepare summary (não retorna detalhes demais por padrão)
        summary = {
            "target": target,
            "method": method,
            "total_requested": total,
            "concurrency": concurrency,
            "timeout_seconds": timeout,
            "wall_time_seconds": round(total_time, 4),
            "requests_sent": len(results),
            "successes": successes,
            "failures": failures,
            "errors": errors,
            "status_counts": status_counter,
            "avg_latency_seconds": avg_latency,
            "p50_latency_seconds": p50,
            "p95_latency_seconds": p95,
            # detalhes limitados (primeiros 100) para inspeção
            "details_sample": results[:100],
        }

        return summary


# instância esperada pelo loader dinâmico
test = IntruderTest()
