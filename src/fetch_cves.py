"""
fetch_cves.py
--------------
Este script faz 3 coisas, sempre nessa ordem:

  1. Pede para a internet (API do NVD) a lista de vulnerabilidades
     (CVEs) publicadas nos últimos 7 dias.
  2. Organiza essas informações, pegando só o que interessa.
  3. Guarda tudo dentro do nosso banco de dados SQLite.

O NVD (National Vulnerability Database) é um banco de dados público
e gratuito, mantido pelo governo dos EUA, que lista vulnerabilidades
de segurança conhecidas em softwares do mundo todo. Não precisa de
cadastro nem chave de API para pedidos pequenos como o nosso.

Como rodar:
    python fetch_cves.py
"""

import requests  # biblioteca para "conversar" com sites/APIs pela internet
from datetime import datetime, timedelta, timezone

from db import conectar, criar_tabelas

# Endereço da API do NVD que devolve a lista de CVEs
URL_API_NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def calcular_periodo_ultimos_dias(dias=7):
    """
    A API do NVD exige que a gente diga um período de datas
    (de quando até quando queremos buscar CVEs).

    Essa função calcula "de X dias atrás até agora" e devolve as
    duas datas já no formato de texto que a API entende.
    """
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)

    formato = "%Y-%m-%dT%H:%M:%S.000"
    return inicio.strftime(formato), agora.strftime(formato)


def buscar_cves_recentes(dias=7):
    """
    Faz o pedido (request) para a API do NVD e devolve a lista de
    CVEs encontradas. Cada CVE chega como um "dicionário" Python
    (pares de chave: valor), dentro de um JSON gigante.
    """
    data_inicio, data_fim = calcular_periodo_ultimos_dias(dias)

    parametros = {
        "pubStartDate": data_inicio,
        "pubEndDate": data_fim,
        "resultsPerPage": 50,  # no máximo 50 CVEs por pedido
    }

    print(f"🔎 Buscando CVEs publicadas entre {data_inicio} e {data_fim}...")
    resposta = requests.get(URL_API_NVD, params=parametros, timeout=30)
    resposta.raise_for_status()  # se der erro (404, 500...), para aqui e avisa

    dados = resposta.json()
    lista_cves = dados.get("vulnerabilities", [])
    print(f"📦 {len(lista_cves)} CVEs recebidas da API.")
    return lista_cves


def filtrar_cves_rejeitadas(lista_cves):
    """
    O NVD também devolve CVEs que foram OFICIALMENTE CANCELADAS
    (campo vulnStatus = "Rejected") - normalmente porque não eram
    uma vulnerabilidade de verdade, ou o ID foi criado por engano.

    Essas não representam risco nenhum, então não faz sentido
    guardar elas no nosso banco. Essa função separa só as que
    ainda estão válidas.
    """
    validas = [
        item for item in lista_cves
        if item["cve"].get("vulnStatus") != "Rejected"
    ]

    quantidade_rejeitadas = len(lista_cves) - len(validas)
    if quantidade_rejeitadas > 0:
        print(f"🚫 {quantidade_rejeitadas} CVEs rejeitadas foram descartadas.")

    return validas


def extrair_informacoes(item_cve):
    """
    Cada item que vem da API é um JSON grande, cheio de detalhes
    que não vamos usar. Essa função "filtra" só as partes que
    interessam: id, descrição, severidade, nota (score) e datas.

    Pense nisso como preencher uma ficha resumida a partir de um
    processo inteiro.
    """
    cve = item_cve["cve"]
    cve_id = cve["id"]

    # A descrição vem em vários idiomas; pegamos a que está em inglês
    descricao = ""
    for texto in cve.get("descriptions", []):
        if texto["lang"] == "en":
            descricao = texto["value"]
            break

    # A nota de severidade (CVSS) pode vir em versões diferentes.
    # Tentamos pegar a mais nova primeiro (v3.1), depois v3.0, depois v2.
    severidade = "DESCONHECIDA"
    score = None
    metricas = cve.get("metrics", {})

    if "cvssMetricV31" in metricas:
        dado = metricas["cvssMetricV31"][0]["cvssData"]
        severidade = dado["baseSeverity"]
        score = dado["baseScore"]
    elif "cvssMetricV30" in metricas:
        dado = metricas["cvssMetricV30"][0]["cvssData"]
        severidade = dado["baseSeverity"]
        score = dado["baseScore"]
    elif "cvssMetricV2" in metricas:
        dado = metricas["cvssMetricV2"][0]
        severidade = dado.get("baseSeverity", "DESCONHECIDA")
        score = dado["cvssData"]["baseScore"]

    # Lista de produtos afetados, se essa informação existir
    produtos = []
    for configuracao in cve.get("configurations", []):
        for node in configuracao.get("nodes", []):
            for match in node.get("cpeMatch", []):
                produtos.append(match.get("criteria", "produto desconhecido"))

    return {
        "id": cve_id,
        "descricao": descricao,
        "severidade": severidade,
        "score": score,
        "data_publicacao": cve.get("published"),
        "data_atualizacao": cve.get("lastModified"),
        "produtos": produtos,
    }


def salvar_no_banco(cves_extraidas):
    """
    Pega a lista de CVEs já organizadas e salva no banco SQLite.

    Usamos "INSERT OR REPLACE": se a CVE já existir (por exemplo,
    você rodou o script ontem e hoje de novo), ela é atualizada
    ao invés de criar uma linha duplicada.
    """
    conexao = conectar()
    cursor = conexao.cursor()

    for item in cves_extraidas:
        cursor.execute(
            """
            INSERT OR REPLACE INTO cve
                (id, descricao, severidade, score_cvss, data_publicacao, data_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["descricao"],
                item["severidade"],
                item["score"],
                item["data_publicacao"],
                item["data_atualizacao"],
            ),
        )

        # Antes de inserir os produtos de novo, apagamos os antigos
        # dessa CVE, para não duplicar se o script rodar várias vezes.
        cursor.execute("DELETE FROM produto_afetado WHERE cve_id = ?", (item["id"],))

        for produto in item["produtos"]:
            cursor.execute(
                "INSERT INTO produto_afetado (cve_id, nome_produto) VALUES (?, ?)",
                (item["id"], produto),
            )

    conexao.commit()
    conexao.close()
    print(f"💾 {len(cves_extraidas)} CVEs salvas no banco de dados.")


def main():
    """
    Função principal: liga tudo em sequência, do começo ao fim.
    É o "botão de start" deste script.
    """
    criar_tabelas()                              # 1. garante que as tabelas existem
    cves_brutas = buscar_cves_recentes(dias=7)    # 2. busca na internet
    cves_validas = filtrar_cves_rejeitadas(cves_brutas)      # 3. descarta as canceladas
    cves_prontas = [extrair_informacoes(c) for c in cves_validas]  # 4. organiza
    salvar_no_banco(cves_prontas)                 # 5. guarda no SQLite


if __name__ == "__main__":
    main()
