"""
db.py
------
Este arquivo tem UMA única missão: abrir a "caixa" (o banco de
dados SQLite) onde vamos guardar as CVEs, e garantir que as
tabelas já existem antes de qualquer outro script tentar usá-las.

Analogia: o SQLite é um arquivo único no seu computador (parecido
com um .xlsx), mas que sabe guardar TABELAS dentro dele e responder
perguntas em SQL. Não precisa instalar nenhum programa de banco de
dados à parte - o Python já sabe conversar com ele sozinho, usando
a biblioteca "sqlite3" que já vem pronta.
"""

import sqlite3
import os

# --------------------------------------------------------------
# Descobrindo os caminhos dos arquivos automaticamente, para que
# o script funcione não importa de onde você o execute.
# --------------------------------------------------------------
PASTA_SRC = os.path.dirname(os.path.abspath(__file__))          # pasta "src/"
PASTA_PROJETO = os.path.dirname(PASTA_SRC)                       # pasta raiz do projeto
CAMINHO_BANCO = os.path.join(PASTA_PROJETO, "database", "cve_tracker.db")
CAMINHO_SCHEMA = os.path.join(PASTA_PROJETO, "database", "schema.sql")


def conectar():
    """
    Abre uma "porta de entrada" para o banco de dados.
    Toda vez que quisermos ler ou escrever alguma coisa, vamos
    precisar chamar essa função primeiro para conseguir essa conexão.
    """
    conexao = sqlite3.connect(CAMINHO_BANCO)
    return conexao


def criar_tabelas():
    """
    Lê o arquivo schema.sql (a "planta da casa") e manda o SQLite
    construir as tabelas, caso elas ainda não existam.

    É seguro rodar essa função várias vezes: se as tabelas já
    existirem, ela simplesmente não faz nada (por causa do
    "IF NOT EXISTS" que colocamos no schema.sql).
    """
    conexao = conectar()
    with open(CAMINHO_SCHEMA, "r", encoding="utf-8") as arquivo:
        script_sql = arquivo.read()

    conexao.executescript(script_sql)  # roda várias instruções SQL de uma vez
    conexao.commit()                    # "salva" as mudanças de verdade
    conexao.close()                     # fecha a porta de entrada
    print("✅ Tabelas verificadas/criadas com sucesso em:", CAMINHO_BANCO)


# Isso só roda se você executar "python db.py" diretamente
# (e não quando outro arquivo importa este como biblioteca).
if __name__ == "__main__":
    criar_tabelas()
