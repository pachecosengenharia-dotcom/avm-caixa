import sqlite3

# Conecta ao mesmo arquivo de banco de dados que aparece no seu app
conexao = sqlite3.connect("base_instituicao_financeira.db")
cursor = conexao.cursor()

# Garante que a tabela existe
cursor.execute('''
    CREATE TABLE IF NOT EXISTS imoveis_banco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipologia TEXT,
        area REAL,
        valor REAL
    )
''')

# Lista de dados de teste para popular a tabela
dados_teste = [
    ("Casa", 120.5, 380000.0),
    ("Apartamento", 85.0, 290000.0),
    ("Lote", 300.0, 150000.0),
    ("Galpão Comercial", 450.0, 950000.0)
]

# Insere os dados de teste na tabela
cursor.executemany("INSERT INTO imoveis_banco (tipologia, area, valor) VALUES (?, ?, ?)", dados_teste)

# Salva as alterações e fecha a conexão
conexao.commit()
conexao.close()

print("✅ Dados de teste inseridos com sucesso no banco SQLite!")