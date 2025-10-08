from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTest(ABC):
    """
    Interface que todo teste deve implementar.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def requires(self) -> Dict[str, str]:
        """
        Retorna um dicionário {field_name: prompt} com os inputs necessários.
        Ex: {"target": "URL alvo (http://...): "}
        """
        return {}

    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o teste. Deve retornar um dicionário com resultados/metadata.
        """
        pass
