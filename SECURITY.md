# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 3.x (beta) | yes |
| < 3.0 | no |

## Reporting a Vulnerability

**Nao abra issues publicas para vulnerabilidades de seguranca.**

Envie um relatorio privado para o mantenedor do repositorio via GitHub
[Security Advisories](https://github.com/RafaDru/agent-factory/security/advisories/new)
ou contato direto com o owner do repo.

Inclua:

- Descricao do problema
- Passos para reproduzir
- Impacto estimado
- Sugestao de correcao (se houver)

Expectativa de resposta: ate 7 dias uteis para confirmacao inicial.

## Escopo

Este projeto executa codigo localmente, roteia prompts para LLMs externos e
expoe MCP/HTTP em `localhost` por padrao.

Boas praticas ao usar:

- Nunca commitar `.env` ou API keys
- Nao exponha `:8080` / `:8081` na internet sem autenticacao
- Revise `CONTEXTO.md` e acoes de agentes antes de delegar em repositorios sensiveis
- RabbitMQ default (`afp`/`afp123`) e apenas para dev local — altere em producao
