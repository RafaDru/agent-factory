# Contributing to Agent Factory Platform

Obrigado pelo interesse em contribuir. Este projeto esta em **beta tecnico** —
feedback, issues e PRs sao bem-vindos.

## Como comecar

1. Fork o repositorio
2. Clone e instale: [docs/QUICKSTART.md](docs/QUICKSTART.md)
3. Crie um branch: `git checkout -b feat/minha-melhoria`
4. Rode os testes: `python -m pytest tests/ -q`
5. Abra um Pull Request

## Escopo do repositorio publico

Este repo contem **apenas a plataforma AFP** (runtime, MCP, dashboard, SDK).

- **Nao commitar** projetos de negocio em `contexts/` (exceto `_template/` e `demo-onboarding/`)
- **Nao commitar** `.env`, `.agent-factory/`, chaves ou dados de runtime
- Agentes de dominio pertencem ao **projeto do usuario**, nao ao Factory

## Padroes de codigo

- Python 3.11+, type hints onde fizer sentido
- Testes em `tests/` para logica de plataforma (RPC, discovery, mission API)
- Docs em `docs/` — prefira atualizar `QUICKSTART.md` para fluxos de usuario
- Commits: imperativo, curto (`fix(rpc): ...`, `docs: ...`, `feat(mcp): ...`)

## Rodar testes

```powershell
pip install -e ".[dev]"
python -m pytest tests/ -q
```

CI roda o mesmo suite no push/PR (GitHub Actions).

## Reportar bugs

Use [GitHub Issues](https://github.com/RafaDru/agent-factory/issues) com:

- SO e versao do Python
- Comando executado
- Log relevante (`.agent-factory/logs/`)
- Comportamento esperado vs. observado

## Roadmap

Veja [docs/backlog.md](docs/backlog.md) antes de PRs grandes — epics E-012 a E-015
orientam prioridades atuais.

## Licenca

Ao contribuir, voce concorda que suas contribuicoes serao licenciadas sob MIT.
