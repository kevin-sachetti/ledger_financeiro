"""
Utilitários de segurança para o mini-gestor-financeiro.

Este módulo fornece funções criptográficas e de autenticação incluindo:
- Hashing e verificação de senhas usando bcrypt
- Criação e decodificação de tokens JWT
- Geração de hash de transações para trilhas de auditoria usando HMAC-SHA256
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import hashlib
import hmac
import json

from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import settings


# Contexto bcrypt para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """
    Gera o hash de uma senha usando o algoritmo bcrypt.

    Args:
        senha: A senha em texto puro para gerar o hash.

    Returns:
        A string da senha hasheada adequada para armazenamento.
    """
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    """
    Verifica uma senha em texto puro contra seu hash bcrypt.

    Args:
        senha: A senha em texto puro para verificar.
        hash: O hash bcrypt para comparação.

    Returns:
        True se a senha corresponder ao hash, False caso contrário.
    """
    return pwd_context.verify(senha, hash)


def criar_token_acesso(dados: Dict[str, Any]) -> str:
    """
    Cria um token de acesso JWT com expiração.

    Args:
        dados: Dicionário contendo as claims para codificar no token.
               Normalmente deve incluir 'sub' (subject/user_id) e 'email'.

    Returns:
        String do token JWT codificado.
    """
    dados_copia = dados.copy()

    # Define o tempo de expiração a partir das configurações
    expiracao = datetime.now(timezone.utc) + timedelta(
        minutes=settings.TOKEN_EXPIRE_MINUTES
    )
    dados_copia.update({"exp": expiracao})

    # Codifica o token
    token_codificado = jwt.encode(
        dados_copia,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token_codificado


def decodificar_token(token: str) -> Dict[str, Any]:
    """
    Decodifica e valida um token de acesso JWT.

    Args:
        token: A string do token JWT para decodificar.

    Returns:
        Dicionário contendo as claims do token decodificado.

    Raises:
        JWTError: Se o token for inválido, expirado ou não puder ser decodificado.
    """
    try:
        dados_decodificados = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return dados_decodificados
    except JWTError as e:
        raise JWTError(f"Token inválido: {str(e)}")


def gerar_hash_transacao(dados: Dict[str, Any]) -> str:
    """
    Gera um hash HMAC-SHA256 dos dados da transação para trilha de auditoria.

    Utiliza HMAC (Código de Autenticação de Mensagem baseado em Hash) com SHA-256 para criar
    um hash com chave que fornece garantias de integridade e autenticidade.
    Diferente do SHA-256 puro, o HMAC previne falsificação de registros de auditoria,
    pois a chave secreta é necessária para produzir um hash válido.

    Args:
        dados: Dicionário contendo os dados da transação para gerar o hash.

    Returns:
        Representação em string hexadecimal do digest HMAC-SHA256.
    """
    # Converte o dicionário para string JSON com chaves ordenadas para consistência
    dados_json = json.dumps(dados, sort_keys=True, default=str)

    # Gera HMAC-SHA256 usando a chave secreta da aplicação
    chave_secreta = settings.HMAC_SECRET.encode("utf-8")
    mac = hmac.new(chave_secreta, dados_json.encode("utf-8"), hashlib.sha256)

    return mac.hexdigest()


def verificar_hmac_transacao(dados: Dict[str, Any], hash_esperado: str) -> bool:
    """
    Verifica um hash HMAC-SHA256 dos dados da transação usando comparação em tempo constante.

    Utiliza hmac.compare_digest para prevenir ataques de temporização durante a comparação de hash.

    Args:
        dados: Dicionário contendo os dados da transação para verificar.
        hash_esperado: Digest hexadecimal HMAC-SHA256 esperado para comparação.

    Returns:
        True se o hash calculado corresponder ao hash esperado, False caso contrário.
    """
    hash_calculado = gerar_hash_transacao(dados)
    return hmac.compare_digest(hash_calculado, hash_esperado)
