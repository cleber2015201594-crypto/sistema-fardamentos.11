import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import sqlite3
import time

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO - SQLITE
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Estabelece conexão com SQLite"""
    try:
        conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco SQLite com todas as tabelas necessárias"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome_completo TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de escolas
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            # Tabela de clientes
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Tabela de produtos - COM PREÇO DE CUSTO
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco_custo REAL DEFAULT 0,
                    preco_venda REAL,
                    estoque INTEGER DEFAULT 0,
                    estoque_minimo INTEGER DEFAULT 5,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER REFERENCES clientes(id),
                    escola_id INTEGER REFERENCES escolas(id),
                    status TEXT DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    forma_pagamento TEXT DEFAULT 'Dinheiro',
                    quantidade_total INTEGER,
                    valor_total REAL,
                    observacoes TEXT,
                    cupom_desconto TEXT,
                    valor_desconto REAL DEFAULT 0
                )
            ''')
            
            # Tabela de itens do pedido
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario REAL,
                    subtotal REAL
                )
            ''')
            
            # Tabela de cupons de desconto
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    desconto_percentual REAL,
                    desconto_fixo REAL,
                    valido_ate DATE,
                    usos_maximos INTEGER DEFAULT 1,
                    usos_atuais INTEGER DEFAULT 0,
                    ativo BOOLEAN DEFAULT 1
                )
            ''')
            
            # Tabela de templates de pedidos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS templates_pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    escola_id INTEGER REFERENCES escolas(id),
                    itens TEXT,  -- JSON com os itens do template
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor'),
                ('gerente', make_hashes('Gerente@123'), 'Gerente', 'gerente')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
                    cur.execute('''
                        INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (?, ?, ?, ?)
                    ''', (username, password_hash, nome, tipo))
                except Exception as e:
                    pass
            
            # Inserir escolas padrão
            escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
            for escola in escolas_padrao:
                try:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except Exception as e:
                    pass
            
            # Inserir cupons padrão
            cupons_padrao = [
                ('ESCOLA10', 10.0, 0.0, '2024-12-31', 100),
                ('PRIMEIRACOMPRA', 15.0, 0.0, '2024-12-31', 50),
                ('FRETE100', 0.0, 10.0, '2024-12-31', 100)
            ]
            
            for codigo, perc, fixo, valido, usos in cupons_padrao:
                try:
                    cur.execute('''
                        INSERT OR IGNORE INTO cupons (codigo, desconto_percentual, desconto_fixo, valido_ate, usos_maximos)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (codigo, perc, fixo, valido, usos))
                except Exception as e:
                    pass
            
            conn.commit()
            
        except Exception as e:
            st.error(f"Erro ao inicializar banco: {str(e)}")
        finally:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios 
            WHERE username = ? AND ativo = 1
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]  # sucesso, nome, tipo
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def alterar_senha(username, senha_atual, nova_senha):
    """Altera a senha do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar senha atual
        cur.execute('SELECT password_hash FROM usuarios WHERE username = ?', (username,))
        resultado = cur.fetchone()
        
        if not resultado or not check_hashes(senha_atual, resultado[0]):
            return False, "Senha atual incorreta"
        
        # Atualizar senha
        nova_senha_hash = make_hashes(nova_senha)
        cur.execute(
            'UPDATE usuarios SET password_hash = ? WHERE username = ?',
            (nova_senha_hash, username)
        )
        conn.commit()
        return True, "Senha alterada com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_usuarios():
    """Lista todos os usuários (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, username, nome_completo, tipo, ativo, data_criacao 
            FROM usuarios 
            ORDER BY username
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar usuários: {e}")
        return []
    finally:
        conn.close()

def criar_usuario(username, password, nome_completo, tipo):
    """Cria novo usuário (apenas para admin)"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        password_hash = make_hashes(password)
        
        cur.execute('''
            INSERT INTO usuarios (username, password_hash, nome_completo, tipo)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, nome_completo, tipo))
        
        conn.commit()
        return True, "Usuário criado com sucesso!"
        
    except sqlite3.IntegrityError:
        return False, "Username já existe"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem, tipo_usuario = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.session_state.tipo_usuario = tipo_usuario
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# Inicializar banco na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🚀 SISTEMA PRINCIPAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONFIGURAÇÕES ESPECÍFICAS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS - SQLITE
# =========================================

# FUNÇÕES PARA ESCOLAS
def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        conn.close()

def obter_escola_por_id(escola_id):
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas WHERE id = ?", (escola_id,))
        return cur.fetchone()
    except Exception as e:
        st.error(f"Erro ao obter escola: {e}")
        return None
    finally:
        conn.close()

# FUNÇÕES PARA CLIENTES
def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (?, ?, ?, ?)",
            (nome, telefone, email, data_cadastro)
        )
        
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar clientes: {e}")
        return []
    finally:
        conn.close()

def excluir_cliente(cliente_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se tem pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = ?", (cliente_id,))
        if cur.fetchone()[0] > 0:
            return False, "Cliente possui pedidos e não pode ser excluído"
        
        cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        return True, "Cliente excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA PRODUTOS
def adicionar_produto(nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, estoque_minimo, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, estoque_minimo, descricao, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, estoque_minimo, descricao, escola_id))
        
        conn.commit()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.escola_id = ?
                ORDER BY p.categoria, p.nome
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                ORDER BY e.nome, p.categoria, p.nome
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def buscar_produtos(termo, escola_id=None):
    """Busca produtos por nome, categoria ou cor"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        termo = f"%{termo}%"
        
        if escola_id:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE (p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ?)
                AND p.escola_id = ?
                ORDER BY p.nome
            ''', (termo, termo, termo, escola_id))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ?
                ORDER BY p.nome
            ''', (termo, termo, termo))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []
    finally:
        conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🏭 SISTEMA DE ESTOQUE PARA FÁBRICA
# =========================================

def mover_para_producao(pedido_id):
    """Move pedido para produção sem consumir estoque"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Apenas atualiza status para "Em produção"
        cur.execute('''
            UPDATE pedidos 
            SET status = 'Em produção' 
            WHERE id = ?
        ''', (pedido_id,))
        
        conn.commit()
        return True, "Pedido movido para produção!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def finalizar_producao(pedido_id):
    """Finaliza produção e consome estoque"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Obter itens do pedido
        cur.execute('''
            SELECT produto_id, quantidade 
            FROM pedido_itens 
            WHERE pedido_id = ?
        ''', (pedido_id,))
        
        itens = cur.fetchall()
        
        # Verificar estoque disponível
        for produto_id, quantidade in itens:
            cur.execute("SELECT estoque FROM produtos WHERE id = ?", (produto_id,))
            estoque_atual = cur.fetchone()[0]
            
            if estoque_atual < quantidade:
                return False, f"Estoque insuficiente para o produto ID {produto_id}"
        
        # Consumir estoque
        for produto_id, quantidade in itens:
            cur.execute('''
                UPDATE produtos 
                SET estoque = estoque - ? 
                WHERE id = ?
            ''', (quantidade, produto_id))
        
        # Atualizar status do pedido
        cur.execute('''
            UPDATE pedidos 
            SET status = 'Pronto para entrega' 
            WHERE id = ?
        ''', (pedido_id,))
        
        conn.commit()
        return True, "Produção finalizada! Estoque consumido."
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÕES PARA PEDIDOS - VERSÃO FÁBRICA
def adicionar_pedido_fabrica(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes, cupom_desconto=None):
    """Versão para fábrica - não consome estoque automaticamente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        # Aplicar desconto se houver cupom
        valor_desconto = 0
        if cupom_desconto:
            cupom = verificar_cupom(cupom_desconto)
            if cupom:
                if cupom['desconto_percentual'] > 0:
                    valor_desconto = valor_total * (cupom['desconto_percentual'] / 100)
                else:
                    valor_desconto = cupom['desconto_fixo']
                
                valor_total -= valor_desconto
                # Registrar uso do cupom
                cur.execute('UPDATE cupons SET usos_atuais = usos_atuais + 1 WHERE codigo = ?', (cupom_desconto,))
        
        # Status inicial para fábrica
        status_inicial = "Pendente"
        
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, 
                               quantidade_total, valor_total, observacoes, status, cupom_desconto, valor_desconto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes, status_inicial, cupom_desconto, valor_desconto))
        
        pedido_id = cur.lastrowid
        
        # Adicionar itens do pedido (SEM consumir estoque)
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_pedidos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.escola_id = ?
                ORDER BY p.data_pedido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                ORDER BY p.data_pedido DESC
            ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar pedidos: {e}")
        return []
    finally:
        conn.close()

def atualizar_status_pedido(pedido_id, novo_status):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            cur.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega, pedido_id))
        else:
            cur.execute('''
                UPDATE pedidos 
                SET status = ? 
                WHERE id = ?
            ''', (novo_status, pedido_id))
        
        conn.commit()
        return True, "Status do pedido atualizado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Excluir pedido (não precisa restaurar estoque pois fábrica não consome automaticamente)
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 🎫 SISTEMA DE CUPONS
# =========================================

def verificar_cupom(codigo):
    """Verifica se um cupom é válido"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM cupons 
            WHERE codigo = ? AND ativo = 1 AND valido_ate >= DATE('now') AND usos_atuais < usos_maximos
        ''', (codigo,))
        
        resultado = cur.fetchone()
        return dict(resultado) if resultado else None
        
    except Exception as e:
        return None
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES PARA RELATÓRIOS - SQLITE
# =========================================

