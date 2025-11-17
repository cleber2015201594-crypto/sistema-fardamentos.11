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
# 🔧 CONFIGURAÇÃO INICIAL
# =========================================

# Configurar página PRIMEIRO
st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# 🎯 CONFIGURAÇÕES ESPECÍFICAS
# =========================================

tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🔧 FUNÇÕES PRINCIPAIS (resumidas para exemplo)
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

# =========================================
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title(f"{menu.split(' ')[1]} - Sistema de Fardamentos")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA (versão simplificada)
# =========================================

if menu == "📊 Dashboard":
    st.header("🎯 Dashboard - Visão Geral")
    
    escolas = listar_escolas()
    clientes = listar_clientes()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Escolas", len(escolas))
    
    with col2:
        st.metric("Clientes Cadastrados", len(clientes))
    
    with col3:
        total_produtos = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            total_produtos += len(produtos)
        st.metric("Total de Produtos", total_produtos)
    
    with col4:
        st.metric("Sistema", "✅ Online")
    
    st.success("🏭 Sistema configurado para fábrica - Pedidos em produção não consomem estoque!")

elif menu == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    
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

elif menu == "👕 Produtos":
    st.header("👕 Gestão de Produtos")
    
    escolas = listar_escolas()
    
    if escolas:
        escola_selecionada_nome = st.selectbox(
            "🏫 Selecione a Escola:",
            [e[1] for e in escolas]
        )
        
        produtos = listar_produtos_por_escola(next(e[0] for e in escolas if e[1] == escola_selecionada_nome))
        
        if produtos:
            st.dataframe(pd.DataFrame([
                {
                    'ID': p[0],
                    'Produto': p[1],
                    'Categoria': p[2],
                    'Tamanho': p[3],
                    'Cor': p[4],
                    'Preço Venda': f"R$ {p[6]:.2f}",
                    'Estoque': p[7]
                } for p in produtos
            ]), use_container_width=True)
        else:
            st.info(f"👕 Nenhum produto para {escola_selecionada_nome}")
    else:
        st.error("❌ Nenhuma escola cadastrada")

elif menu == "📦 Estoque":
    st.header("📦 Controle de Estoque")
    
    escolas = listar_escolas()
    
    for escola in escolas:
        with st.expander(f"🏫 {escola[1]}"):
            produtos = listar_produtos_por_escola(escola[0])
            
            if produtos:
                st.dataframe(pd.DataFrame([
                    {
                        'Produto': p[1],
                        'Tamanho': p[3],
                        'Cor': p[4],
                        'Estoque': p[7],
                        'Status': '✅ Suficiente' if p[7] > 5 else '⚠️ Baixo' if p[7] > 0 else '❌ Sem estoque'
                    } for p in produtos
                ]), use_container_width=True)
            else:
                st.info("Nenhum produto cadastrado")

elif menu == "📦 Pedidos":
    st.header("📦 Gestão de Pedidos")
    st.info("🏭 Sistema configurado para fábrica - Os pedidos em produção NÃO consomem estoque automaticamente")
    
    st.success("""
    **Fluxo para Fábrica:**
    1. ✅ Pedido criado → Não consome estoque
    2. 🏭 Em produção → Não consome estoque  
    3. 📦 Pronto para entrega → CONSOME estoque
    4. 🚚 Entregue → Pedido finalizado
    """)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v2.0\n\n🏭 **Modo Fábrica Ativo**")
