# scripts/analisar_impacto.py
"""
Script de Análise de Impacto de Negócio para os pontos P1 a P5.
Avalia cada ponto considerando retenção de usuário, confiabilidade
e eficiência operacional, gerando classificação preliminar e prioridade.
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class PontoAnalise:
    id: str
    titulo: str
    descricao: str
    tipo_problema: str  # "bug" ou "melhoria"
    impacto_retencao: int  # 1-10
    impacto_confiabilidade: int  # 1-10
    impacto_eficiencia: int  # 1-10
    classificacao: str  # "bug", "melhoria", "feature"
    prioridade: str  # "alta", "media", "baixa"
    justificativa: str


def calcular_prioridade(impacto_total: int) -> str:
    """Determina a prioridade baseada no score de impacto total."""
    if impacto_total >= 24:
        return "alta"
    elif impacto_total >= 16:
        return "media"
    return "baixa"


def classificar_ponto(tipo_problema: str, impacto_total: int) -> str:
    """Classifica o ponto como bug, melhoria ou feature."""
    if tipo_problema == "bug":
        return "bug"
    elif tipo_problema == "melhoria" and impacto_total >= 20:
        return "feature"
    return "melhoria"


def analisar_pontos() -> List[PontoAnalise]:
    """Realiza a análise de impacto de negócio para cada ponto."""

    pontos = [
        PontoAnalise(
            id="P1",
            titulo="Interaction Flow com 'idas e vindas'",
            descricao=(
                "O fluxo de interação atual mostra cada task com estado 'running' "
                "(com glow) e depois 'completed/failed'. O problema é que o ícone "
                "continua piscando 'running' mesmo após término, dando falsa sensação "
                "de execução. A melhoria desejada é agrupar por task 'mãe' da conversa "
                "e mostrar apenas o estado atual, funcionando como indicador de operação "
                "em tempo real, não como log histórico."
            ),
            tipo_problema="melhoria",
            impacto_retencao=8,
            impacto_confiabilidade=9,
            impacto_eficiencia=7,
            classificacao="",
            prioridade="",
            justificativa=(
                "Impacto direto na confiança do usuário: indicador falso de execução "
                "mina a credibilidade da plataforma. Usuários podem abandonar tarefas "
                "acreditando que ainda estão em andamento ou, pior, duvidar da "
                "confiabilidade do sistema. Retenção afetada pela experiência confusa. "
                "Eficiência operacional prejudicada pela incapacidade de distinguir "
                "estados reais dos históricos."
            ),
        ),
        PontoAnalise(
            id="P2",
            titulo="Cards de agentes sem atualização ao vivo",
            descricao=(
                "Os cards de agentes acima do interaction flow não refletem em tempo "
                "real o status. O SSE entrega eventos corretamente, mas os cards não "
                "são atualizados, criando desconexão entre o backend e a interface."
            ),
            tipo_problema="bug",
            impacto_retencao=7,
            impacto_confiabilidade=8,
            impacto_eficiencia=6,
            classificacao="",
            prioridade="",
            justificativa=(
                "Bug que afeta a confiabilidade percebida: dados desatualizados nos "
                "cards geram desconfiança sobre o estado real do sistema. Usuários "
                "podem tomar decisões baseadas em informações incorretas. Retenção "
                "impactada pela inconsistência visual. Eficiência reduzida ao exigir "
                "verificação manual em outras áreas da interface."
            ),
        ),
        PontoAnalise(
            id="P3",
            titulo="Lista de modelos limitada",
            descricao=(
                "A interface mostra apenas Groq/Ollama/Opencode como opções de "
                "provedores. Outros providers configurados (OpenAI, Anthropic, etc.) "
                "não aparecem na lista de seleção, limitando as opções do usuário."
            ),
            tipo_problema="melhoria",
            impacto_retencao=6,
            impacto_confiabilidade=4,
            impacto_eficiencia=8,
            classificacao="",
            prioridade="",
            justificativa=(
                "Limitação que afeta a eficiência operacional: usuários avançados "
                "que possuem chaves de outros provedores não conseguem utilizá-los, "
                "reduzindo a flexibilidade da plataforma. Retenção impactada para "
                "usuários que preferem modelos específicos. Confiabilidade menos "
                "afetada pois os provedores existentes funcionam corretamente."
            ),
        ),
        PontoAnalise(
            id="P4",
            titulo="Primeira tela (localhost:8080) sem live stream",
            descricao=(
                "A página de listagem de projetos não mostra status ao vivo dos "
                "agentes. O indicador fica piscando '0 agents running' mesmo quando "
                "há execuções ativas, fornecendo informação incorreta na porta de "
                "entrada da aplicação."
            ),
            tipo_problema="bug",
            impacto_retencao=9,
            impacto_confiabilidade=9,
            impacto_eficiencia=5,
            classificacao="",
            prioridade="",
            justificativa=(
                "Bug crítico na primeira impressão do usuário: a tela inicial é a "
                "porta de entrada e exibir informação incorreta sobre o estado do "
                "sistema causa desconfiança imediata. Alta probabilidade de abandono "
                "na primeira visita. Confiabilidade severamente afetada pois contradiz "
                "a proposta de valor da plataforma (orquestração em tempo real). "
                "Retenção fortemente impactada."
            ),
        ),
        PontoAnalise(
            id="P5",
            titulo="Navegação por URL (/project=xxx)",
            descricao=(
                "Ao recarregar a página (F5/refresh), o navegador retorna para a "
                "primeira tela em vez de manter o projeto selecionado. A navegação "
                "deveria usar query parameters na URL para persistir o estado da "
                "seleção entre recarregamentos."
            ),
            tipo_problema="bug",
            impacto_retencao=7,
            impacto_confiabilidade=6,
            impacto_eficiencia=8,
            classificacao="",
            prioridade="",
            justificativa=(
                "Bug de UX que afeta a eficiência operacional: recarregamentos são "
                "comuns durante o desenvolvimento e depuração. Perder o contexto do "
                "projeto selecionado interrompe o fluxo de trabalho e causa frustração. "
                "Retenção afetada pela experiência interrompida. Confiabilidade "
                "moderadamente impactada pois sugere falta de polimento na aplicação."
            ),
        ),
    ]

    # Calcular classificações e prioridades
    for ponto in pontos:
        impacto_total = (
            ponto.impacto_retencao
            + ponto.impacto_confiabilidade
            + ponto.impacto_eficiencia
        )
        ponto.classificacao = classificar_ponto(ponto.tipo_problema, impacto_total)
        ponto.prioridade = calcular_prioridade(impacto_total)

    return pontos


def gerar_relatorio(pontos: List[PontoAnalise]) -> Dict[str, Any]:
    """Gera o relatório final em formato de dicionário."""
    pontos_ordenados = sorted(
        pontos,
        key=lambda p: (
            p.impacto_retencao + p.impacto_confiabilidade + p.impacto_eficiencia
        ),
        reverse=True,
    )

    relatorio = {
        "titulo": "Análise de Impacto de Negócio — Pontos P1 a P5",
        "criterios_avaliacao": [
            "Retenção de usuário (escala 1-10)",
            "Confiabilidade do sistema (escala 1-10)",
            "Eficiência operacional (escala 1-10)",
        ],
        "resumo_prioridades": {
            "alta": [p.id for p in pontos_ordenados if p.prioridade == "alta"],
            "media": [p.id for p in pontos_ordenados if p.prioridade == "media"],
            "baixa": [p.id for p in pontos_ordenados if p.prioridade == "baixa"],
        },
        "pontos": [asdict(p) for p in pontos_ordenados],
        "ordem_execucao_recomendada": [p.id for p in pontos_ordenados],
        "metricas_consolidadas": {
            "impacto_medio_retencao": round(
                sum(p.impacto_retencao for p in pontos) / len(pontos), 1
            ),
            "impacto_medio_confiabilidade": round(
                sum(p.impacto_confiabilidade for p in pontos) / len(pontos), 1
            ),
            "impacto_medio_eficiencia": round(
                sum(p.impacto_eficiencia for p in pontos) / len(pontos), 1
            ),
            "total_bugs": sum(1 for p in pontos if p.classificacao == "bug"),
            "total_melhorias": sum(1 for p in pontos if p.classificacao == "melhoria"),
            "total_features": sum(1 for p in pontos if p.classificacao == "feature"),
        },
    }

    return relatorio


def imprimir_analise_formatada(pontos: List[PontoAnalise]) -> None:
    """Imprime a análise em formato legível no console."""
    print("=" * 80)
    print("ANÁLISE DE IMPACTO DE NEGÓCIO — PONTOS P1 A P5")
    print("=" * 80)
    print()

    for ponto in pontos:
        impacto_total = (
            ponto.impacto_retencao
            + ponto.impacto_confiabilidade
            + ponto.impacto_eficiencia
        )
        print(f"--- {ponto.id}: {ponto.titulo} ---")
        print(f"  Classificação: {ponto.classificacao.upper()}")
        print(f"  Prioridade:    {ponto.prioridade.upper()}")
        print(f"  Score Impacto: {impacto_total}/30")
        print(f"    - Retenção:       {ponto.impacto_retencao}/10")
        print(f"    - Confiabilidade: {ponto.impacto_confiabilidade}/10")
        print(f"    - Eficiência:     {ponto.impacto_eficiencia}/10")
        print(f"  Justificativa: {ponto.justificativa}")
        print()

    print("=" * 80)
    print("RESUMO DE PRIORIDADES")
    print("=" * 80)
    alta = [p.id for p in pontos if p.prioridade == "alta"]
    media = [p.id for p in pontos if p.prioridade == "media"]
    baixa = [p.id for p in pontos if p.prioridade == "baixa"]
    print(f"  ALTA:  {', '.join(alta) if alta else 'Nenhum'}")
    print(f"  MÉDIA: {', '.join(media) if media else 'Nenhum'}")
    print(f"  BAIXA: {', '.join(baixa) if baixa else 'Nenhum'}")
    print()
    print(f"  Ordem recomendada de execução: {' → '.join(p.id for p in pontos)}")
    print()


def main():
    """Função principal: executa análise e exibe resultados."""
    pontos = analisar_pontos()

    # Ordenar por impacto total (decrescente)
    pontos_ordenados = sorted(
        pontos,
        key=lambda p: (
            p.impacto_retencao + p.impacto_confiabilidade + p.impacto_eficiencia
        ),
        reverse=True,
    )

    # Imprimir análise formatada
    imprimir_analise_formatada(pontos_ordenados)

    # Gerar e imprimir JSON
    relatorio = gerar_relatorio(pontos)
    print("=" * 80)
    print("SAÍDA JSON")
    print("=" * 80)
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()