def gerar_relatorio_vendas_por_escola(escola_id=None, data_inicio=None, data_fim=None):
    """Gera relatório de vendas por período e escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        query = '''
            SELECT 
                DATE(p.data_pedido) as data,
                e.nome as escola,
                COUNT(*) as total_pedidos,
                SUM(p.quantidade_total) as total_itens,
                SUM(p.valor_total) as total_vendas,
                SUM(p.valor_desconto) as total_descontos,
                GROUP_CONCAT(DISTINCT p.forma_pagamento) as formas_pagamento
            FROM pedidos p
            JOIN escolas e ON p.escola_id = e.id
            WHERE p.status = 'Entregue'
        '''
        params = []
        
        if escola_id:
            query += ' AND p.escola_id = ?'
            params.append(escola_id)
        
        if data_inicio and data_fim:
            query += ' AND DATE(p.data_pedido) BETWEEN ? AND ?'
            params.extend([data_inicio, data_fim])
        
        query += ' GROUP BY DATE(p.data_pedido), e.nome ORDER BY data DESC'
        
        cur.execute(query, params)
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)', 'Total Descontos (R$)', 'Formas Pagamento'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_produtos_por_escola(escola_id=None):
    """Gera relatório de produtos mais vendidos por escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado,
                    AVG(pr.preco_custo) as custo_medio,
                    (SUM(pi.subtotal) - SUM(pi.quantidade * pr.preco_custo)) as lucro_total
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                WHERE p.escola_id = ? AND p.status = 'Entregue'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor
                ORDER BY total_vendido DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    pr.nome as produto,
                    pr.categoria,
                    pr.tamanho,
                    pr.cor,
                    e.nome as escola,
                    SUM(pi.quantidade) as total_vendido,
                    SUM(pi.subtotal) as total_faturado,
                    AVG(pr.preco_custo) as custo_medio,
                    (SUM(pi.subtotal) - SUM(pi.quantidade * pr.preco_custo)) as lucro_total
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                JOIN pedidos p ON pi.pedido_id = p.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.status = 'Entregue'
                GROUP BY pr.id, pr.nome, pr.categoria, pr.tamanho, pr.cor, e.nome
                ORDER BY total_vendido DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Total Vendido', 'Total Faturado (R$)', 'Custo Médio (R$)', 'Lucro Total (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Escola', 'Total Vendido', 'Total Faturado (R$)', 'Custo Médio (R$)', 'Lucro Total (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_fechamento(data_inicio, data_fim, escola_id=None):
    """Gera relatório completo de fechamento"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        # Relatório principal
        query = '''
            SELECT 
                DATE(p.data_pedido) as data,
                e.nome as escola,
                COUNT(*) as total_pedidos,
                SUM(p.quantidade_total) as total_itens,
                SUM(p.valor_total) as total_vendas,
                SUM(p.valor_desconto) as total_descontos,
                p.forma_pagamento,
                COUNT(*) as pedidos_forma_pagamento
            FROM pedidos p
            JOIN escolas e ON p.escola_id = e.id
            WHERE p.status = 'Entregue' AND DATE(p.data_pedido) BETWEEN ? AND ?
        '''
        params = [data_inicio, data_fim]
        
        if escola_id:
            query += ' AND p.escola_id = ?'
            params.append(escola_id)
        
        query += ' GROUP BY DATE(p.data_pedido), e.nome, p.forma_pagamento ORDER BY data DESC'
        
        cur.execute(query, params)
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)', 'Total Descontos (R$)', 'Forma Pagamento', 'Pedidos por Forma'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🔔 SISTEMA DE NOTIFICAÇÕES
# =========================================

def verificar_notificacoes():
    """Verifica alertas e notificações"""
    notificacoes = []
    
    # Verificar estoque baixo
    produtos = listar_produtos_por_escola()
    for produto in produtos:
        if produto[7] <= produto[8]:  # estoque <= estoque_minimo
            notificacoes.append(f"⚠️ Estoque baixo: {produto[1]} - {produto[3]} ({produto[7]} unidades)")
    
    # Verificar pedidos pendentes
    pedidos = listar_pedidos_por_escola()
    pedidos_pendentes = len([p for p in pedidos if p[3] in ['Pendente', 'Em produção']])
    if pedidos_pendentes > 0:
        notificacoes.append(f"📦 {pedidos_pendentes} pedidos pendentes/produção")
    
    return notificacoes

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Menu de gerenciamento de usuários (apenas para admin)
if st.session_state.tipo_usuario == 'admin':
    with st.sidebar.expander("👥 Gerenciar Usuários"):
        st.subheader("Novo Usuário")
        with st.form("novo_usuario"):
            novo_username = st.text_input("Username")
            nova_senha = st.text_input("Senha", type='password')
            nome_completo = st.text_input("Nome Completo")
            tipo = st.selectbox("Tipo", ["admin", "gerente", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if novo_username and nova_senha and nome_completo:
                    sucesso, msg = criar_usuario(novo_username, nova_senha, nome_completo, tipo)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
        
        st.subheader("Usuários do Sistema")
        usuarios = listar_usuarios()
        if usuarios:
            for usuario in usuarios:
                status = "✅ Ativo" if usuario[4] == 1 else "❌ Inativo"
                st.write(f"**{usuario[1]}** - {usuario[2]} ({usuario[3]}) - {status}")

# Menu de alteração de senha
with st.sidebar.expander("🔐 Alterar Senha"):
    with st.form("alterar_senha"):
        senha_atual = st.text_input("Senha Atual", type='password')
        nova_senha1 = st.text_input("Nova Senha", type='password')
        nova_senha2 = st.text_input("Confirmar Nova Senha", type='password')
        
        if st.form_submit_button("Alterar Senha"):
            if senha_atual and nova_senha1 and nova_senha2:
                if nova_senha1 == nova_senha2:
                    sucesso, msg = alterar_senha(st.session_state.username, senha_atual, nova_senha1)
                    if sucesso:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("As novas senhas não coincidem")
            else:
                st.error("Preencha todos os campos")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.nome_usuario = None
    st.session_state.tipo_usuario = None
    st.rerun()

# Menu principal - ORGANIZADO POR ESCOLA
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Sistema de notificações
notificacoes = verificar_notificacoes()
if notificacoes:
    with st.sidebar.expander(f"🔔 Notificações ({len(notificacoes)})", expanded=True):
        for notif in notificacoes:
            st.warning(notif)

# Header dinâmico
if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Visão Geral")
elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos") 
elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
elif menu == "👕 Produtos":
    st.title("👕 Gestão de Produtos")
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")

st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Métricas em Tempo Real")
    
    # Carregar dados
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pedidos = 0
        for escola in escolas:
            pedidos = listar_pedidos_por_escola(escola[0])
            total_pedidos += len(pedidos)
        st.metric("Total de Pedidos", total_pedidos)
    
    with col2:
        pedidos_pendentes = 0
        for escola in escolas:
            pedidos = listar_pedidos_por_escola(escola[0])
            pedidos_pendentes += len([p for p in pedidos if p[3] in ['Pendente', 'Em produção']])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes))
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            produtos_baixo_estoque += len([p for p in produtos if p[7] <= p[8]])
        st.metric("Alertas de Estoque", produtos_baixo_estoque, delta=-produtos_baixo_estoque)
    
    # Métricas por Escola
    st.header("🏫 Métricas por Escola")
    escolas_cols = st.columns(len(escolas))
    
    for idx, escola in enumerate(escolas):
        with escolas_cols[idx]:
            st.subheader(escola[1])
            
            # Pedidos da escola
            pedidos_escola = listar_pedidos_por_escola(escola[0])
            pedidos_pendentes_escola = len([p for p in pedidos_escola if p[3] in ['Pendente', 'Em produção']])
            
            # Produtos da escola
            produtos_escola = listar_produtos_por_escola(escola[0])
            produtos_baixo_estoque_escola = len([p for p in produtos_escola if p[7] <= p[8]])
            
            st.metric("Pedidos", len(pedidos_escola))
            st.metric("Pendentes", pedidos_pendentes_escola)
            st.metric("Produtos", len(produtos_escola))
            st.metric("Alerta Estoque", produtos_baixo_estoque_escola)
    
    # Ações Rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col3:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        nome = st.text_input("👤 Nome completo*")
        telefone = st.text_input("📞 Telefone")
        email = st.text_input("📧 Email")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome:
                sucesso, msg = adicionar_cliente(nome, telefone, email)
                if sucesso:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
            else:
                st.error("❌ Nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Data Cadastro': cliente[4]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("👥 Nenhum cliente cadastrado")
    
    with tab3:
        st.header("🗑️ Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para excluir:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                st.warning("⚠️ Esta ação não pode ser desfeita!")
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    sucesso, msg = excluir_cliente(cliente_id)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("👥 Nenhum cliente cadastrado")

elif menu == "👕 Produtos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    # Seleção da escola
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e[1] for e in escolas],
        key="produtos_escola"
    )
    
    escola_id = next(e[0] for e in escolas if e[1] == escola_selecionada_nome)
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Produto", "📋 Produtos da Escola", "🔍 Buscar Produtos"])
    
    with tab1:
        st.header(f"➕ Novo Produto - {escola_selecionada_nome}")
        
        with st.form("novo_produto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("📝 Nome do produto*", placeholder="Ex: Camiseta Básica")
                categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
                cor = st.text_input("🎨 Cor*", value="Branco", placeholder="Ex: Azul Marinho")
            
            with col2:
                preco_custo = st.number_input("💰 Preço de Custo (R$)", min_value=0.0, value=15.0, step=0.01)
                preco_venda = st.number_input("💰 Preço de Venda (R$)*", min_value=0.0, value=29.90, step=0.01)
                estoque = st.number_input("📦 Estoque inicial*", min_value=0, value=10)
                estoque_minimo = st.number_input("📊 Estoque mínimo*", min_value=0, value=5)
                descricao = st.text_area("📄 Descrição", placeholder="Detalhes do produto...")
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                if nome and cor and preco_venda > 0:
                    # Calcular margem de lucro
                    margem = ((preco_venda - preco_custo) / preco_custo * 100) if preco_custo > 0 else 0
                    
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco_custo, preco_venda, estoque, estoque_minimo, descricao, escola_id)
                    if sucesso:
                        st.success(f"{msg} Margem: {margem:.1f}%")
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome, Cor e Preço de Venda")
    
    with tab2:
        st.header(f"📋 Produtos - {escola_selecionada_nome}")
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            # Métricas rápidas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_produtos = len(produtos)
                st.metric("Total de Produtos", total_produtos)
            with col2:
                total_estoque = sum(p[7] for p in produtos)
                st.metric("Estoque Total", total_estoque)
            with col3:
                total_investimento = sum(p[7] * p[5] for p in produtos)  # estoque * preço_custo
                st.metric("Investimento Estoque", f"R$ {total_investimento:.2f}")
            with col4:
                baixo_estoque = len([p for p in produtos if p[7] <= p[8]])
                st.metric("Produtos com Estoque Baixo", baixo_estoque)
            
            # Tabela de produtos
            dados = []
            for produto in produtos:
                status_estoque = "✅" if produto[7] > produto[8] else "⚠️" if produto[7] > 0 else "❌"
                margem = ((produto[6] - produto[5]) / produto[5] * 100) if produto[5] > 0 else 0
                
                dados.append({
                    'ID': produto[0],
                    'Produto': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Custo': f"R$ {produto[5]:.2f}",
                    'Venda': f"R$ {produto[6]:.2f}",
                    'Margem': f"{margem:.1f}%",
                    'Estoque': f"{status_estoque} {produto[7]}",
                    'Estoque Min': produto[8],
                    'Descrição': produto[9] or 'N/A'
                })
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.info(f"👕 Nenhum produto cadastrado para {escola_selecionada_nome}")
    
    with tab3:
        st.header("🔍 Buscar Produtos")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            termo_busca = st.text_input("Digite o termo de busca:", placeholder="Nome, categoria ou cor...")
        with col2:
            buscar_todas = st.checkbox("Todas escolas", value=True)
        
        if termo_busca:
            if buscar_todas:
                resultados = buscar_produtos(termo_busca)
            else:
                resultados = buscar_produtos(termo_busca, escola_id)
            
            if resultados:
                st.success(f"🔍 {len(resultados)} produto(s) encontrado(s)")
                
                dados = []
                for produto in resultados:
                    status_estoque = "✅" if produto[7] > produto[8] else "⚠️" if produto[7] > 0 else "❌"
                    
                    dados.append({
                        'ID': produto[0],
                        'Produto': produto[1],
                        'Categoria': produto[2],
                        'Tamanho': produto[3],
                        'Cor': produto[4],
                        'Preço': f"R$ {produto[6]:.2f}",
                        'Estoque': f"{status_estoque} {produto[7]}",
                        'Escola': produto[11]
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("🔍 Nenhum produto encontrado")
        else:
            st.info("🔍 Digite um termo para buscar")

elif menu == "📦 Estoque":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    # Abas por escola
    tabs = st.tabs([f"🏫 {e[1]}" for e in escolas])
    
    for idx, escola in enumerate(escolas):
        with tabs[idx]:
            st.header(f"📦 Controle de Estoque - {escola[1]}")
            
            produtos = listar_produtos_por_escola(escola[0])
            
            if produtos:
                # Métricas da escola
                col1, col2, col3, col4 = st.columns(4)
                total_produtos = len(produtos)
                total_estoque = sum(p[7] for p in produtos)
                produtos_baixo_estoque = len([p for p in produtos if p[7] <= p[8]])
                produtos_sem_estoque = len([p for p in produtos if p[7] == 0])
                
                with col1:
                    st.metric("Total Produtos", total_produtos)
                with col2:
                    st.metric("Estoque Total", total_estoque)
                with col3:
                    st.metric("Estoque Baixo", produtos_baixo_estoque)
                with col4:
                    st.metric("Sem Estoque", produtos_sem_estoque)
                
                # Tabela interativa de estoque
                st.subheader("📋 Ajuste de Estoque")
                
                for produto in produtos:
                    with st.expander(f"{produto[1]} - {produto[3]} - {produto[4]} (Estoque: {produto[7]})"):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**Categoria:** {produto[2]}")
                            st.write(f"**Preço Custo:** R$ {produto[5]:.2f}")
                            st.write(f"**Preço Venda:** R$ {produto[6]:.2f}")
                            if produto[9]:
                                st.write(f"**Descrição:** {produto[9]}")
                        
                        with col2:
                            nova_quantidade = st.number_input(
                                "Nova quantidade",
                                min_value=0,
                                value=produto[7],
                                key=f"estoque_{produto[0]}_{idx}"
                            )
                        
                        with col3:
                            if st.button("💾 Atualizar", key=f"btn_{produto[0]}_{idx}"):
                                if nova_quantidade != produto[7]:
                                    sucesso, msg = atualizar_estoque(produto[0], nova_quantidade)
                                    if sucesso:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                                else:
                                    st.info("Quantidade não foi alterada")
                
                # Alertas de estoque baixo
                produtos_alerta = [p for p in produtos if p[7] <= p[8]]
                if produtos_alerta:
                    st.subheader("🚨 Alertas de Estoque Baixo")
                    for produto in produtos_alerta:
                        st.warning(f"**{produto[1]} - {produto[3]} - {produto[4]}**: Apenas {produto[7]} unidades em estoque (mínimo: {produto[8]})")
            
            else:
                st.info(f"👕 Nenhum produto cadastrado para {escola[1]}")

elif menu == "📦 Pedidos":
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada. Configure as escolas primeiro.")
        st.stop()
    
    # Abas principais
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Novo Pedido", "📋 Todos os Pedidos", "🔄 Gerenciar Pedidos", "🏭 Controle Produção"])
    
    with tab1:
        st.header("➕ Novo Pedido")
        
        # Seleção da escola para o pedido
        escola_pedido_nome = st.selectbox(
            "🏫 Escola do Pedido:",
            [e[1] for e in escolas],
            key="pedido_escola"
        )
        escola_pedido_id = next(e[0] for e in escolas if e[1] == escola_pedido_nome)
        
        # Selecionar cliente
        clientes = listar_clientes()
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado. Cadastre clientes primeiro.")
        else:
            cliente_selecionado = st.selectbox(
                "👤 Selecione o cliente:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                # Produtos da escola selecionada
                produtos = listar_produtos_por_escola(escola_pedido_id)
                
                if produtos:
                    st.subheader(f"🛒 Produtos Disponíveis - {escola_pedido_nome}")
                    
                    # Sistema de cupom
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        cupom = st.text_input("🎫 Cupom de desconto (opcional):", placeholder="Ex: ESCOLA10")
                    with col2:
                        if cupom:
                            cupom_info = verificar_cupom(cupom)
                            if cupom_info:
                                if cupom_info['desconto_percentual'] > 0:
                                    st.success(f"✅ Cupom válido! {cupom_info['desconto_percentual']}% de desconto")
                                else:
                                    st.success(f"✅ Cupom válido! R$ {cupom_info['desconto_fixo']} de desconto")
                            else:
                                st.error("❌ Cupom inválido ou expirado")
                    
                    # Interface para adicionar itens
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        produto_selecionado = st.selectbox(
                            "Produto:",
                            [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[7]} - R$ {p[6]:.2f}" for p in produtos],
                            key="produto_pedido"
                        )
                    with col2:
                        quantidade = st.number_input("Quantidade", min_value=1, value=1, key="qtd_pedido")
                    with col3:
                        if st.button("➕ Adicionar Item", use_container_width=True):
                            if 'itens_pedido' not in st.session_state:
                                st.session_state.itens_pedido = []
                            
                            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[7]} - R$ {p[6]:.2f}" == produto_selecionado)
                            produto = next(p for p in produtos if p[0] == produto_id)
                            
                            # Verificar se produto já está no pedido
                            item_existente = next((i for i in st.session_state.itens_pedido if i['produto_id'] == produto_id), None)
                            
                            if item_existente:
                                item_existente['quantidade'] += quantidade
                                item_existente['subtotal'] = item_existente['quantidade'] * item_existente['preco_unitario']
                            else:
                                item = {
                                    'produto_id': produto_id,
                                    'nome': produto[1],
                                    'tamanho': produto[3],
                                    'cor': produto[4],
                                    'quantidade': quantidade,
                                    'preco_unitario': float(produto[6]),
                                    'subtotal': float(produto[6]) * quantidade
                                }
                                st.session_state.itens_pedido.append(item)
                            
                            st.success("✅ Item adicionado!")
                            st.rerun()
                    
                    # Mostrar itens adicionados
                    if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
                        st.subheader("📋 Itens do Pedido")
                        total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
                        
                        # Aplicar desconto do cupom
                        valor_final = total_pedido
                        if cupom:
                            cupom_info = verificar_cupom(cupom)
                            if cupom_info:
                                if cupom_info['desconto_percentual'] > 0:
                                    valor_final = total_pedido * (1 - cupom_info['desconto_percentual'] / 100)
                                else:
                                    valor_final = total_pedido - cupom_info['desconto_fixo']
                        
                        for i, item in enumerate(st.session_state.itens_pedido):
                            col1, col2, col3, col4, col5 = st.columns([3,1,1,1,1])
                            with col1:
                                st.write(f"**{item['nome']}**")
                                st.write(f"Tamanho: {item['tamanho']} | Cor: {item['cor']}")
                            with col2:
                                st.write(f"Qtd: {item['quantidade']}")
                            with col3:
                                st.write(f"R$ {item['preco_unitario']:.2f}")
                            with col4:
                                st.write(f"R$ {item['subtotal']:.2f}")
                            with col5:
                                if st.button("❌ Remover", key=f"del_{i}"):
                                    st.session_state.itens_pedido.pop(i)
                                    st.rerun()
                        
                        st.success(f"**💰 Total do Pedido: R$ {total_pedido:.2f}**")
                        if cupom and cupom_info:
                            st.info(f"**🎫 Com desconto: R$ {valor_final:.2f}** (Economia: R$ {total_pedido - valor_final:.2f})")
                        
                        # Informações adicionais do pedido
                        col1, col2 = st.columns(2)
                        with col1:
                            data_entrega = st.date_input("📅 Data de Entrega Prevista", min_value=date.today())
                            forma_pagamento = st.selectbox(
                                "💳 Forma de Pagamento",
                                ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência"]
                            )
                        with col2:
                            observacoes = st.text_area("📝 Observações")
                        
                        if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                            if st.session_state.itens_pedido:
                                sucesso, resultado = adicionar_pedido_fabrica(
                                    cliente_id, 
                                    escola_pedido_id,
                                    st.session_state.itens_pedido, 
                                    data_entrega, 
                                    forma_pagamento,
                                    observacoes,
                                    cupom if cupom and verificar_cupom(cupom) else None
                                )
                                if sucesso:
                                    st.success(f"✅ Pedido #{resultado} criado com sucesso para {escola_pedido_nome}!")
