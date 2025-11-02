# database/db_manager.py (COMPLETO E CORRIGIDO)

import sqlite3
import os
import sys
from datetime import datetime, timedelta

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class DatabaseManager:
    def __init__(self, db_name="estoque.db"):
        base_path = get_base_path()
        db_path = os.path.join(base_path, db_name)
        db_exists = os.path.exists(db_path)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
        if not db_exists:
            self.populate_initial_data()

    def create_tables(self):
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nivel_acesso TEXT NOT NULL CHECK(nivel_acesso IN ('Administrador', 'Supervisor', 'Operador'))
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            codigo_sku TEXT UNIQUE NOT NULL,
            descricao TEXT,
            quantidade INTEGER NOT NULL,
            quantidade_inicial INTEGER NOT NULL DEFAULT 1,
            id_fornecedor INTEGER,
            FOREIGN KEY (id_fornecedor) REFERENCES fornecedores(id) ON DELETE SET NULL
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_item INTEGER NOT NULL,
            id_usuario INTEGER,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            preco_transacao REAL NOT NULL,
            id_cliente INTEGER,
            id_fornecedor INTEGER,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (id_item) REFERENCES produtos(id) ON DELETE CASCADE,
            FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL,
            FOREIGN KEY (id_cliente) REFERENCES clientes(id) ON DELETE SET NULL,
            FOREIGN KEY (id_fornecedor) REFERENCES fornecedores(id) ON DELETE SET NULL
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'não lida' CHECK(status IN ('lida', 'não lida'))
        )""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, contato TEXT, endereco TEXT)""")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, cpf_cnpj TEXT, telefone TEXT, email TEXT, endereco TEXT)""")
        self.cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = 'admin'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO usuarios (nome_usuario, senha, nivel_acesso) VALUES (?, ?, ?)", ('admin', 'admin', 'Administrador'))
        self.conn.commit()

    # <--- FUNÇÃO CORRIGIDA E ROBUSTA ---
    def populate_initial_data(self):
        try:
            produtos = [
                ('Notebook Gamer Pro', 'NT-GMR-001', 'Notebook de alta performance para jogos', 50, 50),
                ("Monitor Curvo 27'", "MN-CRV-027", "Monitor ultrawide para imersão total", 80, 80)
            ]
            self.cursor.executemany("INSERT INTO produtos (nome, codigo_sku, descricao, quantidade, quantidade_inicial) VALUES (?, ?, ?, ?, ?)", produtos)

            clientes = [
                ("Empresa Alfa", "11222333000144", "11987654321", "contato@alfa.com", "Rua das Flores, 123"),
                ("João da Silva", "12345678900", "21912345678", "joao.silva@email.com", "Avenida Principal, 456")
            ]
            self.cursor.executemany("INSERT INTO clientes (nome, cpf_cnpj, telefone, email, endereco) VALUES (?, ?, ?, ?, ?)", clientes)

            fornecedores = [
                ("Distribuidora Tech", "Maria Souza", "Rua dos Importados, 789"),
                ("Atacado de Eletrônicos", "Carlos Pereira", "Avenida do Comércio, 101")
            ]
            self.cursor.executemany("INSERT INTO fornecedores (nome, contato, endereco) VALUES (?, ?, ?)", fornecedores)
            
            self.conn.commit()
            print("Banco de dados populado com dados iniciais de teste.")
        except Exception as e:
            print(f"Erro ao popular o banco de dados: {e}")

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params); self.conn.commit(); return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                field = str(e).split('.')[-1]
                return f"Erro: O valor fornecido para '{field}' já existe."
            raise e
        except sqlite3.Error as e:
            print(f"Database error: {e}"); raise e
    def fetch_all(self, query, params=()):
        try:
            self.cursor.execute(query, params); return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}"); return []
    def fetch_one(self, query, params=()):
        try:
            self.cursor.execute(query, params); return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Database error: {e}"); return None
    
    def validate_login(self, username, password):
        return self.fetch_one("SELECT * FROM usuarios WHERE nome_usuario = ? AND senha = ?", (username, password))
    def get_user_by_id(self, user_id):
        return self.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    def get_all_users(self):
        return self.fetch_all("SELECT id, nome_usuario, nivel_acesso FROM usuarios")
    def add_user(self, username, password, access_level):
        result = self.execute_query("INSERT INTO usuarios (nome_usuario, senha, nivel_acesso) VALUES (?, ?, ?)", (username, password, access_level))
        if isinstance(result, int):
            self.add_notification(f"Novo usuário '{username}' foi criado.")
        return result
    def update_user(self, user_id, username, password, access_level):
        if password: return self.execute_query("UPDATE usuarios SET nome_usuario = ?, senha = ?, nivel_acesso = ? WHERE id = ?", (username, password, access_level, user_id))
        else: return self.execute_query("UPDATE usuarios SET nome_usuario = ?, nivel_acesso = ? WHERE id = ?", (username, access_level, user_id))
    def delete_user(self, user_id):
        return self.execute_query("DELETE FROM usuarios WHERE id = ?", (user_id,))
    
    def get_all_products(self):
        return self.fetch_all("SELECT id, nome, codigo_sku, descricao, quantidade FROM produtos ORDER BY nome")
    def get_product_by_id(self, product_id):
        return self.fetch_one("SELECT * FROM produtos WHERE id = ?", (product_id,))
    def add_product(self, nome, sku, desc, qtd):
        return self.execute_query("INSERT INTO produtos (nome, codigo_sku, descricao, quantidade, quantidade_inicial) VALUES (?, ?, ?, ?, ?)", (nome, sku, desc, qtd, qtd))
    def update_product(self, prod_id, nome, sku, desc, qtd):
        return self.execute_query("UPDATE produtos SET nome=?, codigo_sku=?, descricao=?, quantidade=? WHERE id=?", (nome, sku, desc, qtd, prod_id))
    def delete_product(self, prod_id):
        return self.execute_query("DELETE FROM produtos WHERE id = ?", (prod_id,))
    
    def add_movement(self, id_item, id_usuario, tipo, quantidade, preco_transacao, id_cliente=None, id_fornecedor=None):
        try:
            self.conn.execute("BEGIN TRANSACTION")
            produto = self.fetch_one("SELECT nome, quantidade, quantidade_inicial FROM produtos WHERE id = ?", (id_item,))
            if not produto:
                self.conn.rollback(); return "Produto não encontrado."
            data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute(
                "INSERT INTO movimentacoes (id_item, id_usuario, tipo, quantidade, preco_transacao, id_cliente, id_fornecedor, data_hora) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (id_item, id_usuario, tipo, quantidade, preco_transacao, id_cliente, id_fornecedor, data_hora)
            )
            new_stock = 0
            if tipo.lower() == 'entrada':
                new_stock = produto[1] + quantidade
                self.cursor.execute("UPDATE produtos SET quantidade = ? WHERE id = ?", (new_stock, id_item))
            elif tipo.lower() == 'saida':
                if produto[1] < quantidade:
                    self.conn.rollback(); return "Estoque insuficiente."
                new_stock = produto[1] - quantidade
                self.cursor.execute("UPDATE produtos SET quantidade = ? WHERE id = ?", (new_stock, id_item))
            self.conn.commit()
            if new_stock == 0: self.add_notification(f"ESTOQUE ZERADO: O produto '{produto[0]}' está esgotado.")
            elif produto[2] > 0 and (new_stock / produto[2]) * 100 < 30: self.add_notification(f"ESTOQUE BAIXO: O produto '{produto[0]}' está com menos de 30% do estoque inicial.")
            return "Sucesso"
        except sqlite3.Error as e:
            self.conn.rollback(); return f"Erro: {e}"

    def reverse_movement(self, movement_id):
        try:
            self.conn.execute("BEGIN TRANSACTION")
            mov = self.fetch_one("SELECT id_item, tipo, quantidade FROM movimentacoes WHERE id = ?", (movement_id,))
            if not mov:
                self.conn.rollback(); return "Movimentação não encontrada."
            id_item, tipo, quantidade = mov
            if tipo.lower() == 'entrada':
                self.cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (quantidade, id_item))
            elif tipo.lower() == 'saida':
                self.cursor.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", (quantidade, id_item))
            self.cursor.execute("DELETE FROM movimentacoes WHERE id = ?", (movement_id,))
            self.conn.commit()
            return "Sucesso"
        except sqlite3.Error as e:
            self.conn.rollback(); return f"Erro ao reverter: {e}"

    def add_notification(self, message):
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.execute_query("INSERT INTO notificacoes (mensagem, data_hora) VALUES (?, ?)", (message, data_hora))
    def get_all_notifications(self):
        return self.fetch_all("SELECT id, mensagem, data_hora, status FROM notificacoes ORDER BY data_hora DESC")
    def get_unread_notification_count(self):
        return self.fetch_one("SELECT COUNT(*) FROM notificacoes WHERE status = 'não lida'")[0]
    def mark_notification_as_read(self, notif_id):
        self.execute_query("UPDATE notificacoes SET status = 'lida' WHERE id = ?", (notif_id,))
    def clear_read_notifications(self):
        self.execute_query("DELETE FROM notificacoes WHERE status = 'lida'")
    def get_inactive_products(self, days_inactive):
        limit_date = (datetime.now() - timedelta(days=days_inactive)).strftime('%Y-%m-%d %H:%M:%S')
        query = """
        SELECT p.id, p.nome FROM produtos p
        WHERE NOT EXISTS (SELECT 1 FROM notificacoes n WHERE n.mensagem LIKE '%' || p.nome || '%inativ%')
        AND (SELECT MAX(m.data_hora) FROM movimentacoes m WHERE m.id_item = p.id) < ?
        """
        return self.fetch_all(query, (limit_date,))
    def get_product_financials(self, product_id):
        query = """
        SELECT
            (SELECT SUM(preco_transacao * quantidade) FROM movimentacoes WHERE id_item = ? AND tipo = 'entrada'),
            (SELECT SUM(preco_transacao * quantidade) FROM movimentacoes WHERE id_item = ? AND tipo = 'saida'),
            (SELECT SUM(quantidade) FROM movimentacoes WHERE id_item = ? AND tipo = 'saida')
        """
        return self.fetch_one(query, (product_id, product_id, product_id))
    def get_all_movements(self):
        query = """
        SELECT m.id, p.nome, u.nome_usuario, m.tipo, m.quantidade, m.preco_transacao, 
               COALESCE(c.nome, f.nome, 'N/A') as origem_destino, m.data_hora
        FROM movimentacoes m 
        JOIN produtos p ON m.id_item = p.id 
        LEFT JOIN usuarios u ON m.id_usuario = u.id
        LEFT JOIN clientes c ON m.id_cliente = c.id
        LEFT JOIN fornecedores f ON m.id_fornecedor = f.id
        ORDER BY m.data_hora DESC
        """
        return self.fetch_all(query)
    def get_summary_for_all_products(self):
        query = """
        SELECT
            strftime('%Y-%m-%d', m.data_hora) as dia, m.id_item, p.nome,
            SUM(CASE WHEN m.tipo = 'entrada' THEN m.quantidade * m.preco_transacao ELSE 0 END) as valor_entrada,
            SUM(CASE WHEN m.tipo = 'saida' THEN m.quantidade * m.preco_transacao ELSE 0 END) as valor_saida,
            SUM(CASE WHEN m.tipo = 'entrada' THEN m.quantidade ELSE 0 END) as qtd_entrada,
            SUM(CASE WHEN m.tipo = 'saida' THEN m.quantidade ELSE 0 END) as qtd_saida
        FROM movimentacoes m JOIN produtos p ON m.id_item = p.id
        GROUP BY dia, m.id_item ORDER BY dia ASC, p.nome ASC LIMIT 300;
        """
        return self.fetch_all(query)
    def get_summary_for_single_product(self, product_id):
        query = """
        SELECT
            strftime('%Y-%m-%d', data_hora) as dia,
            SUM(CASE WHEN tipo = 'entrada' THEN quantidade * preco_transacao ELSE 0 END) as valor_entrada,
            SUM(CASE WHEN tipo = 'saida' THEN quantidade * preco_transacao ELSE 0 END) as valor_saida,
            SUM(CASE WHEN tipo = 'entrada' THEN quantidade ELSE 0 END) as qtd_entrada,
            SUM(CASE WHEN tipo = 'saida' THEN quantidade ELSE 0 END) as qtd_saida
        FROM movimentacoes WHERE id_item = ?
        GROUP BY dia ORDER BY dia ASC LIMIT 30;
        """
        return self.fetch_all(query, (product_id,))
    def get_all_clients(self):
        return self.fetch_all("SELECT id, nome, cpf_cnpj, telefone, email, endereco FROM clientes ORDER BY nome")
    def add_client(self, nome, cpf_cnpj, tel, email, end):
        return self.execute_query("INSERT INTO clientes (nome, cpf_cnpj, telefone, email, endereco) VALUES (?, ?, ?, ?, ?)", (nome, cpf_cnpj, tel, email, end))
    def update_client(self, client_id, nome, cpf_cnpj, tel, email, end):
        return self.execute_query("UPDATE clientes SET nome=?, cpf_cnpj=?, telefone=?, email=?, endereco=? WHERE id=?", (nome, cpf_cnpj, tel, email, end, client_id))
    def delete_client(self, client_id):
        return self.execute_query("DELETE FROM clientes WHERE id = ?", (client_id,))
    def get_all_suppliers(self):
        return self.fetch_all("SELECT id, nome, contato, endereco FROM fornecedores ORDER BY nome")
    def add_supplier(self, nome, contato, endereco):
        return self.execute_query("INSERT INTO fornecedores (nome, contato, endereco) VALUES (?, ?, ?)", (nome, contato, endereco))
    def update_supplier(self, sup_id, nome, contato, endereco):
        return self.execute_query("UPDATE fornecedores SET nome=?, contato=?, endereco=? WHERE id=?", (nome, contato, endereco, sup_id))
    def delete_supplier(self, sup_id):
        return self.execute_query("DELETE FROM fornecedores WHERE id = ?", (sup_id,))
    def close(self):
        self.conn.close()