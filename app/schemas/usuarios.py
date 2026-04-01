"""Schemas de usuário para validação de requisição/resposta."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UsuarioCreate(BaseModel):
    """Schema para criação de um novo usuário.

    Atributos:
        nome: Nome completo do usuário.
        email: Endereço de e-mail do usuário.
        senha: Senha do usuário (será hasheada antes do armazenamento).
    """

    nome: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=255)


class UsuarioRegistro(UsuarioCreate):
    """Schema para registro de usuário (alias de UsuarioCreate para compatibilidade)."""

    pass


class UsuarioLogin(BaseModel):
    """Schema para login de usuário.

    Atributos:
        email: Endereço de e-mail do usuário.
        senha: Senha do usuário.
    """

    email: EmailStr
    senha: str = Field(..., min_length=1)


class UsuarioResponse(BaseModel):
    """Schema para resposta de usuário.

    Atributos:
        user_id: Identificador único do usuário.
        nome: Nome completo do usuário.
        email: Endereço de e-mail do usuário.
        criado_em: Data/hora de criação do usuário.
    """

    user_id: str
    nome: str
    email: str
    criado_em: datetime


class UsuarioResposta(UsuarioResponse):
    """Schema para resposta de usuário (alias de UsuarioResponse para compatibilidade)."""

    pass


class UsuarioUpdate(BaseModel):
    """Schema para atualização de informações do usuário.

    Atributos:
        nome: Nome completo do usuário (opcional).
        email: Endereço de e-mail do usuário (opcional).
        senha: Senha do usuário (opcional).
    """

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    senha: Optional[str] = Field(None, min_length=8, max_length=255)


class UsuarioPerfil(BaseModel):
    """Schema para informações de perfil do usuário.

    Atributos:
        user_id: Identificador único do usuário.
        nome: Nome completo do usuário.
        email: Endereço de e-mail do usuário.
    """

    user_id: Optional[str] = None
    nome: str = Field(..., min_length=1, max_length=255)
    email: EmailStr


class TokenResponse(BaseModel):
    """Schema para resposta de token de autenticação.

    Atributos:
        access_token: Token de acesso JWT.
        token_type: Tipo do token (tipicamente "bearer").
    """

    access_token: str
    token_type: str


class TokenResposta(TokenResponse):
    """Schema para resposta de token de autenticação (alias de TokenResponse para compatibilidade)."""

    pass
