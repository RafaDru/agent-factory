"""
Context Tree — Árvore de Contexto para Agentes
===============================================
Gerencia INDEX.md + domínios segmentados.
Pre-hook: tria qual contexto carregar.
Post-hook: persiste aprendizado.
"""
import json
import re
from pathlib import Path
from typing import Any, Optional

from src.protocols.schema import TaskOutput
from src.sdk.hooks import HookContext, HookPoint


class ContextTree:
    """
    Árvore de contexto para um agente específico.

    Estrutura:
    contexts/<project_id>/<agent_id>/
      INDEX.md              # Índice segmentado
      tree/
        bugs.md             # Bugs conhecidos
        features.md         # Funcionalidades
        arquitetura.md      # Decisões técnicas
        licoes.md           # Aprendizados consolidados
    """

    # Mapeamento task_action -> domínios relevantes (keyword fallback)
    ACTION_DOMAIN_MAP = {
        "read_file": ["arquitetura", "features"],
        "write_file": ["features"],
        "generate_code": ["features", "arquitetura"],
        "refactor_code": ["features", "bugs", "arquitetura"],
        "edit_file": ["features", "bugs"],
        "run_tests": ["bugs"],
        "review_code": ["bugs", "features", "licoes"],
        "lint": ["bugs"],
        "plan_and_execute": ["features", "arquitetura"],
        "delegate": ["features", "arquitetura"],
        "list_directory": [],
        "run_git": [],
        "validate_python_syntax": ["bugs"],
        "analyze_project": ["arquitetura", "licoes"],
    }

    def __init__(self, project_id: str, agent_id: str):
        self.project_id = project_id
        self.agent_id = agent_id
        self.base = Path("contexts") / project_id / agent_id
        self.tree_dir = self.base / "tree"
        self.index_path = self.base / "INDEX.md"

    # -------- Init --------

    def ensure_initialized(self):
        """Cria estrutura inicial se não existir."""
        self.tree_dir.mkdir(parents=True, exist_ok=True)

        if not self.index_path.exists():
            self.index_path.write_text(
                f"# Context Tree — {self.agent_id} — {self.project_id}\n"
                "\n"
                "## Dominios Disponiveis\n"
                "\n"
                "| Dominio | Descricao | Arquivo |\n"
                "|---------|-----------|---------|\n"
                "| bugs | Bugs conhecidos, correcoes, padroes de erro | tree/bugs.md |\n"
                "| features | Funcionalidades implementadas, decisoes tecnicas | tree/features.md |\n"
                "| arquitetura | Decisoes arquiteturais, padroes de codigo | tree/arquitetura.md |\n"
                "| licoes | Aprendizados consolidados | tree/licoes.md |\n",
                encoding="utf-8",
            )

        default_domains = {
            "bugs.md": "# Bugs — {} — {}\n\n## Conhecidos\n\n(Nenhum registro ainda)\n",
            "features.md": "# Features — {} — {}\n\n## Implementadas\n\n(Nenhum registro ainda)\n",
            "arquitetura.md": "# Arquitetura — {} — {}\n\n## Decisoes\n\n(Nenhum registro ainda)\n",
            "licoes.md": "# Licoes — {} — {}\n\n## Consolidado\n\n(Nenhum registro ainda)\n",
        }
        for fname, template in default_domains.items():
            fpath = self.tree_dir / fname
            if not fpath.exists():
                fpath.write_text(template.format(self.agent_id, self.project_id), encoding="utf-8")

    # -------- Pre-hook: triage --------

    def triage(self, task: dict, llm_hint: Optional[str] = None) -> list[str]:
        """
        Seleciona quais domínios carregar com base na action da task.

        Returns:
            list[str]: conteúdos dos arquivos de domínio relevantes
        """
        self.ensure_initialized()
        action = task.get("action", "")
        domains = self.ACTION_DOMAIN_MAP.get(action, [])

        contents = []
        for dom in domains:
            fpath = self.tree_dir / f"{dom}.md"
            if fpath.exists():
                contents.append(f"--- {dom} ---\n{fpath.read_text(encoding='utf-8')}")

        # Se LLM hint foi fornecido, também carrega
        if llm_hint:
            for dom_name in re.findall(r'\b(bugs|features|arquitetura|licoes)\b', llm_hint.lower()):
                fpath = self.tree_dir / f"{dom_name}.md"
                if fpath.exists() and dom_name not in domains:
                    contents.append(f"--- {dom_name} ---\n{fpath.read_text(encoding='utf-8')}")
                    domains.append(dom_name)

        return contents

    # -------- Post-hook: persist learning --------

    def persist_learning(self, task: dict, output: TaskOutput, rationale: str = ""):
        """
        Avalia o resultado da task e persiste aprendizado se relevante.

        Returns:
            str | None: domínio onde foi persistido, ou None
        """
        if not output or output.status in ("failure", "rejected"):
            return None

        action = task.get("action", "")
        text = rationale or output.rationale or ""

        # Determinar domínio com base no conteúdo
        domain = self._classify_learning(action, text)
        if not domain:
            return None

        # Extrair título
        title = task.get("title", task.get("task_id", action))

        # Persistir
        entry = self._format_entry(title, action, text)
        fpath = self.tree_dir / f"{domain}.md"
        if fpath.exists():
            current = fpath.read_text(encoding="utf-8")
            marker = "## Conhecidos" if domain == "bugs" else \
                     "## Implementadas" if domain == "features" else \
                     "## Decisoes" if domain == "arquitetura" else \
                     "## Consolidado"
            if marker in current:
                # Inserir após o marcador
                head, sep, tail = current.partition(marker)
                updated = head + marker + "\n" + entry + tail
            else:
                updated = current + "\n" + entry
            fpath.write_text(updated, encoding="utf-8")
            return domain

        return None

    def _classify_learning(self, action: str, text: str) -> Optional[str]:
        """Classifica aprendizado em um domínio."""
        if not text:
            return None

        text_lower = text.lower()
        # Bugs
        if any(w in text_lower for w in ["bug", "fix", "corrig", "error", "fail", "crash",
                                          "scroll", "overflow", "broken", "issue"]):
            return "bugs"
        # Features
        if any(w in text_lower for w in ["feature", "implement", "adicion", "criac",
                                           "criado", "new", "add"]):
            return "features"
        # Arquitetura
        if any(w in text_lower for w in ["arquitetur", "padrao", "pattern", "design",
                                           "decisao", "decid"]):
            return "arquitetura"
        # Lições (fallback para ações de revisão)
        if action in ("review_code", "analyze_project", "suggest_fixes"):
            return "licoes"
        # Se for refactor_code com texto substancial, guardar em features
        if action == "refactor_code" and len(text) > 200:
            return "features"

        return None

    def _format_entry(self, title: str, action: str, text: str) -> str:
        """Formata entrada para o domínio."""
        # Extrair primeira frase ou linha relevante
        summary = text.strip().split("\n")[0][:120] if text else title
        return (
            f"\n### {title}\n"
            f"- **Acao**: {action}\n"
            f"- **Resumo**: {summary}\n"
        )

    # -------- Stats --------

    def stats(self) -> dict:
        """Retorna métricas da árvore de contexto."""
        self.ensure_initialized()
        total_bytes = 0
        domains = {}
        for fpath in sorted(self.tree_dir.glob("*.md")):
            sz = fpath.stat().st_size
            total_bytes += sz
            domains[fpath.stem] = sz

        index_size = self.index_path.stat().st_size if self.index_path.exists() else 0
        return {
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "index_bytes": index_size,
            "total_bytes": total_bytes,
            "domains": domains,
            "domain_count": len(domains),
        }


# -------- Hooks --------

def hook_context_triage(ctx: HookContext):
    """
    PRE_ACTION hook: carrega contexto relevante da árvore.
    Registrado automaticamente no StandardBaseAgent.
    """
    agent = ctx.agent
    tree = ContextTree(agent.project_id, agent.agent_id)
    ctx_parts = tree.triage(ctx.task)

    if ctx_parts:
        # Anexar ao task original para o agente usar
        context_key = "_context_tree_domains"
        existing = ctx.task.get(context_key, [])
        ctx.task[context_key] = existing + ctx_parts


def hook_persist_learning(ctx: HookContext):
    """
    POST_ACTION hook: persiste aprendizado após execução bem-sucedida.
    """
    if not ctx.output or not ctx.output.rationale:
        return

    agent = ctx.agent
    tree = ContextTree(agent.project_id, agent.agent_id)
    domain = tree.persist_learning(ctx.task, ctx.output, ctx.output.rationale)

    # Emitir evento de aprendizado
    if domain:
        from src.protocols.schema import AgentStatus
        agent.emit(AgentStatus.COMPLETED, f"Learning persisted: {domain}", ctx.task)
