-- ============================================================
--  schema.sql
--  Este arquivo é a "PLANTA DA CASA" do nosso banco de dados.
--  Ele não guarda dados, ele só descreve COMO as tabelas devem
--  ser construídas (quais colunas cada uma tem).
--
--  SQLite guarda tudo isso dentro de UM ÚNICO arquivo no seu
--  computador (o cve_tracker.db) - não precisa instalar nenhum
--  programa de banco de dados separado.
-- ============================================================

-- --------------------------------------------------------------
-- Tabela 1: cve
-- Pense nela como uma PLANILHA. Cada LINHA é uma vulnerabilidade
-- (uma "CVE") encontrada em algum sistema no mundo.
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cve (
    id                TEXT PRIMARY KEY,  -- Código único, ex: "CVE-2024-12345"
                                          -- PRIMARY KEY = não pode repetir, é
                                          -- o "RG" dessa linha na tabela.
    descricao         TEXT,              -- Texto explicando a vulnerabilidade
    severidade        TEXT,              -- LOW, MEDIUM, HIGH ou CRITICAL
    score_cvss        REAL,              -- Nota de 0.0 a 10.0 (quanto maior, pior)
    data_publicacao   TEXT,              -- Quando a CVE foi divulgada
    data_atualizacao  TEXT               -- Última vez que os dados mudaram
);

-- --------------------------------------------------------------
-- Tabela 2: produto_afetado
-- Uma CVE pode afetar VÁRIOS produtos (ex: Windows 10, Apache 2.4).
-- Por isso essa é uma tabela separada: cada linha aqui diz
-- "esse produto é afetado por aquela CVE".
--
-- A coluna cve_id é a "ponte" que liga essa tabela à tabela cve.
-- Isso se chama CHAVE ESTRANGEIRA (foreign key).
-- --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produto_afetado (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- número interno, gerado sozinho
    cve_id        TEXT,                                -- de qual CVE é esse produto
    nome_produto  TEXT,                                -- nome/identificador do produto
    FOREIGN KEY (cve_id) REFERENCES cve(id)
    -- essa linha diz ao SQLite: "todo cve_id aqui precisa existir
    -- de verdade na tabela cve" - isso evita dados quebrados.
);
