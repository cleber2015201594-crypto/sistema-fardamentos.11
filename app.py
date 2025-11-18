import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import hashlib
import sqlite3
import os
import time

# =========================================
# 🚀 CONFIGURAÇÃO PARA SERVIDOR
# =========================================

def is_render_environment():
    """Detecta se está rodando no Render"""
    return 'RENDER' in os.environ or 'DATABASE_URL' in os.environ

def get_database_config():
    """Retorna configuração do banco baseada no ambiente"""
    if is_render_environment():
        return {
            'type': 'postgresql',
            'url': os.environ.get('DATABASE_URL'),
            'engine': 'psycopg2'
        }
    else:
        return {
            'type': 'sqlite', 
            'url': 'fardamentos.db',
            'engine': 'sqlite3'
        }

# Configuração inicial
DB_CONFIG = get_database_config()
IS_RENDER = is_render_environment()

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Estabelece conexão com o banco - Adaptado para servidor"""
    try:
        if IS_RENDER and DB_CONFIG['type'] == 'postgresql':
            import psycopg2
            from urllib.parse import urlparse
            
            url = urlparse(DB_CONFIG['url'])
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port,
                sslmode='require'
            )
            return conn
        else:
            conn = sqlite3.connect(DB_CONFIG['url'], check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {str(e)}")
        return None

def init_db():
    """Inicializa o banco - Adaptado para PostgreSQL no Render"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        if IS_RENDER:
            # PostgreSQL para Render
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    nome_completo VARCHAR(100),
                    tipo VARCHAR(20) DEFAULT 'vendedor',
                    ativo BOOLEAN DEFAULT true,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) UNIQUE NOT NULL
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    telefone VARCHAR(20),
                    email VARCHAR(100),
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    categoria VARCHAR(50),
                    tamanho VARCHAR(10),
                    cor VARCHAR(50),
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    estoque_reservado INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedidos (
                    id SERIAL PRIMARY KEY,
                    cliente_id INTEGER REFERENCES clientes(id),
                    escola_id INTEGER REFERENCES escolas(id),
                    status VARCHAR(20) DEFAULT 'Pendente',
                    data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_entrega_prevista DATE,
                    data_entrega_real DATE,
                    forma_pagamento VARCHAR(50) DEFAULT 'Dinheiro',
                    quantidade_total INTEGER,
                    valor_total DECIMAL(10,2),
                    observacoes TEXT,
                    tipo_pedido VARCHAR(20) DEFAULT 'Venda'
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pedido_itens (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
                    produto_id INTEGER REFERENCES produtos(id),
                    quantidade INTEGER,
                    preco_unitario DECIMAL(10,2),
                    subtotal DECIMAL(10,2)
                )
            ''')
        else:
            # SQLite para ambiente local
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
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    estoque_reservado INTEGER DEFAULT 0,
                    descricao TEXT,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
                    tipo_pedido TEXT DEFAULT 'Venda'
                )
            ''')
            
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
        
        # Inserir usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
            ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            try:
                if IS_RENDER:
                    cur.execute('''
                        INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (username) DO NOTHING
                    ''', (username, password_hash, nome, tipo))
                else:
                    cur.execute('''
                        INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                        VALUES (?, ?, ?, ?)
                    ''', (username, password_hash, nome, tipo))
            except:
                pass
        
        # Inserir escolas padrão
        escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas_padrao:
            try:
                if IS_RENDER:
                    cur.execute('INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING', (escola,))
                else:
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
            except:
                pass
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        conn.close()

