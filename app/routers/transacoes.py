"""
Transacoes router - gerencia transações financeiras e trilha de auditoria.

Endpoints:
    POST / - Criar uma nova transação
    GET / - Listar transações com filtros opcionais
    GET /{transacao_id} - Obter detalhes de uma transação específica
    DELETE /{transacao_id} - Deletar uma transação (exclusão lógica)
    GET /auditoria/ - Listar trilha de auditoria de todas as transações do usuário
    GET /auditoria/{transacao_id} - Obter trilha de auditoria de uma transação específica
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.transacoes import (
    TransacaoCreate,
    TransacaoResponse,
    AuditoriaResposta,
)
from app.services import transacoes_service, auditoria_service

router = APIRouter(prefix="/transacoes", tags=["Transações"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def criar_transacao(
    transacao_dados: TransacaoCreate,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Criar uma nova transação.

    Args:
        transacao_dados: Dados da transação (conta_id, categoria_id, tipo, valor, descricao, data_transacao)
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        TransacaoResponse: Dados da transação criada com transacao_id

    Raises:
        HTTPException: 400 se os dados da transação forem inválidos
        HTTPException: 404 se conta_id ou categoria_id não forem encontrados
    """
    try:
        nova_transacao = transacoes_service.criar_transacao(
            user_id=usuario_atual["user_id"],
            dados=transacao_dados,
        )
        return nova_transacao
    except ValueError as e:
        # Verificar se a exceção possui um atributo especial status_code
        status_code = getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST)
        raise HTTPException(
            status_code=status_code,
            detail=str(e),
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in criar_transacao: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar transação: {str(e)}",
        )


@router.get("/", response_model=list[TransacaoResponse])
def listar_transacoes(
    usuario_atual: dict = Depends(obter_usuario_atual),
    conta_id: str | None = Query(None, description="Filter by account ID"),
    categoria_id: str | None = Query(None, description="Filter by category ID"),
    data_inicio: date | None = Query(None, description="Filter from start date"),
    data_fim: date | None = Query(None, description="Filter to end date"),
) -> list:
    """
    Listar transações do usuário atual com filtros opcionais.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência
        conta_id: Filtro opcional de ID da conta
        categoria_id: Filtro opcional de ID da categoria
        data_inicio: Filtro opcional de data de início (inclusivo)
        data_fim: Filtro opcional de data de fim (inclusivo)

    Returns:
        list[TransacaoResponse]: Lista de transações correspondentes aos filtros
    """
    transacoes = transacoes_service.listar_transacoes(
        user_id=usuario_atual["user_id"],
        conta_id=conta_id,
        categoria_id=categoria_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return transacoes


@router.get("/{transacao_id}", response_model=TransacaoResponse)
def obter_transacao(
    transacao_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Obter detalhes de uma transação específica.

    Args:
        transacao_id: ID da transação
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        TransacaoResponse: Detalhes da transação

    Raises:
        HTTPException: 404 se a transação não for encontrada ou não pertencer ao usuário
    """
    transacao = transacoes_service.obter_transacao(
        user_id=usuario_atual["user_id"],
        transacao_id=transacao_id,
    )

    if not transacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada",
        )

    return transacao


@router.delete("/{transacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_transacao(
    transacao_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> None:
    """
    Deletar uma transação (exclusão lógica).

    Args:
        transacao_id: ID da transação
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        None

    Raises:
        HTTPException: 404 se a transação não for encontrada ou não pertencer ao usuário
    """
    sucesso = transacoes_service.deletar_transacao(
        user_id=usuario_atual["user_id"],
        transacao_id=transacao_id,
    )

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada",
        )


@router.get("/auditoria/", response_model=list[AuditoriaResposta])
def listar_auditoria(
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> list:
    """
    Listar trilha de auditoria de todas as transações do usuário atual.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        list[AuditoriaResposta]: Lista de entradas de auditoria
    """
    auditoria = auditoria_service.listar_auditoria(usuario_atual["user_id"])
    return auditoria


@router.get("/auditoria/verificar-integridade")
def verificar_integridade_auditoria(
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Verificar integridade HMAC-SHA256 da cadeia de auditoria completa do usuário atual.

    Recalcula o HMAC-SHA256 de cada registro de auditoria e compara com o
    hash armazenado, detectando registros que foram modificados, adicionados ou deletados
    diretamente no banco de dados (sem passar pela API).

    IMPORTANTE: Esta rota deve ser definida ANTES de /auditoria/{transacao_id} para que
    o FastAPI não trate "verificar-integridade" como um parâmetro de caminho transacao_id.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência.

    Returns:
        dict com:
            - integra (bool): True se todos os hashes forem válidos.
            - total_registros (int): Número de registros verificados.
            - registros_com_erro (list): IDs de auditoria com hashes inválidos.
            - detalhes (dict): Metadados adicionais da verificação.
    """
    return auditoria_service.verificar_integridade_cadeia(usuario_atual["user_id"])


@router.get("/auditoria/{transacao_id}", response_model=list[AuditoriaResposta])
def obter_auditoria_transacao(
    transacao_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> list:
    """
    Obter trilha de auditoria de uma transação específica.

    Args:
        transacao_id: ID da transação
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        list[AuditoriaResposta]: Lista de entradas de auditoria da transação

    Raises:
        HTTPException: 404 se a transação não for encontrada ou não pertencer ao usuário
    """
    auditoria = auditoria_service.obter_auditoria_transacao(
        user_id=usuario_atual["user_id"],
        transacao_id=transacao_id,
    )

    if not auditoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada",
        )

    return auditoria
