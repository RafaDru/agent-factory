# Template de Projeto AFP

Copie esta pasta para `contexts/{seu-projeto}/` e substitua os placeholders.

## Uso rapido (PowerShell)

```powershell
.\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto" -Description "Descricao curta"
```

## Estrutura

```
contexts/{proj}/
├── project.json          # Registro do projeto (agentes, working_dir)
├── coordenador/
│   ├── CONTEXTO.md       # Papel e regras do coordenador
│   ├── INDEX.md          # Indice da arvore de contexto
│   └── tree/             # Aprendizado persistente por dominio
└── dev/                  # Exemplo de worker (renomeie/adicione agentes)
    ├── CONTEXTO.md
    ├── INDEX.md
    └── tree/
```

## Apos copiar

1. Ajuste `project.json` (agentes, `working_dir`, LLM providers)
2. Edite `coordenador/CONTEXTO.md` com objetivos do projeto
3. Registre via MCP `register_project` ou reinicie o dashboard (auto-discovery)
4. Primeira missao: `run_objective(project_id, "Descreva o objetivo inicial")`

Ver tambem: [docs/playbook-onboarding.md](../../docs/playbook-onboarding.md)
