"""
Utilitários de validação para o mini-gestor-financeiro.

Este módulo fornece funções de validação para diversos tipos de dados financeiros,
incluindo tipos de conta, tipos de transação, moedas e valores monetários.
"""

from typing import Optional


# Valores válidos para diferentes entidades financeiras
TIPOS_CONTA_VALIDOS = {"corrente", "poupanca", "investimento", "carteira"}
TIPOS_TRANSACAO_VALIDOS = {"deposito", "saque", "transferencia"}
MOEDAS_VALIDAS = {"BRL", "USD", "EUR"}


def validar_valor_positivo(valor: float) -> bool:
    """
    Valida se um valor é positivo e maior que zero.

    Args:
        valor: O valor numérico a ser validado.

    Returns:
        True se o valor for positivo, False caso contrário.
    """
    try:
        return float(valor) > 0
    except (TypeError, ValueError):
        return False


def validar_tipo_conta(tipo: str) -> bool:
    """
    Valida se o tipo de conta é um dos tipos permitidos.

    Tipos válidos: corrente, poupanca, investimento, carteira.

    Args:
        tipo: A string do tipo de conta a ser validada.

    Returns:
        True se o tipo for válido, False caso contrário.
    """
    if not isinstance(tipo, str):
        return False
    return tipo.lower() in TIPOS_CONTA_VALIDOS


def validar_tipo_transacao(tipo: str) -> bool:
    """
    Valida se o tipo de transação é um dos tipos permitidos.

    Tipos válidos: deposito, saque, transferencia.

    Args:
        tipo: A string do tipo de transação a ser validada.

    Returns:
        True se o tipo for válido, False caso contrário.
    """
    if not isinstance(tipo, str):
        return False
    return tipo.lower() in TIPOS_TRANSACAO_VALIDOS


def validar_moeda(moeda: str) -> bool:
    """
    Valida se o código da moeda é uma das moedas suportadas.

    Moedas válidas: BRL, USD, EUR.

    Args:
        moeda: A string do código da moeda a ser validada.

    Returns:
        True se a moeda for válida, False caso contrário.
    """
    if not isinstance(moeda, str):
        return False
    return moeda.upper() in MOEDAS_VALIDAS


def validar_mes(mes: int) -> bool:
    """
    Valida se o valor do mês está entre 1 e 12 (inclusive).

    Args:
        mes: O número do mês a ser validado.

    Returns:
        True se o mês for válido, False caso contrário.
    """
    try:
        mes_int = int(mes)
        return 1 <= mes_int <= 12
    except (TypeError, ValueError):
        return False


def validar_ano(ano: int) -> bool:
    """
    Valida se o ano está dentro do intervalo aceitável (2000-2100).

    Args:
        ano: O ano a ser validado.

    Returns:
        True se o ano for válido, False caso contrário.
    """
    try:
        ano_int = int(ano)
        return 2000 <= ano_int <= 2100
    except (TypeError, ValueError):
        return False


def formatar_valor_monetario(valor: float, moeda: str) -> str:
    """
    Formata um valor numérico como string monetária com símbolo da moeda.

    Args:
        valor: O valor numérico a ser formatado.
        moeda: O código da moeda (BRL, USD, EUR).

    Returns:
        String monetária formatada (ex.: "R$ 1.234,56", "$1,234.56", "€1.234,56").

    Raises:
        ValueError: Se a moeda não for suportada.
    """
    if not validar_moeda(moeda):
        raise ValueError(f"Moeda inválida: {moeda}")

    moeda_upper = moeda.upper()

    # Formata conforme convenções de cada moeda
    if moeda_upper == "BRL":
        # Formato brasileiro: R$ 1.234,56
        return f"R$ {valor:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    elif moeda_upper == "USD":
        # Formato americano: $1,234.56
        return f"${valor:,.2f}"
    elif moeda_upper == "EUR":
        # Formato europeu: €1.234,56
        return f"€{valor:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

    # Fallback (não deveria chegar aqui devido à verificação de validar_moeda)
    return f"{valor:.2f} {moeda_upper}"
