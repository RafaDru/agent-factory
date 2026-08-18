# Contextos de projeto

Esta pasta registra **projetos que a AFP orquestra**. A plataforma escaneia
`contexts/*/project.json` na inicializacao (auto-discovery).

## O que vem no repositorio publico

| Pasta | Proposito |
|-------|-----------|
| `_template/` | Template vazio para copiar/scaffold |
| `demo-onboarding/` | Exemplo minimo (coordenador + dev) para validar setup |

**Projetos reais de negocio nao devem ser commitados aqui.** Use scaffold local.

## Registrar seu projeto

```powershell
.\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto"
```

Edite `contexts/meu-projeto/project.json` e os `CONTEXTO.md` dos agentes.
Reinicie a stack (`.\start_afp.ps1 -Restart`) ou aguarde auto-discovery.

## Git

Por padrao, apenas `_template/`, `demo-onboarding/` e este README sao versionados.
Contextos criados localmente ficam fora do Git (veja `.gitignore`).

Ver tambem: [docs/playbook-onboarding.md](../docs/playbook-onboarding.md)
