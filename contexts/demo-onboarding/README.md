# Demo Onboarding

Exemplo minimo versionado no repo publico: **coordenador + dev**.

## Objetivo

Validar que a AFP esta operacional apos clone — auto-discovery, RPC e primeira missao.

## Subir stack

```powershell
docker compose up -d rabbitmq
.\start_afp.ps1 -Restart
.\start_afp.ps1 -HealthCheck
```

## Primeira missao (automated smoke)

```powershell
python run_smoke_e012.py
```

Esperado: `SMOKE_OK` — coordenador delega `read_file` em `docs/backlog.md`.

## Primeira missao (MCP manual)

No Cursor ou OpenCode, configure MCP `http://127.0.0.1:8081/sse` e execute:

```
run_objective(
  project_id="demo-onboarding",
  objective="Ler docs/QUICKSTART.md e resumir os 5 passos principais",
  context="Plano minimo: 1 step, agent dev, action read_file"
)
```

## Estrutura

```
demo-onboarding/
├── project.json       # working_dir: "." (raiz do repo AFP)
├── coordenador/       # regras de orquestracao
└── dev/               # worker declarativo
```

## Proximo passo

Copie o template para seu projeto real (nao commitado):

```powershell
.\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto"
```

Ver [docs/playbook-onboarding.md](../../docs/playbook-onboarding.md).
