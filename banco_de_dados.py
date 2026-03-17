import sqlite3


def conecta_db(db_caminho: str = 'banco_de_dados.db') -> sqlite3.Connection:
    """
    Cria uma conexão com o banco de dados SQLite.

    Argumentos:
        db_caminho: caminho para o arquivo do banco de dados.

    Retorna:
        conn: conexão configurada com chaves estrangeiras e row_factory ativados.
    """
    conn = sqlite3.connect(db_caminho)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def cria_tabela(conn: sqlite3.Connection, nome_tabela: str, colunas: list[str]) -> None:
    """
    Cria uma tabela no banco de dados SQLite caso ela ainda não exista.

    Argumentos:
        conn: conexão ativa com o banco de dados.
        nome_tabela: nome da tabela a ser criada.
        colunas: lista de strings com as definições de cada coluna.
    """
    cursor = conn.cursor()
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {nome_tabela} ({', '.join(colunas)})")
    conn.commit()


def insere_dado(conn: sqlite3.Connection, nome_tabela: str, dados: dict) -> None:
    """
    Insere um registro em uma tabela do banco de dados.

    Argumentos:
        conn: conexão ativa com o banco de dados.
        nome_tabela: nome da tabela de destino.
        dados: dicionário com os valores a inserir (chave = nome da coluna).
    """
    cursor = conn.cursor()
    colunas = ', '.join(dados.keys())
    valores = ', '.join(['?' for _ in dados])
    cursor.execute(
        f"INSERT INTO {nome_tabela} ({colunas}) VALUES ({valores})",
        list(dados.values())
    )
    conn.commit()


def obtem_dados(conn: sqlite3.Connection, nome_tabela: str, colunas: list[str]) -> list:
    """
    Obtém registros de uma tabela do banco de dados.

    Argumentos:
        conn: conexão ativa com o banco de dados.
        nome_tabela: nome da tabela de origem.
        colunas: lista de colunas a serem retornadas.

    Retorna:
        Lista de registros obtidos.
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT {', '.join(colunas)} FROM {nome_tabela}")
    return cursor.fetchall()


def inicializa_db() -> None:
    """
    Inicializa o banco de dados SQLite criando as três tabelas do sistema.

    Tabelas criadas:
        Financiamentos: dados principais de cada empréstimo.
        Parcelas: parcelas calculadas por financiamento (cascade delete).
        AmortizacoesExtras: amortizações extras por financiamento (cascade delete).
    """
    conn = conecta_db()

    cria_tabela(conn, 'Financiamentos', [
        'id                 INTEGER  PRIMARY KEY AUTOINCREMENT',
        'nome               TEXT     NOT NULL UNIQUE',
        'valor_imovel       NUMERIC  NOT NULL',
        'entrada            NUMERIC  NOT NULL',
        'taxa_juros         NUMERIC  NOT NULL',
        'prazo_meses        INTEGER  NOT NULL',
        'data_inicio        TEXT     NOT NULL'
    ])

    cria_tabela(conn, 'Parcelas', [
        'id               INTEGER  PRIMARY KEY AUTOINCREMENT',
        'financiamento_id INTEGER  NOT NULL REFERENCES Financiamentos(id) ON DELETE CASCADE',
        'numero_parcela   INTEGER  NOT NULL',
        'data_parcela     TEXT     NOT NULL',
        'valor_parcela    NUMERIC  NOT NULL',
    ])

    cria_tabela(conn, 'AmortizacoesExtras', [
        'id               INTEGER  PRIMARY KEY AUTOINCREMENT',
        'financiamento_id INTEGER  NOT NULL REFERENCES Financiamentos(id) ON DELETE CASCADE',
        'valor_amortizado NUMERIC  NOT NULL',
        'data_amortizacao TEXT     NOT NULL'
    ])

    conn.close()
