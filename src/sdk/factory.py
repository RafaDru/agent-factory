"""Fabrica Declarativa de Agentes — YAML/JSON -> StandardBaseAgent."""

import importlib
import json
import traceback
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.sdk.base import StandardBaseAgent
from src.protocols.schema import AgentRole, TaskOutput, OutputStatus
from src.protocols.events import EventNotifier
from src.sdk.hooks import HookRegistry, HookPoint, HookContext
from src.llm import get_provider, LLMProvider


class ActionDef(BaseModel):
    """Definicao declarativa de uma acao de agente."""
    description: str = ""
    params: dict[str, str] = Field(default_factory=dict)
    handler: Optional[str] = None       # "modulo.funcao" — Python callable
    llm_prompt: Optional[str] = None    # usado se handler for None (LLM decide)


class AgentDef(BaseModel):
    """Definicao declarativa de um agente."""
    id: str
    role: AgentRole = AgentRole.WORKER
    description: str = ""
    prompt: str = ""                     # injetado como contexto/skill
    actions: dict[str, ActionDef] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    llm_provider: Optional[str] = None   # "groq", "ollama", etc.


class AgentFactory:
    """
    Fabrica que constroi agentes a partir de definicoes declarativas.
    
    Uso:
        config = AgentFactory.parse_yaml("agentes/meu_agente.yaml")
        agente = AgentFactory.build(config, project_id="...", notifier=...)
        agente.run({"action": "minha_acao", "input": "..."})
    """

    @staticmethod
    def parse_yaml(path: str) -> AgentDef:
        """Le arquivo YAML e retorna AgentDef."""
        import yaml
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return AgentDef(**data)

    @staticmethod
    def parse_json(path: str) -> AgentDef:
        """Le arquivo JSON e retorna AgentDef."""
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
        return AgentDef(**data)

    @staticmethod
    def parse_dict(data: dict) -> AgentDef:
        """Converte dict para AgentDef."""
        return AgentDef(**data)

    @staticmethod
    def build(
        config: AgentDef,
        project_id: str,
        notifier: EventNotifier,
        **kwargs,
    ) -> StandardBaseAgent:
        """
        Constroi agente a partir da configuracao declarativa.
        Registra automaticamente as acoes como metodos do agente.
        """
        # Resolver provider LLM se configurado
        llm_provider: Optional[LLMProvider] = None
        provider_name = config.llm_provider or "auto"
        try:
            llm_provider = get_provider(provider_name)
        except Exception as e:
            print(f"  [Factory] ?? LLM provider '{provider_name}' falhou: {e}")

        # Validar handlers antes de criar a classe
        resolved_handlers: dict[str, Any] = {}
        for action_name, action_def in config.actions.items():
            if action_def.handler:
                resolved_handlers[action_name] = _resolve_handler(action_def.handler)
            else:
                resolved_handlers[action_name] = None  # LLM-based

        # Factory method que cria a classe
        class _DeclarativeAgent(StandardBaseAgent):
            ACTIONS = {
                name: {"description": act.description, "params": act.params}
                for name, act in config.actions.items()
            }

            def __init__(self, *args, **outer_kwargs):
                super().__init__(*args, **outer_kwargs)
                self._agent_def = config
                self._prompt = config.prompt
                self._llm_provider = llm_provider

            def execute(self, task: dict[str, Any]) -> TaskOutput:
                action = task.get("action", "")
                handler_fn = resolved_handlers.get(action)
                if handler_fn is None:
                    return AgentFactory._llm_fallback(task, self, config)
                try:
                    result = handler_fn(self, task)
                    if isinstance(result, TaskOutput):
                        return result
                    if isinstance(result, dict):
                        return TaskOutput.from_execute_output(result)
                    return TaskOutput.success(summary=str(result))
                except Exception as e:
                    return TaskOutput.failure(rationale=str(e))

        instance = _DeclarativeAgent(
            agent_id=config.id,
            project_id=project_id,
            notifier=notifier,
            role=config.role,
            **kwargs,
        )

        # Registrar skills como hooks (TODO: carregar skills externos)
        if config.skills:
            for skill_name in config.skills:
                AgentFactory._inject_skill(instance, skill_name, config)

        return instance

    @staticmethod
    def _llm_fallback(task: dict, agent: StandardBaseAgent, config: AgentDef) -> TaskOutput:
        """Quando o action nao tem handler Python, usa LLM com tool-calling para executar."""
        import json, logging
        logger = logging.getLogger(__name__)
        action = task.get("action", "")
        action_def = config.actions.get(action)

        if not action_def:
            return TaskOutput.needs_direction(
                rationale=f"Acao '{action}' nao definida no agente '{config.id}'",
                available_actions=list(config.actions.keys()),
            )

        provider: Optional[LLMProvider] = getattr(agent, '_llm_provider', None) or getattr(agent, '_llm', None)
        if provider is None or not provider.is_available():
            return TaskOutput.failure(
                rationale=f"Acao '{action}' sem handler Python e LLM provider "
                           f"'{config.llm_provider}' indisponivel. "
                           "Defina handler Python ou configure llm_provider valido.",
                available_actions=list(config.actions.keys()),
            )

        task_params = {k: v for k, v in task.items() if k not in ('action', 'task_id', 'title')}
        tools = AgentFactory._build_tools_schema(config)

        prompt = f"""Voce e o agente '{config.id}' — {config.description or 'sem descricao'}.

## Instrucao do sistema
{config.prompt or 'Nenhuma instrucao especifica.'}

## Acao solicitada
{action_def.description or action}

## Dados recebidos
{json.dumps(task_params, ensure_ascii=False, indent=2) if task_params else '(nenhum)'}

## Instrucoes
1. Analise a acao solicitada e os dados recebidos.
2. Use as ferramentas disponiveis para executar a acao (ex: read_file, write_file, edit_file).
3. Leia arquivos antes de modifica-los para entender o contexto.
4. Ao final, responda com um resumo do que foi feito.
"""

        messages = [{"role": "user", "content": prompt}]
        max_iterations = 15
        step_count = 0
        final_content = ""
        all_tool_results = []
        last_resp = None

        try:
            while step_count < max_iterations:
                step_count += 1
                kwargs = {}
                if tools:
                    kwargs["tools"] = tools

                resp = provider.chat(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4096,
                    **kwargs,
                )
                last_resp = resp

                if resp.tool_calls:
                    for tc in resp.tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            fn_args = {}

                        tool_task = {"action": fn_name, **fn_args}
                        logger.info("LLM tool call: %s args=%s", fn_name, fn_args)

                        try:
                            tool_result = agent.execute(tool_task)
                            if isinstance(tool_result, TaskOutput):
                                result_data = tool_result.summary or tool_result.rationale or str(tool_result.details)
                            else:
                                result_data = str(tool_result)
                        except Exception as e:
                            result_data = f"Erro: {e}"

                        all_tool_results.append({"tool": fn_name, "args": fn_args, "result": str(result_data)[:500]})

                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tc.get("id", f"call_{step_count}"),
                                "type": "function",
                                "function": {"name": fn_name, "arguments": tc["function"]["arguments"]},
                            }],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", f"call_{step_count}"),
                            "content": str(result_data)[:2000],
                        })
                else:
                    final_content = resp.content
                    break

            if final_content and last_resp:
                return TaskOutput.success(
                    summary=f"LLM ({config.llm_provider}): {final_content[:200].strip()}...",
                    rationale=final_content,
                    details={"steps": step_count, "tool_calls": len(all_tool_results), "results": all_tool_results},
                    raw_response=final_content,
                    model=last_resp.model,
                    usage=last_resp.usage,
                )
            return TaskOutput.failure(
                rationale=f"LLM nao produziu resposta final apos {step_count} iteracoes",
                details={"tool_calls": all_tool_results},
            )
        except Exception as e:
            logger.exception("LLM tool-calling falhou")
            return TaskOutput.failure(
                rationale=f"LLM fallback falhou: {e}",
                available_actions=list(config.actions.keys()),
                details={"tool_calls": all_tool_results} if all_tool_results else None,
            )

    @staticmethod
    def _build_tools_schema(config: AgentDef) -> list[dict]:
        """Converte acoes do agente em schema OpenAI function-calling."""
        import json
        tools = []
        _type_map = {"str": "string", "int": "integer", "float": "number", "bool": "boolean", "list": "array", "dict": "object"}

        for name, act in config.actions.items():
            if not act.handler:
                continue
            properties = {}
            required = []
            for pname, pdesc in (act.params or {}).items():
                pdesc_lower = pdesc.lower()
                is_required = "obrigatorio" in pdesc_lower or "required" in pdesc_lower
                ptype = "string"
                for kw, js_type in _type_map.items():
                    if kw in pdesc_lower:
                        ptype = js_type
                        break
                properties[pname] = {"type": ptype, "description": pdesc}
                if is_required:
                    required.append(pname)

            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": act.description or name,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return tools

    @staticmethod
    def _inject_skill(agent: StandardBaseAgent, skill_name: str, config: AgentDef):
        """Injeta uma skill no agente como hooks + actions (TODO)."""
        pass  # Placeholder para integracao futura de skills


def _resolve_handler(handler_path: str) -> Any:
    """
    Resolve "modulo.funcao" para a funcao Python correspondente.
    A funcao recebe (self, task: dict) -> TaskOutput | dict.
    """
    parts = handler_path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Handler deve ser 'modulo.funcao': {handler_path}")

    module_path = ".".join(parts[:-1])
    func_name = parts[-1]

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ValueError(f"Modulo nao encontrado: {module_path} (handler: {handler_path})")

    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        raise ValueError(f"Funcao '{func_name}' nao encontrada ou nao callable em {module_path}")

    return func
