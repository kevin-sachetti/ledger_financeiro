"""
Usuarios router - gerencia autenticação e perfil de usuários.

Endpoints:
    POST /registrar - Registrar um novo usuário
    POST /login - Fazer login e obter token JWT
    GET /perfil - Obter perfil do usuário atual
    PUT /perfil - Atualizar perfil do usuário atual
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.usuarios import (
    UsuarioRegistro,
    UsuarioResposta,
    UsuarioPerfil,
    UsuarioUpdate,
    TokenResposta,
)
from app.services import usuarios_service as usuarios_svc
from app.utils.seguranca import criar_token_acesso

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/registrar", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario_dados: UsuarioRegistro) -> dict:
    """
    Registrar um novo usuário.

    Args:
        usuario_dados: Dados de registro do usuário (email, nome, senha)

    Returns:
        UsuarioResposta: Dados do usuário com user_id

    Raises:
        HTTPException: 400 se o email já existir
    """
    try:
        novo_usuario = usuarios_svc.criar_usuario(
            dados=usuario_dados,
        )
        return novo_usuario
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResposta)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    Fazer login e obter token JWT.

    Aceita nome de usuário e senha via OAuth2PasswordRequestForm para compatibilidade com Swagger.
    O nome de usuário deve ser o email do usuário.

    Args:
        form_data: Dados do formulário OAuth2 com username (email) e password

    Returns:
        TokenResposta: Token JWT e tipo do token

    Raises:
        HTTPException: 401 se as credenciais forem inválidas
    """
    usuario = usuarios_svc.autenticar_usuario(form_data.username, form_data.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = criar_token_acesso({"sub": usuario["user_id"], "email": usuario["email"]})

    return {"access_token": token, "token_type": "bearer"}


@router.get("/perfil", response_model=UsuarioPerfil)
def obter_perfil(usuario_atual: dict = Depends(obter_usuario_atual)) -> dict:
    """
    Obter perfil do usuário atual.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        UsuarioPerfil: Dados do perfil do usuário
    """
    usuario = usuarios_svc.obter_usuario_por_id(usuario_atual["user_id"])
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    return usuario


@router.put("/perfil", response_model=UsuarioPerfil)
def atualizar_perfil(
    perfil_dados: UsuarioPerfil,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Atualizar perfil do usuário atual.

    Args:
        perfil_dados: Dados atualizados do perfil do usuário
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        UsuarioPerfil: Dados do perfil do usuário atualizado

    Raises:
        HTTPException: 404 se o usuário não for encontrado, 400 se o email já existir
    """
    dados_atualizacao = UsuarioUpdate(
        nome=perfil_dados.nome,
        email=perfil_dados.email,
    )
    try:
        usuario_atualizado = usuarios_svc.atualizar_usuario(
            user_id=usuario_atual["user_id"],
            dados=dados_atualizacao,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not usuario_atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    return usuario_atualizado
