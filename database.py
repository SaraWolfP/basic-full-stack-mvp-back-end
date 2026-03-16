import sqlite3


DATABASE_PATH = "financiamentos.db"


def get_connection() -> sqlite3.Connection:
    """
    Abre e retorna uma conexão com o banco SQLite configurada para uso na API.

    Configurações aplicadas:
        - row_factory = sqlite3.Row: permite acessar colunas pelo nome (ex: row["nome"])
          em vez de apenas por índice numérico.
        - PRAGMA foreign_keys = ON: habilita o suporte a chaves estrangeiras e
          cascata de deleção, que o SQLite desativa por padrão.

    Returns:
        sqlite3.Connection: conexão pronta para uso.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """
    Cria as tabelas do banco de dados caso ainda não existam.

    Tabelas:
        Financiamentos:
            Armazena os dados de cada empréstimo cadastrado.
            'nome' é UNIQUE para evitar duplicatas identificáveis pelo usuário.
            'modelo_amortizacao' aceita apenas 'PRICE' ou 'SAC' via CHECK.

        Parcelas:
            Armazena as parcelas calculadas de cada financiamento.
            Deletada em cascata quando o financiamento pai é removido.
            'numero_parcela' permite ordenação e identificação da sequência.

        AmortizacoesExtras:
            Registra cada amortização extra realizada pelo usuário.
            Deletada em cascata quando o financiamento pai é removido.
            'tipo_amortizacao' aceita apenas 'Prazo' ou 'Parcela' via CHECK:
                - 'Prazo':   mantém o valor da parcela, reduz o número de meses.
                - 'Parcela': mantém o número de meses, reduz o valor da parcela.
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Financiamentos (
                id                  INTEGER  PRIMARY KEY AUTOINCREMENT,
                nome                TEXT     NOT NULL UNIQUE,
                valor_imovel        NUMERIC  NOT NULL,
                entrada             NUMERIC  NOT NULL,
                taxa_juros          NUMERIC  NOT NULL,
                prazo_meses         INTEGER  NOT NULL,
                data_inicio         TEXT     NOT NULL,
                modelo_amortizacao  TEXT     NOT NULL
                    CHECK (modelo_amortizacao IN ('PRICE', 'SAC'))
            );

            CREATE TABLE IF NOT EXISTS Parcelas (
                id               INTEGER  PRIMARY KEY AUTOINCREMENT,
                financiamento_id INTEGER  NOT NULL
                    REFERENCES Financiamentos(id) ON DELETE CASCADE,
                numero_parcela   INTEGER  NOT NULL,
                data_parcela     TEXT     NOT NULL,
                valor_parcela    NUMERIC  NOT NULL
            );

            CREATE TABLE IF NOT EXISTS AmortizacoesExtras (
                id               INTEGER  PRIMARY KEY AUTOINCREMENT,
                financiamento_id INTEGER  NOT NULL
                    REFERENCES Financiamentos(id) ON DELETE CASCADE,
                valor_amortizado NUMERIC  NOT NULL,
                data_amortizacao TEXT     NOT NULL,
                tipo_amortizacao TEXT     NOT NULL
                    CHECK (tipo_amortizacao IN ('Prazo', 'Parcela'))
            );
        """)
