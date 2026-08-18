# Copilot — Agent Factory Platform

Este repositorio e a **plataforma AFP** (orquestrador de agentes), nao um app de negocio.

Antes de mudar codigo de runtime/MCP:

1. Leia `docs/AI_ONBOARDING.md` e `AGENTS.md`
2. Projeto versionado padrao: `contexts/demo-onboarding/` (`project_id=demo-onboarding`)
3. Nao commitar projetos em `contexts/` exceto `_template/` e `demo-onboarding/`
4. Testes: `python -m pytest tests/ -q`
5. Stack Windows: `.\start_afp.ps1 -Restart` (nao bloquear terminal em foreground)
6. Copilot nao usa MCP — validar com `.\scripts\first-mission.ps1`

Docs em portugues; commits em portugues quando o repo ja usa esse padrao.
