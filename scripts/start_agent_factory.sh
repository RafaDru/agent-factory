#!/usr/bin/env bash
#
# Agent Factory — Linux Startup
# Inicia Ollama (GPU otimizado) + Dashboard.
#
# Uso:
#   ./scripts/start_agent_factory.sh                  # normal
#   ./scripts/start_agent_factory.sh --demo           # + demo agents
#   ./scripts/start_agent_factory.sh --no-ollama      # não gerencia Ollama
#   ./scripts/start_agent_factory.sh --port 9090      # porta customizada
#

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8080
DEMO=false
NO_OLLAMA=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        --demo) DEMO=true; shift ;;
        --no-ollama) NO_OLLAMA=true; shift ;;
        *) echo "Opção desconhecida: $1"; exit 1 ;;
    esac
done

echo ""
echo "    +----------------------------------------------+"
echo "    |        Agent Factory -- v2.0.0-beta           |"
echo "    |              Linux Startup                    |"
echo "    +----------------------------------------------+"
echo ""

# ─── Step 1: Ollama ────────────────────────────────────────────────────
if [ "$NO_OLLAMA" = false ]; then
    echo "[1/3] Configurando Ollama..."

    export OLLAMA_FLASH_ATTENTION=1
    export OLLAMA_KV_CACHE_TYPE=q8_0
    export OLLAMA_NUM_PARALLEL=2
    export OLLAMA_MAX_LOADED_MODELS=3
    export OLLAMA_SCHED_SPREAD=1
    export OLLAMA_KEEP_ALIVE=15m

    echo "  OLLAMA_FLASH_ATTENTION   = $OLLAMA_FLASH_ATTENTION"
    echo "  OLLAMA_KV_CACHE_TYPE     = $OLLAMA_KV_CACHE_TYPE"
    echo "  OLLAMA_NUM_PARALLEL      = $OLLAMA_NUM_PARALLEL"
    echo "  OLLAMA_MAX_LOADED_MODELS = $OLLAMA_MAX_LOADED_MODELS"
    echo "  OLLAMA_KEEP_ALIVE        = $OLLAMA_KEEP_ALIVE"

    # Check if ollama is running
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✅ Ollama já está rodando"
    else
        echo "  🚀 Iniciando Ollama..."
        if ! command -v ollama &> /dev/null; then
            echo "  ❌ Ollama não encontrado. Instale: https://ollama.com"
            exit 1
        fi
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!
        sleep 3
        echo "  ✅ Ollama rodando (PID $OLLAMA_PID)"
    fi

    # List models
    echo ""
    echo "[2/3] Modelos disponíveis:"
    if curl -sf http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if models:
    for m in sorted(models, key=lambda x: -x['size']):
        size = m['size'] / (1024**3)
        print(f'  • {m[\"name\"]:<25s} ({size:.1f} GB)')
else:
    print('  ⚠️  Nenhum modelo instalado')
    print('     Execute: ollama pull gemma3:4b')
    print('     Execute: ollama pull qwen2.5-coder:7b')
" 2>/dev/null; then
        :
    else
        echo "  ⚠️  Não foi possível listar modelos"
    fi
else
    echo "[1/3] ⏭️  Ollama: gerenciamento desabilitado (--no-ollama)"
    echo "[2/3] ⏭️  Modelos: pulado"
fi

# ─── Step 2: Dashboard ─────────────────────────────────────────────────
echo ""
echo "[3/3] Iniciando Dashboard..."

ARGS="--port $PORT --no-ollama"
if [ "$DEMO" = true ]; then
    ARGS="$ARGS --demo"
fi

echo "  http://localhost:$PORT/?project=agent-factory-dev"
echo "  Pressione Ctrl+C para encerrar"
echo ""

cd "$ROOT_DIR"
exec python3 start_agent_factory.py $ARGS
