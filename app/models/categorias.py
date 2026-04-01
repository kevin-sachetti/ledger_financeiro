"""Modelo de categoria para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Literal


@dataclass
class Categoria:
    """Modelo de categoria representando uma categoria de transação.

    Atributos:
        categoria_id: Identificador único da categoria (string UUID).
        user_id: Proprietário da categoria (string UUID).
        nome: Nome da categoria.
        descricao: Descrição da categoria (opcional).
        tipo: Tipo da categoria (receita para entradas, despesa para gastos).
        cor: Código de cor hexadecimal da categoria (opcional).
        icone: Identificador do ícone da categoria (opcional).
    """

    categoria_id: str
    user_id: str
    nome: str
    descricao: Optional[str]
    tipo: Literal["receita", "despesa"]
    cor: Optional[str]
    icone: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Categoria para um dicionário.

        Retorna:
            Representação em dicionário do objeto Categoria.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Categoria":
        """Cria uma instância de Categoria a partir de um dicionário.

        Args:
            data: Dicionário contendo dados da categoria.

        Retorna:
            Instância de Categoria criada a partir do dicionário fornecido.
        """
        return cls(**data)
