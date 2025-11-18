import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import hashlib
import sqlite3

# =========================================
# 🔧 CONFIGURAÇÃO INICIAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================
# 🗄️ CONEXÃO COM BANCO DE DADOS
# =========================================

def get_connection():
    """Conexão com SQLite para Streamlit Sharing"""
    try:
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Tabela de usuários
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )
            ''')
            
            # Tabela de produtos
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0
                )
            ''')
            
            # Inserir usuário admin padrão
            cur.execute('''
                INSERT OR IGNORE INTO usuarios (username, password, nome, tipo)
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin123', 'Administrador', 'admin'))
            
            conn.commit()
            st.success("Banco de dados inicializado!")
            
        except Exception as e:
            st.error(f"Erro ao criar tabelas: {str(e)}")
        finally:
            conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN SIMPLIFICADO
# =========================================

def verificar_login(username, password):
    """Verifica se o usuário e senha estão corretos"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', 
                   (username, password))
        usuario = cur.fetchone()
        
        if usuario:
            return True, usuario['nome']
        else:
            return False, "Credenciais inválidas"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def login():
    """Interface de login"""
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username and password:
            sucesso, mensagem = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.nome_usuario = mensagem
                st.sidebar.success(f"Bem-vindo, {mensagem}!")
                st.rerun()
            else:
                st.sidebar.error(mensagem)
        else:
            st.sidebar.error("Preencha todos os campos")

# =========================================
# 🎯 PÁGINA PRINCIPAL
# =========================================

def mostrar_dashboard():
    """Página principal do sistema"""
    st.title("👕 Sistema de Fardamentos")
    st.markdown("---")
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📦 Total de Produtos", "15")
    
    with col2:
        st.metric("👥 Clientes Cadastrados", "8")
    
    with col3:
        st.metric("💰 Vendas do Mês", "R$ 2.450,00")
    
    # Ações rápidas
    st.subheader("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")
    
    with col2:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")
    
    with col3:
        if st.button("👥 Novo Cliente", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")

# =========================================
# 🚀 INICIALIZAÇÃO DO SISTEMA
# =========================================

# Inicializar sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Inicializar banco na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Verificar login
if not st.session_state.logged_in:
    login()
    st.stop()

# Sistema principal
mostrar_dashboard()

# Rodapé
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.nome_usuario = None
    st.rerun()
