"""
Agent Factory — Real Agents
============================
Agentes que executam código real via subprocess.
"""

import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path
from typing import Any, Optional
from ..agents.base import AgentBase, AgentRole
from ..protocols.events import EventNotifier
from ..protocols.schema import AgentStatus


class SubprocessAgent(AgentBase):
    """
    Agente que executa código Python via subprocess.
    
    Uso:
        agent = SubprocessAgent(
            agent_id="executor",
            project_id="my-project",
            notifier=notifier,
        )
        
        result = agent.run({
            "task_id": "task-1",
            "code": "print('Olá mundo')",
        })
    """
    
    def __init__(
        self,
        agent_id: str,
        project_id: str,
        notifier: EventNotifier,
        role: AgentRole = AgentRole.WORKER,
        timeout: int = 300,
        working_dir: Optional[str] = None,
    ):
        super().__init__(agent_id, project_id, notifier, role)
        self.timeout = timeout
        self.working_dir = working_dir or os.getcwd()
    
    def validate_input(self, task: dict[str, Any]) -> bool:
        """Valida se a tarefa tem código para executar."""
        return "code" in task or "script" in task
    
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Executa código Python via subprocess."""
        if "code" in task:
            return self._execute_code(task["code"], task.get("args", {}))
        elif "script" in task:
            return self._execute_script(task["script"], task.get("args", {}))
        else:
            raise ValueError("Tarefa deve conter 'code' ou 'script'")
    
    def _execute_code(self, code: str, args: dict[str, Any]) -> dict[str, Any]:
        """Executa código Python em um subprocess."""
        # Criar script temporário
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as f:
            # Adicionar argumentos como variáveis globais
            if args:
                f.write("import json\n")
                f.write(f"args = json.loads('{json.dumps(args)}')\n\n")
            
            f.write(code)
            temp_path = f.name
        
        try:
            # Executar subprocess
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_dir,
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Timeout após {self.timeout} segundos",
                "returncode": -1,
                "success": False,
                "timeout": True,
            }
        
        finally:
            # Limpar arquivo temporário
            os.unlink(temp_path)
    
    def _execute_script(self, script_path: str, args: dict[str, Any]) -> dict[str, Any]:
        """Executa um script Python existente."""
        script = Path(script_path)
        
        if not script.exists():
            return {
                "stdout": "",
                "stderr": f"Script não encontrado: {script_path}",
                "returncode": -1,
                "success": False,
            }
        
        # Construir comando
        cmd = [sys.executable, str(script)]
        
        # Adicionar argumentos
        for key, value in args.items():
            cmd.extend([f"--{key}", str(value)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_dir,
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
                "script": str(script),
            }
        
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Timeout após {self.timeout} segundos",
                "returncode": -1,
                "success": False,
                "timeout": True,
            }


class LLMAgent(AgentBase):
    """
    Agente que usa LLM para tomar decisões.
    
    Uso:
        from agent_factory.llm import get_provider
        
        agent = LLMAgent(
            agent_id="analyst",
            project_id="my-project",
            notifier=notifier,
            provider=get_provider("groq"),
            system_prompt="Você é um analista de dados.",
        )
        
        result = agent.run({
            "task_id": "task-1",
            "prompt": "Analise estes dados: ...",
        })
    """
    
    def __init__(
        self,
        agent_id: str,
        project_id: str,
        notifier: EventNotifier,
        provider: Any,
        system_prompt: str = "Você é um assistente útil.",
        role: AgentRole = AgentRole.WORKER,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        super().__init__(agent_id, project_id, notifier, role)
        self.provider = provider
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def validate_input(self, task: dict[str, Any]) -> bool:
        """Valida se a tarefa tem um prompt."""
        return "prompt" in task
    
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Executa o LLM com o prompt fornecido."""
        prompt = task["prompt"]
        context = task.get("context", {})
        
        # Construir mensagens
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Adicionar contexto se disponível
        if context:
            context_str = json.dumps(context, default=str, ensure_ascii=False)
            messages.append({
                "role": "system",
                "content": f"Contexto anterior:\n{context_str}"
            })
        
        messages.append({"role": "user", "content": prompt})
        
        # Chamar LLM
        response = self.provider.chat(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        return {
            "response": response.content,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason,
        }
