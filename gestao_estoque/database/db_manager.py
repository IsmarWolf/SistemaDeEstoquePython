# database/db_manager.py

import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="estoque.db"):
        """
        Conecta ao banco de dados. Se o arquivo não existir, ele será criado.
        Os dados persistirão entre as execuções.
        """
        # Garante que o banco de dados seja criado ou acessado no diretório raiz do projeto
        db_path = os.path.join(os.path.dirname(__file__), '..', db_name)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """
        Cria todas as tabelas do sistema usando "IF NOT EXISTS" para evitar
        recriação e perda de dados. Também insere o usuário 'admin' se ele não existir.
        """
        self.cursor.execute("PRAGMA foreign_keys = ON;")

        # Tabela de Usuários
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nivel_acesso TEXT DEFAULT 'operador' NOT NULL
        )""")

        # Tabela de Fornecedores
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            contato TEXT,
            endereco TEXT
        )""")

        # Tabela de Produtos
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codigo_sku TEXT UNIQUE NOT NULL,
            descricao TEXT,
            quantidade INTEGER NOT NULL,
            preco_unitario REAL NOT NULL,
            unidade_medida TEXT DEFAULT 'un',
            id_fornecedor INTEGER,
            FOREIGN KEY (id_fornecedor) REFERENCES fornecedores(id) ON DELETE SET NULL
        )""")

        # Tabela de Clientes
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT
        )""")

        # Tabela de Movimentações
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_item INTEGER NOT NULL,
            id_usuario INTEGER,
            tipo TEXT NOT NULL, -- 'entrada' ou 'saida'
            quantidade INTEGER NOT NULL,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (id_item) REFERENCES produtos(id) ON DELETE CASCADE,
            FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
        )""")
        
        # Inserir usuário admin padrão APENAS SE NÃO EXISTIR
        self.cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = 'admin'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO usuarios (nome_usuario, senha, nivel_acesso) VALUES (?, ?, ?)",
                                ('admin', 'admin', 'administrador'))

        self.conn.commit()

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def fetch_all(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def fetch_one(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    # --- Usuários ---
    def validate_login(self, username, password):
        return self.fetch_one("SELECT * FROM usuarios WHERE nome_usuario = ? AND senha = ?", (username, password))
    
    def get_all_users(self):
        return self.fetch_all("SELECT id, nome_usuario, nivel_acesso FROM usuarios")

    def add_user(self, username, password, access_level):
        return self.execute_query("INSERT INTO usuarios (nome_usuario, senha, nivel_acesso) VALUES (?, ?, ?)", (username, password, access_level))

    def update_user(self, user_id, username, password, access_level):
        if password:
            return self.execute_query("UPDATE usuarios SET nome_usuario = ?, senha = ?, nivel_acesso = ? WHERE id = ?", (username, password, access_level, user_id))
        else:
            return self.execute_query("UPDATE usuarios SET nome_usuario = ?, nivel_acesso = ? WHERE id = ?", (username, access_level, user_id))

    def delete_user(self, user_id):
        return self.execute_query("DELETE FROM usuarios WHERE id = ?", (user_id,))

    # --- Produtos ---
    def get_all_products(self):
        return self.fetch_all("SELECT id, nome, codigo_sku, quantidade, preco_unitario, descricao FROM produtos ORDER BY nome")

    def add_product(self, nome, sku, desc, qtd, preco):
        return self.execute_query("INSERT INTO produtos (nome, codigo_sku, descricao, quantidade, preco_unitario) VALUES (?, ?, ?, ?, ?)", (nome, sku, desc, qtd, preco))

    def update_product(self, prod_id, nome, sku, desc, qtd, preco):
        return self.execute_query("UPDATE produtos SET nome=?, codigo_sku=?, descricao=?, quantidade=?, preco_unitario=? WHERE id=?", (nome, sku, desc, qtd, preco, prod_id))

    def delete_product(self, prod_id):
        return self.execute_query("DELETE FROM produtos WHERE id = ?", (prod_id,))
    
    def search_products(self, term):
        return self.fetch_all("SELECT id, nome, codigo_sku, quantidade, preco_unitario, descricao FROM produtos WHERE nome LIKE ? OR codigo_sku LIKE ?", (f'%{term}%', f'%{term}%'))

    # --- Clientes ---
    def get_all_clients(self):
        return self.fetch_all("SELECT id, nome, cpf_cnpj, telefone, email, endereco FROM clientes ORDER BY nome")

    def add_client(self, nome, cpf_cnpj, tel, email, end):
        return self.execute_query("INSERT INTO clientes (nome, cpf_cnpj, telefone, email, endereco) VALUES (?, ?, ?, ?, ?)", (nome, cpf_cnpj, tel, email, end))

    def update_client(self, client_id, nome, cpf_cnpj, tel, email, end):
        return self.execute_query("UPDATE clientes SET nome=?, cpf_cnpj=?, telefone=?, email=?, endereco=? WHERE id=?", (nome, cpf_cnpj, tel, email, end, client_id))

    def delete_client(self, client_id):
        return self.execute_query("DELETE FROM clientes WHERE id = ?", (client_id,))

    # --- Fornecedores ---
    def get_all_suppliers(self):
        return self.fetch_all("SELECT id, nome, contato, endereco FROM fornecedores ORDER BY nome")

    def add_supplier(self, nome, contato, endereco):
        return self.execute_query("INSERT INTO fornecedores (nome, contato, endereco) VALUES (?, ?, ?)", (nome, contato, endereco))

    def update_supplier(self, sup_id, nome, contato, endereco):
        return self.execute_query("UPDATE fornecedores SET nome=?, contato=?, endereco=? WHERE id=?", (nome, contato, endereco, sup_id))

    def delete_supplier(self, sup_id):
        return self.execute_query("DELETE FROM fornecedores WHERE id = ?", (sup_id,))

    # --- Movimentações ---
    def get_all_movements(self):
        query = """
        SELECT m.id, p.nome, u.nome_usuario, m.tipo, m.quantidade, m.data_hora
        FROM movimentacoes m
        JOIN produtos p ON m.id_item = p.id
        LEFT JOIN usuarios u ON m.id_usuario = u.id
        ORDER BY m.data_hora DESC
        """
        return self.fetch_all(query)

    def add_movement(self, id_item, id_usuario, tipo, quantidade):
        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute(
                "INSERT INTO movimentacoes (id_item, id_usuario, tipo, quantidade, data_hora) VALUES (?, ?, ?, ?, ?)",
                (id_item, id_usuario, tipo, quantidade, data_hora)
            )
            
            if tipo.lower() == 'entrada':
                self.cursor.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", (quantidade, id_item))
            elif tipo.lower() == 'saida':
                stock = self.fetch_one("SELECT quantidade FROM produtos WHERE id = ?", (id_item,))
                if stock and stock[0] < quantidade:
                    self.conn.rollback()
                    return "Estoque insuficiente."
                self.cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (quantidade, id_item))
            
            self.conn.commit()
            return "Sucesso"
        except sqlite3.Error as e:
            self.conn.rollback()
            return f"Erro: {e}"

    def close(self):
        """Fecha a conexão com o banco de dados."""
        self.conn.close()