"""
Mini Gestor Financeiro - Ponto de entrada da aplicação.

API de Gestão Financeira Pessoal construída com FastAPI e DynamoDB.
Permite gerenciar contas, transações, categorias, orçamentos,
gerar relatórios e consultar cotações do Banco Central do Brasil.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.tabelas import TabelasDynamoDB
from app.routers import (
    categorias,
    contas,
    cotacoes,
    orcamentos,
    relatorios,
    snapshots,
    transacoes,
    usuarios,
)
from app.services.snapshot_service import iniciar_scheduler_snapshots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação."""
    logger.info("Iniciando Mini Gestor Financeiro...")
    settings = get_settings()
    logger.info("Conectando ao DynamoDB em %s", settings.DYNAMODB_ENDPOINT)

    try:
        tabelas = TabelasDynamoDB()
        tabelas.criar_todas_tabelas()
        logger.info("Tabelas DynamoDB inicializadas com sucesso.")
    except Exception as e:
        logger.error("Erro ao inicializar tabelas: %s", e)
        raise

    # Iniciar tarefa em segundo plano para snapshot periódico da Árvore de Merkle
    snapshot_task = iniciar_scheduler_snapshots()
    logger.info(
        "Scheduler de snapshots Merkle iniciado (intervalo: %dh).",
        settings.SNAPSHOT_INTERVAL_HOURS,
    )

    yield

    # Cancelar a tarefa em segundo plano ao encerrar
    snapshot_task.cancel()
    logger.info("Encerrando Mini Gestor Financeiro.")


app = FastAPI(
    title="Mini Gestor Financeiro",
    description=(
        "API de Gestão Financeira Pessoal. "
        "Gerencie contas, transações, categorias, orçamentos, "
        "relatórios e cotações do Banco Central do Brasil."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuarios.router)
app.include_router(contas.router)
app.include_router(transacoes.router)
app.include_router(categorias.router)
app.include_router(orcamentos.router)
app.include_router(relatorios.router)
app.include_router(cotacoes.router)
app.include_router(snapshots.router)


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """Verifica se a API está funcionando."""
    return {
        "status": "ok",
        "projeto": "Mini Gestor Financeiro",
        "versao": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Endpoint de health check detalhado."""
    settings = get_settings()
    return {
        "status": "healthy",
        "database": settings.DYNAMODB_ENDPOINT,
        "region": settings.DYNAMODB_REGION,
    }
