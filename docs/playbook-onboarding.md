# Playbook de Onboarding de Projeto no AFP

Siga os passos abaixo para registrar um novo projeto no Agent Factory Platform.

1. **Registrar o projeto**  
   Utilize o comando `register_project` (via MCP ou interface do coordenador) informando o nome e descrição do projeto.

2. **Criar estrutura de contexto**  
   Copie `contexts/_template/` para `contexts/{proj}/` ou use:
   ```powershell
   .\scripts\scaffold_project.ps1 -ProjectId "meu-projeto" -ProjectName "Meu Projeto"
   ```

3. **Criar `project.json`**  
   Dentro de `contexts/{proj}/`, crie o arquivo `project.json` com metadados do projeto: nome, descrição, objetivos, stakeholders, etc.

4. **Criar `CONTEXTO.md`**  
   Ainda em `contexts/{proj}/`, crie o arquivo `CONTEXTO.md` com o contexto inicial: backlog resumido, requisitos principais, restrições e referências.

5. **Iniciar a primeira missão**  
   Via MCP, envie uma missão ao coordenador (ex.: "Planejar e executar a primeira tarefa do backlog") para dar início ao ciclo de desenvolvimento.