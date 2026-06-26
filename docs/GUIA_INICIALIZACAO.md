# Agent Factory - Guia de Inicialização Rápida

**Última atualização**: 24/06/2026

---

## Problema Identificado

O Agent Factory dashboard não inicia de forma persistente. O processo é encerrado quando a sessão PowerShell/terminal é fechada.

---

## Solução: Inicialização Correta

### Método 1: Usando `start` (Recomendado)

```powershell
cd C:\Users\rafae\agent-factory
start python start_dashboard.py
```

**Por que funciona**: O comando `start` cria um novo processo separado que continua rodando após o terminal ser fechado.

### Método 2: Usando Background Job

```powershell
cd C:\Users\rafae\agent-factory
Start-Process -FilePath "python" -ArgumentList "start_dashboard.py" -WindowStyle Hidden
```

### Método 3: Usando Task Scheduler (Automático)

```powershell
# Executar como administrador
cd C:\Users\rafae\agent-factory
.\install_startup.ps1
```

---

## Verificação

### 1. Verificar se o dashboard está rodando

```powershell
python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8080', timeout=2)
    print('Dashboard: RODANDO')
    print(f'Status: {response.status}')
except Exception as e:
    print(f'Dashboard: NÃO RODANDO - {e}')
"
```

### 2. Acessar o dashboard

- **URL**: http://localhost:8080?project=pta
- **Projeto**: PTA (Personal Trainer Agent)

---

## Comandos Úteis

### Iniciar Dashboard
```powershell
cd C:\Users\rafae\agent-factory
start python start_dashboard.py
```

### Verificar Status
```powershell
python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8080', timeout=2); print('RODANDO' if r.status==200 else 'ERRO')"
```

### Parar Dashboard
```powershell
# Encontrar e matar o processo
Get-Process python | Where-Object {$_.CommandLine -like "*start_dashboard*"} | Stop-Process
```

---

## Solução de Problemas

### Dashboard não inicia
1. Verificar se a porta 8080 está livre
2. Verificar se o Python está configurado
3. Executar manualmente para ver erros

### Dashboard inicia mas não responde
1. Verificar firewall
2. Verificar se o notificador está funcionando
3. Verificar logs no terminal

### Dashboard some após algum tempo
1. Usar `start` em vez de executar direto
2. Configurar Task Scheduler para iniciar automaticamente

---

## Arquivos Importantes

- `start_dashboard.py` - Script principal de inicialização
- `install_startup.ps1` - Configuração de inicialização automática
- `start_agent_factory.bat` - Script alternativo para Windows

---

## Correlação com GitHub Projects

### Labels para Event Log
- **title**: Título da tarefa
- **observation**: Observação adicional
- **description**: Descrição detalhada
- **github_issue**: Número da issue (ex: PTA-123)

### Exemplo de Uso
```python
task = {
    'task_id': 'melhoria-identificacao-v1',
    'title': 'Classificar Landmarks por Tipo',
    'observation': 'Adicionar constantes e cores',
    'description': 'Implementar JOINT_LANDMARKS no WebView',
    'github_issue': 'PTA-123',
    'payload': {...}
}
```

---

## Checklist de Inicialização

- [ ] Verificar se Python está instalado
- [ ] Verificar se porta 8080 está livre
- [ ] Executar `start python start_dashboard.py`
- [ ] Verificar se dashboard responde em http://localhost:8080
- [ ] Acessar dashboard e verificar projeto PTA
