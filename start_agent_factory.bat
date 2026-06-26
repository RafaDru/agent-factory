@echo off
REM ============================================
REM Agent Factory - Inicialização com Windows
REM ============================================
REM Este script inicia o Agent Factory automaticamente
REM quando o Windows é iniciado.
REM
REM Para instalar:
REM 1. Copie este arquivo para a pasta de inicialização do Windows
REM    (geralmente: C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup)
REM 2. Reinicie o Windows
REM
REM Para remover:
REM 1. Delete este arquivo da pasta de inicialização
REM ============================================

REM Configurar diretório
cd /d C:\Users\rafae\agent-factory

REM Iniciar dashboard em background
start /B python start_dashboard.py

REM Aguardar 5 segundos para o dashboard iniciar
timeout /t 5 /nobreak >nul

REM Verificar se o dashboard está rodando
python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8080', timeout=2)
    print('Agent Factory Dashboard iniciado com sucesso!')
    print('URL: http://localhost:8080?project=pta')
except Exception as e:
    print(f'Erro ao iniciar dashboard: {e}')
"

REM Manter janela aberta
pause
