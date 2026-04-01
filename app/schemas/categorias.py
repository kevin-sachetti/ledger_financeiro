"""Schemas de categoria para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class CategoriaCreate(BaseModel):
    """Schema para criação de uma nova categoria.

    Atributos:
        nome: Nome da categoria.
        descricao: Descrição da categoria (opcional).
        tipo: Tipo da categoria (receita para entradas, despesa para gastos).
        cor: Código de cor hexadecimal da categoria (opcional).
        icone: Identificador do ícone da categoria (opcional).
    """

    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = Field(None, max_length=500)
    tipo: Literal["receita", "despesa"]
    cor: Optional[str] = Field(None, min_length=7, max_length=7)
    icone: Optional[str] = Field(None, max_length=50)


class CategoriaResponse(BaseModel):
    """Schema para resposta de categoria.

    Atributos:
        categoria_id: Identificador único da categoria.
        user_id: Proprietário da categoria.
        nome: Nome da categoria.
        descricao: Descrição da categoria.
        tipo: Tipo da categoria.
        cor: Código de cor hexadecimal da categoria.
        icone: Identificador do ícone da categoria.
    """

    categoria_id: str
    user_id: str
    nome: str
    descricao: Optional[str]
    tipo: Literal["receita", "despesa"]
    cor: Optional[str]
    icone: Optional[str]
