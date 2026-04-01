"""
Categorias router - gerencia categorias de despesas.

Endpoints:
    POST / - Criar uma nova categoria
    GET / - Listar todas as categorias do usuário atual
    DELETE /{categoria_id} - Deletar uma categoria
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.categorias import CategoriaCreate, CategoriaResponse
from app.services.categorias_service import CategoriasService

router = APIRouter(prefix="/categorias", tags=["Categorias"])
categorias_service = CategoriasService()


@router.post("/", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
def criar_categoria(
    categoria_dados: CategoriaCreate,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Criar uma nova categoria de despesa.

    Args:
        categoria_dados: Dados da categoria (nome, cor, descricao)
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        CategoriaResponse: Dados da categoria criada com categoria_id

    Raises:
        HTTPException: 400 se os dados da categoria forem inválidos
    """
    nova_categoria = categorias_service.criar_categoria(
        user_id=usuario_atual["user_id"],
        dados=categoria_dados.model_dump(),
    )

    return nova_categoria


@router.get("/", response_model=list[CategoriaResponse])
def listar_categorias(
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> list:
    """
    Listar todas as categorias de despesa do usuário atual.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        list[CategoriaResponse]: Lista de categorias
    """
    categorias = categorias_service.listar_categorias(usuario_atual["user_id"])
    return categorias


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_categoria(
    categoria_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> None:
    """
    Deletar uma categoria de despesa.

    Args:
        categoria_id: ID da categoria
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        None

    Raises:
        HTTPException: 404 se a categoria não for encontrada ou não pertencer ao usuário
    """
    sucesso = categorias_service.deletar_categoria(
        user_id=usuario_atual["user_id"],
        categoria_id=categoria_id,
    )

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada",
        )
