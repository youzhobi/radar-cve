"""
queries.py
-----------
Este arquivo guarda as "perguntas" (queries) que fazemos ao banco
de dados usando SQL. Cada função aqui faz UMA pergunta específica
e devolve a resposta pronta para o Python usar.

SQL é a linguagem que usamos para pedir coisas ao banco de dados,
tipo: "me dê todas as CVEs críticas dos últimos 7 dias, da mais
grave para a menos grave".

Como testar sozinho:
    python queries.py
"""

from db import conectar


def cves_por_severidade():
    """
    Pergunta: "Quantas CVEs existem de cada nível de severidade?"

    Isso é uma AGREGAÇÃO: o SQL primeiro AGRUPA (GROUP BY) as
    linhas pela coluna severidade, e depois CONTA (COUNT) quantas
    linhas caem em cada grupo. É como separar um monte de cartas
    em pilhas por naipe e depois contar cada pilha.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT severidade, COUNT(*) AS total
        FROM cve
        GROUP BY severidade
        ORDER BY total DESC
        """
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado  # ex: [("HIGH", 12), ("MEDIUM", 8), ...]


def cves_criticas_recentes(limite=10):
    """
    Pergunta: "Quais são as CVEs mais graves (CRITICAL ou HIGH),
    ordenadas da nota mais alta para a mais baixa?"

    O WHERE filtra só as linhas que interessam, o ORDER BY organiza
    do maior score para o menor, e o LIMIT corta a lista no tamanho
    que a gente pedir.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, descricao, severidade, score_cvss, data_publicacao
        FROM cve
        WHERE severidade IN ('CRITICAL', 'HIGH')
        ORDER BY score_cvss DESC
        LIMIT ?
        """,
        (limite,),
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def cves_por_dia():
    """
    Pergunta: "Quantas CVEs foram publicadas em cada dia?"

    Essa é uma query de TENDÊNCIA: ajuda a enxergar se o número de
    CVEs está subindo, descendo ou estável ao longo do tempo.

    A coluna data_publicacao guarda data E hora juntas
    (ex: "2026-08-10T10:00:00"). Usamos substr(texto, 1, 10) pra
    pegar só os 10 primeiros caracteres (a parte da data) - senão
    cada horário diferente viraria um grupo separado no GROUP BY,
    e nunca duas CVEs do mesmo dia ficariam juntas.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT substr(data_publicacao, 1, 10) AS dia, COUNT(*) AS total
        FROM cve
        GROUP BY dia
        ORDER BY dia
        """
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def produtos_recorrentes_em_criticas(minimo_ocorrencias=2):
    """
    Pergunta: "Quais produtos aparecem em MAIS DE UMA CVE crítica?"

    Essa query junta três ideias de SQL na mesma consulta:

      - JOIN: liga a tabela de produtos com a tabela de CVEs.
      - WHERE: filtra LINHA POR LINHA, antes de qualquer
        agrupamento (aqui, só as linhas com severidade CRITICAL).
      - HAVING: filtra DEPOIS que os grupos já foram formados e o
        COUNT(*) já foi calculado. Isso é obrigatório aqui: tentar
        colocar "COUNT(*) > 1" dentro do WHERE dá erro, porque na
        hora que o WHERE roda, o banco ainda nem agrupou nada -
        o COUNT(*) simplesmente ainda não existe naquele momento.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT produto_afetado.nome_produto, COUNT(*) AS total_cves_criticas
        FROM produto_afetado
        JOIN cve ON produto_afetado.cve_id = cve.id
        WHERE cve.severidade = 'CRITICAL'
        GROUP BY produto_afetado.nome_produto
        HAVING COUNT(*) >= ?
        ORDER BY total_cves_criticas DESC
        """,
        (minimo_ocorrencias,),
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def todas_as_cves(limite=500):
    """
    Pergunta: "Me dê todas as CVEs, de qualquer severidade,
    da mais grave pra menos grave."

    Diferente de cves_criticas_recentes(), essa NÃO tem WHERE
    nenhum - é por isso que ela serve pra alimentar a tabela
    inteira do dashboard, incluindo os filtros HIGH, MEDIUM e LOW
    (a outra query só devolvia CRITICAL/HIGH, então os outros
    filtros ficavam vazios).
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, descricao, severidade, score_cvss, data_publicacao
        FROM cve
        ORDER BY score_cvss DESC
        LIMIT ?
        """,
        (limite,),
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


def produtos_afetados_por_cve(cve_id):
    """
    Pergunta: "Quais produtos essa CVE específica afeta?"

    Aqui usamos um JOIN: juntamos a tabela 'cve' com a tabela
    'produto_afetado', ligando as duas pela coluna em comum
    (cve.id = produto_afetado.cve_id). É como grampear duas
    planilhas usando uma coluna que existe nas duas.
    """
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT cve.id, cve.descricao, produto_afetado.nome_produto
        FROM cve
        JOIN produto_afetado ON cve.id = produto_afetado.cve_id
        WHERE cve.id = ?
        """,
        (cve_id,),
    )
    resultado = cursor.fetchall()
    conexao.close()
    return resultado


# Um "teste rápido na mão": roda as queries e mostra o resultado
# na tela, sem precisar do Firebase nem de nada externo.
if __name__ == "__main__":
    print("📊 CVEs por severidade:")
    for severidade, total in cves_por_severidade():
        print(f"   {severidade}: {total}")

    print("\n🔥 Top CVEs críticas/altas:")
    for cve_id, descricao, severidade, score, data in cves_criticas_recentes(5):
        print(f"   [{severidade} - {score}] {cve_id} ({data})")

    print("\n📈 CVEs por dia:")
    for dia, total in cves_por_dia():
        print(f"   {dia}: {total}")

    print("\n♻️  Produtos com mais de 1 CVE crítica:")
    for produto, total in produtos_recorrentes_em_criticas(2):
        print(f"   {produto}: {total} CVEs críticas")
