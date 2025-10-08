from .base import BaseTest
from typing import Dict, Any
import time
import random

class IntruderTest(BaseTest):
    @property
    def name(self):
        return "intruder"

    @property
    def description(self):
        return "Simula requisições concorrentes simples contra um endpoint (stress/funcionalidade)."

    @property
    def requires(self):
        return {
            "target": "URL alvo (ex: http://localhost:8000/login): ",
            "threads": "Número de requisições: ",
            "payload": "Payload (json/string) — deixe vazio para payload padrão: "
        }

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        target = inputs.get("target")
        try:
            threads = int(inputs.get("threads", 5))
        except Exception:
            threads = 5
        payload = inputs.get("payload") or '{"username":"test","password":"test"}'

        # Implementação simplificada (mock) - substitua por requests ou urllib para testes reais
        results = {"target": target, "attempts": threads, "successes": 0, "errors": 0, "details": []}

        for i in range(threads):
            # simula latência e resposta aleatória
            time.sleep(0.1 * random.random())
            ok = random.choice([True, True, False])  # mais chances de sucesso para demo
            if ok:
                results["successes"] += 1
                results["details"].append({"id": i, "status": 200, "note": "OK (simulado)"})
            else:
                results["errors"] += 1
                results["details"].append({"id": i, "status": 500, "note": "Erro (simulado)"})

        return results

# exportar a factory/instância esperada pelo loader
test = IntruderTest()