def verificar_login(username, password):
    """Verifica credenciais no banco de dados"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        
        if IS_RENDER:
            cur.execute('''
                SELECT password_hash, nome_completo, tipo 
                FROM usuarios 
                WHERE username = %s AND ativo = true
            ''', (username,))
        else:
            cur.execute('''
                SELECT password_hash, nome_completo, tipo 
                FROM usuarios 
                WHERE username = ? AND ativo = 1
            ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS
# =========================================

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

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_cadastro = datetime.now().strftime("%Y-%m-%d")
        
        if IS_RENDER:
            cur.execute(
                "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s)",
                (nome, telefone, email, data_cadastro)
            )
        else:
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

def listar_produtos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            if IS_RENDER:
                cur.execute('''
                    SELECT p.*, e.nome as escola_nome 
                    FROM produtos p 
                    LEFT JOIN escolas e ON p.escola_id = e.id 
                    WHERE p.escola_id = %s
                    ORDER BY p.categoria, p.nome
                ''', (escola_id,))
            else:
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

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        if IS_RENDER:
            cur.execute('''
                INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        else:
            cur.execute('''
                INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id))
        
        conn.commit()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        if IS_RENDER:
            cur.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (nova_quantidade, produto_id))
        else:
            cur.execute("UPDATE produtos SET estoque = ? WHERE id = ?", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes, tipo_pedido="Venda"):
    """Função CORRIGIDA para adicionar pedido com controle de estoque"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        # VERIFICAR ESTOQUE ANTES DE INSERIR
        for item in itens:
            produto_id = item['produto_id']
            quantidade = item['quantidade']
            
            if IS_RENDER:
                cur.execute("SELECT estoque, estoque_reservado FROM produtos WHERE id = %s", (produto_id,))
            else:
                cur.execute("SELECT estoque, estoque_reservado FROM produtos WHERE id = ?", (produto_id,))
                
            produto = cur.fetchone()
            
            if not produto:
                return False, f"Produto ID {produto_id} não encontrado"
            
            estoque_disponivel = produto[0]
            
            if tipo_pedido == "Venda" and quantidade > estoque_disponivel:
                return False, f"Estoque insuficiente para {item['nome']}. Disponível: {estoque_disponivel}"
        
        # INSERIR PEDIDO
        if IS_RENDER:
            cur.execute('''
                INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, 
                                   quantidade_total, valor_total, observacoes, tipo_pedido)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes, tipo_pedido))
            pedido_id = cur.fetchone()[0]
        else:
            cur.execute('''
                INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, 
                                   quantidade_total, valor_total, observacoes, tipo_pedido)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes, tipo_pedido))
            pedido_id = cur.lastrowid
        
        # INSERIR ITENS E ATUALIZAR ESTOQUE
        for item in itens:
            produto_id = item['produto_id']
            quantidade = item['quantidade']
            preco_unitario = item['preco_unitario']
            subtotal = item['subtotal']
            
            if IS_RENDER:
                cur.execute('''
                    INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (pedido_id, produto_id, quantidade, preco_unitario, subtotal))
                
                # ATUALIZAR ESTOQUE
                if tipo_pedido == "Venda":
                    cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id = %s", 
                               (quantidade, produto_id))
                else:
                    cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado + %s WHERE id = %s", 
                               (quantidade, produto_id))
            else:
                cur.execute('''
                    INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pedido_id, produto_id, quantidade, preco_unitario, subtotal))
                
                # ATUALIZAR ESTOQUE
                if tipo_pedido == "Venda":
                    cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                               (quantidade, produto_id))
                else:
                    cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado + ? WHERE id = ?", 
                               (quantidade, produto_id))
        
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
            if IS_RENDER:
                cur.execute('''
                    SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                    FROM pedidos p
                    JOIN clientes c ON p.cliente_id = c.id
                    JOIN escolas e ON p.escola_id = e.id
                    WHERE p.escola_id = %s
                    ORDER BY p.data_pedido DESC
                ''', (escola_id,))
            else:
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
        
        # Obter tipo do pedido
        if IS_RENDER:
            cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = %s', (pedido_id,))
        else:
            cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = ?', (pedido_id,))
            
        resultado = cur.fetchone()
        tipo_pedido = resultado[0] if resultado else "Venda"
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            if IS_RENDER:
                cur.execute('''
                    UPDATE pedidos 
                    SET status = %s, data_entrega_real = %s 
                    WHERE id = %s
                ''', (novo_status, data_entrega, pedido_id))
                
                # Se for pedido de produção, liberar estoque reservado
                if tipo_pedido == "Produção":
                    cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = %s', (pedido_id,))
                    itens = cur.fetchall()
                    
                    for produto_id, quantidade in itens:
                        cur.execute('''
                            UPDATE produtos 
                            SET estoque = estoque + %s, estoque_reservado = estoque_reservado - %s 
                            WHERE id = %s
                        ''', (quantidade, quantidade, produto_id))
            else:
                cur.execute('''
                    UPDATE pedidos 
                    SET status = ?, data_entrega_real = ? 
                    WHERE id = ?
                ''', (novo_status, data_entrega, pedido_id))
                
                # Se for pedido de produção, liberar estoque reservado
                if tipo_pedido == "Produção":
                    cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
                    itens = cur.fetchall()
                    
                    for produto_id, quantidade in itens:
                        cur.execute('''
                            UPDATE produtos 
                            SET estoque = estoque + ?, estoque_reservado = estoque_reservado - ? 
                            WHERE id = ?
                        ''', (quantidade, quantidade, produto_id))
                    
        else:
            if IS_RENDER:
                cur.execute('''
                    UPDATE pedidos 
                    SET status = %s 
                    WHERE id = %s
                ''', (novo_status, pedido_id))
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
        
        # Obter tipo do pedido e itens
        if IS_RENDER:
            cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = %s', (pedido_id,))
        else:
            cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = ?', (pedido_id,))
            
        resultado = cur.fetchone()
        tipo_pedido = resultado[0] if resultado else "Venda"
        
        if IS_RENDER:
            cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = %s', (pedido_id,))
        else:
            cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
            
        itens = cur.fetchall()
        
        # Restaurar estoque corretamente
        for produto_id, quantidade in itens:
            if tipo_pedido == "Venda":
                if IS_RENDER:
                    cur.execute("UPDATE produtos SET estoque = estoque + %s WHERE id = %s", (quantidade, produto_id))
                else:
                    cur.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))
            else:
                if IS_RENDER:
                    cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado - %s WHERE id = %s", (quantidade, produto_id))
                else:
                    cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado - ? WHERE id = ?", (quantidade, produto_id))
        
        # Excluir pedido
        if IS_RENDER:
            cur.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        else:
            cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
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

