"""
Agent Orchestrator — Windows Notifications
============================================
Notificações nativas do Windows via toast notifications.
"""

import os
import sys
import json
from typing import Optional
from pathlib import Path


def send_windows_notification(
    title: str,
    message: str,
    duration: str = "short",
) -> bool:
    """
    Envia notificação toast no Windows.
    
    Usa PowerShell para criar notificação nativa.
    
    Args:
        title: Título da notificação
        message: Corpo da mensagem
        duration: 'short' (5s) ou 'long' (25s)
    
    Returns:
        True se enviou com sucesso
    """
    if sys.platform != "win32":
        print(f"[NOTIFICATION] {title}: {message}")
        return False
    
    # Criar script PowerShell temporário
    ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast duration="{duration}">
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Agent Orchestrator").Show($toast)
'''
    
    try:
        # Salvar script temporário
        temp_script = Path(os.environ.get("TEMP", ".")) / "agent_notification.ps1"
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(ps_script)
        
        # Executar PowerShell
        os.system(f'powershell -ExecutionPolicy Bypass -File "{temp_script}"')
        
        # Limpar
        temp_script.unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")
        return False


def send_completion_notification(
    project_id: str,
    total_tasks: int,
    completed: int,
    failed: int,
    duration_seconds: float,
):
    """Envia notificação de conclusão de execução."""
    if failed > 0:
        title = f"⚠️ {project_id} — Concluído com falhas"
        message = f"{completed}/{total_tasks} tarefas concluídas, {failed} falharam. Tempo: {duration_seconds:.1f}s"
    else:
        title = f"✅ {project_id} — Todas as tarefas concluídas!"
        message = f"{completed}/{total_tasks} tarefas executadas com sucesso. Tempo: {duration_seconds:.1f}s"
    
    send_windows_notification(title, message, duration="long")


def send_error_notification(project_id: str, error: str):
    """Envia notificação de erro."""
    title = f"❌ {project_id} — Erro na execução"
    message = error[:200]  # Limitar tamanho
    send_windows_notification(title, message, duration="long")
