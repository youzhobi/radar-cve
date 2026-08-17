"""
sync_firestore.py
-------------------
Este script pega os dados que já estão organizados no SQLite
(nosso banco local) e envia uma cópia resumida para o Firestore,
que é o banco de dados do Firebase na nuvem. É o Firestore que o
nosso painel (dashboard) na internet vai ler.

Analogia:
    SQLite     = seu caderno de anotações pessoal (só você acessa)
    Firestore  = um quadro de avisos público na internet

Este script é a "mão" que copia informação do caderno para o quadro.

IMPORTANTE: para este script funcionar, você precisa ter baixado
o arquivo de chave da conta de serviço do Firebase e salvo como
"firebase-service-account.json" na raiz do projeto (veja o README).

Como rodar:
    python sync_firestore.py
"""

import firebase_admin
from firebase_admin import credentials, firestore

from queries import (
    cves_criticas_recentes,
    cves_por_severidade,
    cves_por_dia,
    produtos_recorrentes_em_criticas,
    todas_as_cves,
)

# Caminho para o arquivo de chave secreta da conta de serviço.
# Esse arquivo NUNCA deve ser compartilhado ou enviado ao GitHub
# (por isso ele já está no .gitignore do projeto).
CAMINHO_CHAVE_FIREBASE = "../firebase-service-account.json"


def iniciar_firebase():
    """
    "Liga" a conexão com o Firebase usando a chave secreta.
    Isso só precisa ser feito uma vez, no começo do script.
    Devolve um objeto "db" que sabemos usar para ler/escrever
    no Firestore.
    """
    credencial = credentials.Certificate(CAMINHO_CHAVE_FIREBASE)
    firebase_admin.initialize_app(credencial)
    return firestore.client()


def enviar_resumo_severidade(db):
    """
    Envia para o Firestore a contagem de CVEs por severidade.
    No dashboard, isso vira os cartõezinhos de resumo no topo
    da página (ex: "CRITICAL: 3", "HIGH: 12"...).
    """
    resumo = cves_por_severidade()  # lista de tuplas: [("HIGH", 12), ...]

    # No Firestore, os dados ficam organizados em "coleções"
    # (parecido com pastas) e "documentos" (parecido com arquivos
    # dentro da pasta). Aqui usamos UM documento só, chamado
    # "por_severidade", dentro da coleção "resumo".
    referencia = db.collection("resumo").document("por_severidade")

    dados_para_enviar = {severidade: total for severidade, total in resumo}
    referencia.set(dados_para_enviar)
    print("📤 Resumo de severidade enviado ao Firestore.")


def enviar_cves(db, limite=500):
    """
    Envia para o Firestore a lista de CVEs de TODAS as severidades,
    uma por documento, dentro da coleção "cves_recentes". É essa
    coleção que alimenta a tabela principal do dashboard - inclusive
    os filtros de Critical/High/Medium/Low.
    """
    lista = todas_as_cves(limite)

    for cve_id, descricao, severidade, score, data_publicacao in lista:
        referencia = db.collection("cves_recentes").document(cve_id)
        referencia.set(
            {
                "id": cve_id,
                "descricao": descricao,
                "severidade": severidade,
                "score": score,
                "data_publicacao": data_publicacao,
            }
        )

    print(f"📤 {len(lista)} CVEs (todas as severidades) enviadas ao Firestore.")


def enviar_tendencia_por_dia(db):
    """
    Envia para o Firestore a contagem de CVEs por dia (a query de
    tendência que aprendemos com a história das caixinhas).
    No dashboard, isso vira o gráfico de barrinhas simples mostrando
    se o número de CVEs está subindo ou descendo.
    """
    tendencia = cves_por_dia()  # lista de tuplas: [("2026-08-10", 2), ...]

    referencia = db.collection("resumo").document("por_dia")
    dados_para_enviar = {dia: total for dia, total in tendencia}
    referencia.set(dados_para_enviar)
    print("📤 Tendência por dia enviada ao Firestore.")


def enviar_produtos_recorrentes(db, minimo_ocorrencias=2, limite=10):
    """
    Envia para o Firestore os produtos que aparecem em mais de uma
    CVE crítica (a query com JOIN + WHERE + HAVING - a história dos
    brinquedos dentro das caixinhas vermelhas).
    """
    produtos = produtos_recorrentes_em_criticas(minimo_ocorrencias)[:limite]

    referencia = db.collection("resumo").document("produtos_recorrentes")
    dados_para_enviar = {produto: total for produto, total in produtos}
    referencia.set(dados_para_enviar)
    print(f"📤 {len(produtos)} produtos recorrentes enviados ao Firestore.")


def main():
    """Liga tudo em sequência: conecta, envia resumo, envia lista."""
    db = iniciar_firebase()
    enviar_resumo_severidade(db)
    enviar_cves(db)
    enviar_tendencia_por_dia(db)
    enviar_produtos_recorrentes(db)
    print("✅ Sincronização com o Firebase concluída!")


if __name__ == "__main__":
    main()