# =========================================
# 🚀 INICIALIZAÇÃO DO SISTEMA
# =========================================

# Configuração da página
st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar banco
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Verificar login
if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# CONFIGURAÇÕES
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# Sidebar
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Info ambiente
if IS_RENDER:
    st.sidebar.success("🌐 **Ambiente: Render**")
else:
    st.sidebar.info("💻 **Ambiente: Local**")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = [
    "📊 Dashboard por Escola", 
    "📦 Gestão de Pedidos",
    "👕 Produtos e Estoque",
    "👥 Clientes"
]
menu = st.sidebar.radio("Navegação", menu_options)

# Header
st.title("👕 Sistema de Fardamentos")
if IS_RENDER:
    st.success("🚀 **Sistema rodando na nuvem!**")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard por Escola":
    st.header("📊 Dashboard - Visão por Escola")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    # Seleção da escola
    escola_dashboard = st.selectbox(
        "🏫 Selecione a Escola para Visualizar:",
        [e[1] for e in escolas],
        key="dashboard_escola"
    )
    
    escola_id = next(e[0] for e in escolas if e[1] == escola_dashboard)
    
    # Métricas da escola
    pedidos_escola = listar_pedidos_por_escola(escola_id)
    produtos_escola = listar_produtos_por_escola(escola_id)
    
    total_pedidos = len(pedidos_escola)
    pedidos_pendentes = len([p for p in pedidos_escola if p[3] == 'Pendente'])
    pedidos_producao = len([p for p in pedidos_escola if p[3] == 'Em produção'])
    total_produtos = len(produtos_escola)
    alertas_estoque = len([p for p in produtos_escola if p[6] < 5])
    
    # Calcular vendas do mês
    mes_atual = datetime.now().strftime("%Y-%m")
    vendas_mes = sum(float(p[9]) for p in pedidos_escola 
                    if p[11] == 'Venda' and str(p[4]).startswith(mes_atual))
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Pedidos", total_pedidos)
        st.metric("⏳ Pendentes", pedidos_pendentes)
    
    with col2:
        st.metric("🏭 Em Produção", pedidos_producao)
        st.metric("👕 Total Produtos", total_produtos)
    
    with col3:
        st.metric("💰 Vendas do Mês", f"R$ {vendas_mes:,.2f}")
    
    with col4:
        st.metric("🚨 Alertas Estoque", alertas_estoque)
        if alertas_estoque > 0:
            st.error(f"⚠️ {alertas_estoque} produtos com estoque baixo")
    
    # Pedidos recentes
    st.subheader(f"📦 Pedidos Recentes - {escola_dashboard}")
    if pedidos_escola:
        dados = []
        for pedido in pedidos_escola[:10]:
            status_info = {
                'Pendente': '🟡 Pendente',
                'Em produção': '🟠 Em produção', 
                'Pronto para entrega': '🔵 Pronto',
                'Entregue': '🟢 Entregue',
                'Cancelado': '🔴 Cancelado'
            }.get(pedido[3], f'⚪ {pedido[3]}')
            
            tipo_info = "📦 Venda" if pedido[11] == "Venda" else "🏭 Produção"
            
            dados.append({
                'ID': pedido[0],
                'Tipo': tipo_info,
                'Cliente': pedido[11],
                'Status': status_info,
                'Data': pedido[4],
                'Valor': f"R$ {float(pedido[9]):.2f}"
            })
        
        st.dataframe(pd.DataFrame(dados), use_container_width=True)
    else:
        st.info(f"📦 Nenhum pedido para {escola_dashboard}")

