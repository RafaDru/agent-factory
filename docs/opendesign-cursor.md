# OpenDesign no Cursor — AFP

## Por que nao aparece como plugin?

O README upstream menciona `/add-plugin opendesign` e busca no marketplace, mas **isso ainda nao esta disponivel de forma confiavel no Cursor** (diferente de Claude Code/Codex).

**Solucao adotada no AFP:** skills OpenDesign instaladas como **Cursor Agent Skills** no projeto.

## Onde esta instalado

```
.cursor/skills/
├── opendesign/              ← entry point (leia primeiro)
├── setup-opendesign/
├── run-opendesign/
├── create-design-system/
├── frontend-design/
├── wireframe/
├── interactive-prototype/
├── make-a-deck/
├── make-tweakable/
└── handoff-to-claude-code/
```

Outputs de design continuam em `./opendesign/` (viewer, mockups, manifest).

## Como usar no Cursor Agent

Exemplos de prompt:

```
Siga a skill opendesign. Wireframe 3 opcoes para a tela Mission Control do Console React.
```

```
Siga opendesign + frontend-design. Refinar marca Hive Lattice para favicon 16px.
```

```
Siga opendesign + create-design-system. Extrair tokens do dashboard-react para afp-hive-lattice.
```

```
Siga opendesign + handoff-to-claude-code. Entregar mockup aprovado para implementacao no React.
```

O agente deve **ler** `.cursor/skills/opendesign/SKILL.md` no inicio da tarefa.

## Preview local

```powershell
cd opendesign
python -m http.server 8289
# Abrir http://localhost:8289/opendesign/
```

## Atualizar skills

```powershell
cd C:\Users\rafae\agent-factory
git clone --depth 1 https://github.com/manalkaff/opendesign.git .tmp-opendesign
Copy-Item .tmp-opendesign\skills\* .cursor\skills\ -Recurse -Force
Remove-Item .tmp-opendesign -Recurse -Force
```

## OpenCode (ja configurado)

Plugin em `.opencode/opencode.json` — use `opencode run` no terminal quando preferir o runtime OpenCode.

## Referencias

- Repo: https://github.com/manalkaff/opendesign
- Regra Cursor: `.cursor/rules/opendesign.mdc`
- Designer AFP: `contexts/afp-team/designer/CONTEXTO.md`
