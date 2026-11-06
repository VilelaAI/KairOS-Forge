#!/usr/bin/env python3
"""segredos.py — o que é segredo, numa regra só (ADR-0056 e a emenda de v0.50.4).

Usada por quem tira o segredo de um texto antes que ele vá a algum lugar:
- o `guardrail.py saida`, na saída de uma ferramenta, antes de o modelo ler;
- o `guardrail.py ocultar`, no que os gatilhos de CI leem e publicam;
- tudo o que o `guardrail.py` e o `execucao.py` gravam na trajetória
  (`.agents/execucoes/`), que pode ir para o git do projeto;
- o `telemetria.py corroborar`, que compara o comando alegado com o gravado.

Só formatos de alta precisão. O falso positivo esconde um valor; o falso negativo manda
o segredo para fora. Por isso não há detecção por entropia: ela esconderia hash e id em
toda linha. Só stdlib, sem I/O.
"""
from __future__ import annotations

import re

MARCA_SEGREDO = "«segredo ocultado pelo kairos-forge: {tipo}»"
# Valor de variável secreta: um token inteiro, terminado por espaço, aspas ou pontuação,
# que não começa como referência (`$X`, `<seu-token>`, `{{ }}`, `***`). Assim
# `api_key = os.environ["API_KEY"]` e `token = get_token()` não são valor.
VALOR = r"(?![$<{%*])([A-Za-z0-9_\-+/=.:@!#^&~]{8,})(?=[\s'\",;}\]]|$)"
# O token depois de `Bearer` tem de ter um dígito: "Bearer authentication" é texto.
VALOR_BEARER = r"(?![$<{%*])(?=[A-Za-z0-9_\-+/=.~]*\d)([A-Za-z0-9_\-+/=.~]{16,})"

SEGREDOS_NA_SAIDA: list[tuple[re.Pattern, str, int]] = [    # (padrão, tipo, grupo do valor)
    (re.compile(r"-----BEGIN ([A-Z ]*)PRIVATE KEY-----[\s\S]*?(?:-----END \1PRIVATE KEY-----|\Z)"),
     "chave privada", 0),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "chave de acesso AWS", 0),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"), "token GitHub", 0),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "token GitLab", 0),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), "token Slack", 0),
    (re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), "chave Stripe", 0),
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"), "chave de API de modelo", 0),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "chave de API Google", 0),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT", 0),
    (re.compile(r"(?i)\bbearer\s+" + VALOR_BEARER), "token Bearer", 1),
    (re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]{3,})@"), "senha em URL de conexão", 1),
    (re.compile(r"(?:^|\s)(?:-u|--user)\s+['\"]?[^\s:'\"]+:" + VALOR), "senha em usuário:senha", 1),
    (re.compile(r"(?i)--(?:password|passwd|token|secret|api-?key|client-secret|auth-token"
                r"|access-token)\s+['\"]?" + VALOR), "valor de flag secreta", 1),
    (re.compile(r"\b[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_KEY|ACCESS_KEY)"
                r"[A-Z0-9_]*['\"]?\s*[=:]\s*['\"]?" + VALOR), "valor de variável secreta", 1),
    (re.compile(r"\b(?:password|passwd|secret|token|api_?key|access_?key|private_?key"
                r"|client_?secret|auth_?token)['\"]?\s*[=:]\s*['\"]?" + VALOR), "valor de chave secreta", 1),
]


def ocultar_segredos(texto: str) -> tuple[str, list[str]]:
    """O texto com cada segredo trocado pela marca, e o tipo de cada um, em ordem."""
    tipos: list[str] = []
    for padrao, tipo, grupo in SEGREDOS_NA_SAIDA:
        def trocar(m: re.Match, tipo: str = tipo, grupo: int = grupo) -> str:
            tipos.append(tipo)
            inteiro, base = m.group(0), m.start()
            return (inteiro[:m.start(grupo) - base] + MARCA_SEGREDO.format(tipo=tipo)
                    + inteiro[m.end(grupo) - base:])
        texto = padrao.sub(trocar, texto)
    return texto, tipos


def ocultar(texto: str) -> str:
    """Só o texto, para quem grava e não precisa dos tipos."""
    return ocultar_segredos(texto)[0]
