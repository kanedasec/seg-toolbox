import pkgutil
import importlib
import inspect
import time
from typing import Dict, Any, List
from pathlib import Path
from utils.logger import get_logger
from utils.results import save_result_csv, save_result_json, enrich_result
from tests.base import BaseTest

logger = get_logger("main")
TESTS_PACKAGE = "tests"


def discover_tests() -> List[BaseTest]:
    """Descobre e importa automaticamente os módulos em src/tests/"""
    tests = []
    package = importlib.import_module(f"{TESTS_PACKAGE}")
    package_path = Path(package.__file__).parent

    for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
        if name.startswith("_"):
            continue
        full_name = f"{TESTS_PACKAGE}.{name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as e:
            logger.error(f"Falha ao importar {full_name}: {e}")
            continue

        if hasattr(mod, "test"):
            candidate = getattr(mod, "test")
            if isinstance(candidate, BaseTest):
                tests.append(candidate)
                continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, BaseTest) and obj is not BaseTest:
                try:
                    inst = obj()
                    tests.append(inst)
                except Exception as e:
                    logger.error(f"Falha instanciando {obj}: {e}")
    return tests


def prompt_inputs(requires: Dict[str, str]) -> Dict[str, Any]:
    inputs = {}
    for key, prompt in requires.items():
        val = input(prompt).strip()
        inputs[key] = val
    return inputs


def pretty_print_result(res: Dict[str, Any]):
    from rich import print_json
    try:
        print_json(data=res)
    except Exception:
        print(res)


def ask_save_result() -> str | None:
    """
    Pergunta se o usuário quer salvar o resultado.
    Retorna 'csv', 'json' ou None.
    """
    choice = input("\nDeseja salvar o resultado em CSV, JSON ou não salvar? (csv/json/N): ").strip().lower()
    if choice in ["csv", "json"]:
        return choice
    return None


def main():
    logger.info("Iniciando Security Toolbox")
    tests = discover_tests()
    if not tests:
        logger.warning("Nenhum teste encontrado em src/tests.")
        return

    while True:
        print("\n=== Testes disponíveis ===")
        for i, t in enumerate(tests, start=1):
            print(f"{i}) {t.name} — {t.description}")
        print("0) Sair")

        choice = input("\nEscolha um teste (número): ").strip()
        if choice == "0":
            logger.info("Saindo.")
            break

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(tests):
                print("Escolha inválida.")
                continue
        except ValueError:
            print("Escolha inválida.")
            continue

        selected = tests[idx]
        print(f"\nExecutando: {selected.name} — {selected.description}\n")
        inputs = prompt_inputs(selected.requires)
        logger.info(f"Inputs recebidos: {inputs}")

        try:
            start_time = time.time()
            result = selected.run(inputs)
            enriched = enrich_result(selected.name, result, start_time)
            pretty_print_result(enriched)

            save_format = ask_save_result()
            if save_format == "csv":
                saved_path = save_result_csv(selected.name, enriched)
                print(f"Resultado salvo em: {saved_path}")
            elif save_format == "json":
                saved_path = save_result_json(selected.name, enriched)
                print(f"Resultado salvo em: {saved_path}")

        except Exception as e:
            logger.exception(f"Erro ao executar o teste: {e}")


if __name__ == "__main__":
    main()
