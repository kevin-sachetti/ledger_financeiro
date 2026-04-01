"""
Middleware de autenticação para o mini-gestor-financeiro.

Este módulo fornece autenticação baseada em JWT utilizando o sistema Depends do FastAPI,
incluindo o esquema OAuth2PasswordBearer e funções de autenticação de usuário.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.utils.seguranca import decodificar_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/usuarios/login",
    description="Token JWT para autenticação",
)


async def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, Any]:
    """
    Função de dependência para extrair e validar o usuário atual a partir do token JWT.

    Decodifica o token JWT, extrai o user_id da claim 'sub',
    consulta o DynamoDB para obter os detalhes do usuário e retorna as informações.

    Args:
        token: String do token JWT da requisição.

    Returns:
        Dicionário contendo os dados do usuário.

    Raises:
        HTTPException: 401 se o token for inválido, expirado ou o usuário não for encontrado.
    """
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        dados_token = decodificar_token(token)
    except Exception:
        raise credenciais_invalidas

    usuario_id = dados_token.get("sub")
    if not usuario_id:
        raise credenciais_invalidas

    # Importação aqui para evitar importações circulares
    from app.services.usuarios_service import obter_usuario_por_id

    try:
        usuario = obter_usuario_por_id(usuario_id)
    except Exception:
        raise credenciais_invalidas

    if not usuario:
        raise credenciais_invalidas

    return usuario
