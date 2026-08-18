# Guia de Inicializacao (LEGADO)

> **Este documento esta desatualizado.** Use o guia canonico:
> **[docs/QUICKSTART.md](QUICKSTART.md)**

---

Historico: escrito em jun/2026 para subir apenas `start_dashboard.py` com projeto PTA.
A stack atual usa `start_afp.ps1` (dashboard + MCP + runtimes) e projeto padrao
`demo-onboarding`.

## Substitutos

| Antigo | Atual |
|--------|-------|
| `start python start_dashboard.py` | `.\start_afp.ps1 -Restart` |
| `?project=pta` | `demo-onboarding` ou seu projeto local |
| Dashboard sozinho | Stack completa + healthcheck |

Ver [QUICKSTART.md](QUICKSTART.md) para o fluxo completo.