elif menu == "📦 Gestão de Pedidos":
    st.header("📦 Gestão de Pedidos")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["➕ Novo Pedido", "📋 Todos os Pedidos", "🔄 Gerenciar Pedidos"])
    
    with tab1:
        st.subheader("➕ Novo Pedido")
        
        # Inicializar carrinho
        if 'carrinho_itens' not in st.session_state:
            st.session_state.carrinho_itens = []
        
        tipo_pedido = st.radio("📋 Tipo de Pedido:", ["Venda", "Produção"], horizontal=True, key="tipo_pedido")
        
        if tipo_pedido == "Produção":
            st.info("🏭 **Pedido de Produção**: Itens serão reservados e liberados quando finalizados")
        
        # Seleção da escola
        escola_pedido_nome = st.selectbox(
            "🏫 Escola do Pedido:",
            [e[1] for e in escolas],
            key="pedido_escola"
        )
        escola_pedido_id = next(e[0] for e in escolas if e[1] == escola_pedido_nome)
        
        # Selecionar cliente
        clientes = listar_clientes()
        if not clientes:
            st.error("❌ Nenhum cliente cadastrado.")
        else:
            cliente_selecionado = st.selectbox(
                "👤 Selecione o cliente:",
                [f"{c[1]} (ID: {c[0]})" for c in clientes],
                key="cliente_pedido"
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                # Produtos da escola
                produtos = listar_produtos_por_escola(escola_pedido_id)
                
                if produtos:
                    st.subheader(f"🛒 Produtos Disponíveis - {escola_pedido_nome}")
                    
                    # Adicionar item ao carrinho
                    with st.form("adicionar_item", clear_on_submit=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            produto_selecionado = st.selectbox(
                                "Selecione o produto:",
                                [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" for p in produtos],
                                key="produto_selecionado"
                            )
                        with col2:
                            quantidade = st.number_input("Quantidade:", min_value=1, value=1, key="quantidade_item")
                        with col3:
                            adicionar_submit = st.form_submit_button("➕ Adicionar", use_container_width=True)
                        
                        if adicionar_submit and produto_selecionado:
                            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" == produto_selecionado)
                            produto = next(p for p in produtos if p[0] == produto_id)
                            
                            # Verificar estoque
                            if tipo_pedido == "Venda" and quantidade > produto[6]:
                                st.error(f"❌ Estoque insuficiente! Disponível: {produto[6]} unidades")
                            else:
                                # Verificar se já está no carrinho
                                item_existente = next((i for i in st.session_state.carrinho_itens if i['produto_id'] == produto_id), None)
                                
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
                                        'preco_unitario': float(produto[5]),
                                        'subtotal': float(produto[5]) * quantidade
                                    }
                                    st.session_state.carrinho_itens.append(item)
                                
                                st.success(f"✅ {quantidade}x {produto[1]} adicionado!")
                                st.rerun()
                    
                    # Mostrar carrinho
                    if st.session_state.carrinho_itens:
                        st.subheader("📋 Carrinho de Compras")
                        total_pedido = sum(item['subtotal'] for item in st.session_state.carrinho_itens)
                        
                        for i, item in enumerate(st.session_state.carrinho_itens):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.write(f"**{item['nome']}** - {item['tamanho']} - {item['cor']}")
                            with col2:
                                st.write(f"Qtd: {item['quantidade']}")
                                st.write(f"R$ {item['subtotal']:.2f}")
                            with col3:
                                if st.button("❌ Remover", key=f"rem_{i}"):
                                    st.session_state.carrinho_itens.pop(i)
                                    st.rerun()
                        
                        st.success(f"**💰 Total: R$ {total_pedido:.2f}**")
                        
                        # Informações do pedido
                        col1, col2 = st.columns(2)
                        with col1:
                            data_entrega = st.date_input("📅 Data Entrega", min_value=date.today())
                            forma_pagamento = st.selectbox(
                                "💳 Pagamento",
                                ["Dinheiro", "Cartão", "PIX", "Transferência"]
                            )
                        with col2:
                            observacoes = st.text_area("📝 Observações")
                        
                        # Finalizar pedido
                        if st.button("✅ Finalizar Pedido", type="primary", use_container_width=True):
                            if st.session_state.carrinho_itens:
                                sucesso, resultado = adicionar_pedido(
                                    cliente_id, escola_pedido_id, st.session_state.carrinho_itens,
                                    data_entrega, forma_pagamento, observacoes, tipo_pedido
                                )
                                if sucesso:
                                    st.success(f"✅ Pedido #{resultado} criado!")
                                    st.session_state.carrinho_itens = []
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erro: {resultado}")
                            else:
                                st.error("❌ Carrinho vazio!")
                    
                    else:
                        st.info("🛒 Carrinho vazio. Adicione itens acima.")
                
                else:
                    st.error(f"❌ Nenhum produto para {escola_pedido_nome}")
    
    with tab2:
        st.subheader("📋 Todos os Pedidos")
        
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                escola_filtro = st.selectbox(
                    "Filtrar por escola:",
                    ["Todas"] + list(set(p[12] for p in pedidos)),
                    key="filtro_escola"
                )
            with col2:
                status_filtro = st.selectbox(
                    "Filtrar por status:",
                    ["Todos"] + list(set(p[3] for p in pedidos)),
                    key="filtro_status"
                )
            
            # Aplicar filtros
            pedidos_filtrados = pedidos
            if escola_filtro != "Todas":
                pedidos_filtrados = [p for p in pedidos_filtrados if p[12] == escola_filtro]
            if status_filtro != "Todos":
                pedidos_filtrados = [p for p in pedidos_filtrados if p[3] == status_filtro]
            
            dados = []
            for pedido in pedidos_filtrados:
                status_info = {
                    'Pendente': '🟡 Pendente',
                    'Em produção': '🟠 Em produção', 
                    'Pronto para entrega': '🔵 Pronto',
                    'Entregue': '🟢 Entregue',
                    'Cancelado': '🔴 Cancelado'
                }.get(pedido[3], f'⚪ {pedido[3]}')
                
                tipo_info = "📦 Venda" if pedido[11] == "Venda" else "🏭 Produção"
                
                dados.append({
                    'ID': pedido[0],
                    'Tipo': tipo_info,
                    'Escola': pedido[12],
                    'Cliente': pedido[11],
                    'Status': status_info,
                    'Data': pedido[4],
                    'Valor': f"R$ {float(pedido[9]):.2f}"
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("📦 Nenhum pedido realizado")
    
    with tab3:
        st.subheader("🔄 Gerenciar Pedidos")
        
        pedidos = listar_pedidos_por_escola()
        
        if pedidos:
            for pedido in pedidos:
                with st.expander(f"Pedido #{pedido[0]} - {pedido[11]} - {pedido[12]} - R$ {float(pedido[9]):.2f}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Cliente:** {pedido[11]}")
                        st.write(f"**Escola:** {pedido[12]}")
                        st.write(f"**Data do Pedido:** {pedido[4]}")
                        st.write(f"**Entrega Prevista:** {pedido[5]}")
                    
                    with col2:
                        st.write(f"**Status:** {pedido[3]}")
                        st.write(f"**Tipo:** {pedido[11]}")
                        st.write(f"**Valor Total:** R$ {float(pedido[9]):.2f}")
                    
                    # Atualizar status
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        novo_status = st.selectbox(
                            "Alterar status:",
                            ["Pendente", "Em produção", "Pronto para entrega", "Entregue", "Cancelado"],
                            key=f"status_{pedido[0]}"
                        )
                    with col2:
                        if st.button("🔄 Atualizar", key=f"btn_{pedido[0]}"):
                            sucesso, msg = atualizar_status_pedido(pedido[0], novo_status)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    # Excluir pedido
                    if st.button("🗑️ Excluir Pedido", key=f"del_{pedido[0]}"):
                        if st.button("✅ Confirmar Exclusão", key=f"conf_del_{pedido[0]}"):
                            sucesso, msg = excluir_pedido(pedido[0])
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.info("📦 Nenhum pedido para gerenciar")

elif menu == "👕 Produtos e Estoque":
    st.header("👕 Gestão de Produtos e Estoque")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2 = st.tabs(["📋 Produtos por Escola", "📦 Controle de Estoque"])
    
    with tab1:
        st.subheader("📋 Produtos por Escola")
        
        escola_selecionada_nome = st.selectbox(
            "🏫 Selecione a Escola:",
            [e[1] for e in escolas],
            key="produtos_escola"
        )
        
        escola_id = next(e[0] for e in escolas if e[1] == escola_selecionada_nome)
        
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
            st.success(f"📊 Encontrados {len(produtos)} produtos para {escola_selecionada_nome}")
            
            dados = []
            for produto in produtos:
                status_estoque = "✅" if produto[6] >= 5 else "⚠️" if produto[6] > 0 else "❌"
                
                dados.append({
                    'ID': produto[0],
                    'Produto': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {produto[5]:.2f}",
                    'Estoque': f"{status_estoque} {produto[6]}",
                    'Reservado': produto[7] or 0
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
            
            # Formulário para adicionar produto
            st.subheader("➕ Adicionar Novo Produto")
            with st.form("novo_produto", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("📝 Nome do produto*", placeholder="Ex: Camiseta Básica")
                    categoria = st.selectbox("📂 Categoria*", categorias_produtos)
                    tamanho = st.selectbox("📏 Tamanho*", todos_tamanhos)
                    cor = st.text_input("🎨 Cor*", value="Branco", placeholder="Ex: Azul Marinho")
                
                with col2:
                    preco = st.number_input("💰 Preço (R$)*", min_value=0.0, value=29.90, step=0.01)
                    estoque = st.number_input("📦 Estoque inicial*", min_value=0, value=10)
                    descricao = st.text_area("📄 Descrição", placeholder="Detalhes do produto...")
                
                if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                    if nome and cor:
                        sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Campos obrigatórios: Nome e Cor")
        else:
            st.info(f"👕 Nenhum produto cadastrado para {escola_selecionada_nome}")
    
    with tab2:
        st.subheader("📦 Controle de Estoque")
        
        # Abas por escola para estoque
        tabs = st.tabs([f"🏫 {e[1]}" for e in escolas])
        
        for idx, escola in enumerate(escolas):
            with tabs[idx]:
                st.subheader(f"📦 Estoque - {escola[1]}")
                
                produtos = listar_produtos_por_escola(escola[0])
                
                if produtos:
                    # Métricas da escola
                    col1, col2, col3 = st.columns(3)
                    total_produtos = len(produtos)
                    total_estoque = sum(p[6] for p in produtos)
                    produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
                    
                    with col1:
                        st.metric("Total Produtos", total_produtos)
                    with col2:
                        st.metric("Estoque Total", total_estoque)
                    with col3:
                        st.metric("Estoque Baixo", produtos_baixo_estoque)
                    
                    # Tabela de ajuste de estoque
                    st.subheader("🔄 Ajuste de Estoque")
                    
                    for produto in produtos:
                        with st.expander(f"{produto[1]} - {produto[3]} - {produto[4]} (Estoque: {produto[6]})"):
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                st.write(f"**Categoria:** {produto[2]}")
                                st.write(f"**Preço:** R$ {produto[5]:.2f}")
                            
                            with col2:
                                nova_quantidade = st.number_input(
                                    "Nova quantidade:",
                                    min_value=0,
                                    value=produto[6],
                                    key=f"estoque_{produto[0]}_{idx}"
                                )
                            
                            with col3:
                                if st.button("💾 Atualizar", key=f"btn_{produto[0]}_{idx}"):
                                    if nova_quantidade != produto[6]:
                                        sucesso, msg = atualizar_estoque(produto[0], nova_quantidade)
                                        if sucesso:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                    else:
                                        st.info("Quantidade não foi alterada")
                    
                    # Alertas de estoque baixo
                    produtos_alerta = [p for p in produtos if p[6] < 5]
                    if produtos_alerta:
                        st.subheader("🚨 Alertas de Estoque Baixo")
                        for produto in produtos_alerta:
                            cor = "red" if produto[6] == 0 else "orange"
                            st.markdown(f"<span style='color: {cor}'>⚠️ **{produto[1]} - {produto[3]} - {produto[4]}**: Apenas {produto[6]} unidades</span>", 
                                      unsafe_allow_html=True)
                
                else:
                    st.info(f"👕 Nenhum produto cadastrado para {escola[1]}")

elif menu == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    
    tab1, tab2 = st.tabs(["📋 Listar Clientes", "➕ Cadastrar Cliente"])
    
    with tab1:
        st.subheader("📋 Clientes Cadastrados")
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
    
    with tab2:
        st.subheader("➕ Cadastrar Cliente")
        
        with st.form("novo_cliente", clear_on_submit=True):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente", type="primary"):
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# Rodapé
st.sidebar.markdown("---")
if IS_RENDER:
    st.sidebar.info("👕 **Sistema Fardamentos v3.0**\n\n🌐 **Hospedado no Render**")
else:
    st.sidebar.info("👕 **Sistema Fardamentos v3.0**\n\n💻 **Ambiente Local**")

if st.sidebar.button("🔄 Recarregar Sistema"):
    st.rerun()
