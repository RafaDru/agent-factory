"""Handlers para o agente demo declarativo."""

from pathlib import Path
from src.protocols.schema import TaskOutput


def saudacao(self, task: dict) -> TaskOutput:
    nome = task.get("nome", "Mundo")
    return TaskOutput.success(
        summary=f"Ola, {nome}!",
        rationale=f"Saudacao gerada para {nome}",
        nome=nome,
    )


def ler_arquivo(self, task: dict) -> TaskOutput:
    caminho = task.get("caminho") or task.get("file_path") or task.get("path")
    if not caminho:
        return TaskOutput.needs_direction(
            rationale="Informe o caminho do arquivo.",
            available_actions=["escrever_arquivo"],
        )
    path = Path(caminho)
    if not path.exists():
        return TaskOutput.failure(rationale=f"Arquivo nao encontrado: {path}")
    try:
        conteudo = path.read_text(encoding="utf-8")
        return TaskOutput.success(
            summary=f"Lido: {path.name} ({len(conteudo)} chars)",
            rationale=conteudo[:200],
            path=str(path), tamanho=len(conteudo),
        )
    except Exception as e:
        return TaskOutput.failure(rationale=f"Erro ao ler: {e}")
