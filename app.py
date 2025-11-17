import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# CONFIGURAÇÃO DA PÁGINA - DEVE SER A PRIMEIRA COISA
st.set_page_config(
    page_title="Sistema Fardamentos",
    page_icon="👕",
    layout="wide"
)

# =========================================
# 🔐 SISTEMA DE LOGIN SIMPLIFICADO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Usuários fixos para teste
USUARIOS = {
    "admin": {"senha": make_hashes("Admin@2024!"), "nome": "Administrador", "tipo": "admin"},
    "vendedor": {"senha": make_hashes("Vendas@123"), "nome": "Vendedor", "tipo": "vendedor"}
}

def verificar_login(username, password):
    if username in USUARIOS:
        if check_hashes(password, USUARIOS[username]["senha"]):
            return True, USUARIOS[username]["nome"], USUARIOS[username]["tipo"]
    return False, "Credenciais inválidas", None

# =========================================
# 🔧 BANCO DE DADOS SIMPLIFICADO
# =========================================

def init_db():
    conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabela de escolas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS escolas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabela de produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            tamanho TEXT,
            cor TEXT,
            preco REAL,
            estoque INTEGER DEFAULT 0,
            escola_id INTEGER
        )
    ''')
    
    # Inserir escolas de exemplo
    escolas_exemplo = ['Municipal', 'Desperta', 'São Tadeu']
    for escola in escolas_exemplo:
        try:
            cursor.execute("INSERT OR IGNORE INTO escolas (nome) VALUES (?)", (escola,))
        except:
            pass
    
    conn.commit()
    conn.close()

# =========================================
# 📊 FUNÇÕES BÁSICAS
# =========================================

def listar_escolas():
    conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escolas ORDER BY nome")
    escolas = cursor.fetchall()
    conn.close()
    return escolas

def listar_produtos(escola_id=None):
    conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
    cursor = conn.cursor()
    
    if escola_id:
        cursor.execute("SELECT * FROM produtos WHERE escola_id = ? ORDER BY nome", (escola_id,))
    else:
        cursor.execute("SELECT * FROM produtos ORDER BY nome")
    
    produtos = cursor.fetchall()
    conn.close()
    return produtos

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    conn = sqlite3.connect('fardamentos.db', check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        
        conn.commit()
        conn.close()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        conn.close()
        return False, f"Erro: {str(e)}"

# =========================================
# 🔐 TELA DE LOGIN
# =========================================

def mostrar_login():
    st.title("👕 Sistema de Fardamentos")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    
    with col2:
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                if username and password:
                    sucesso, mensagem, tipo = verificar_login(username, password)
                    if sucesso:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.nome_usuario = mensagem
                        st.session_state.tipo_usuario = tipo
                        st.rerun()
                    else:
                        st.error(mensagem)
                else:
                    st.error("Preencha todos os campos")
        
        st.markdown("---")
        st.info("**Usuários para teste:**")
        st.write("👤 **Admin:** admin / Admin@2024!")
        st.write("👤 **Vendedor:** vendedor / Vendas@123")

# =========================================
# 🚀 INICIALIZAÇÃO
# =========================================

# Inicializar session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Inicializar banco
if 'db_inicializado' not in st.session_state:
    init_db()
    st.session_state.db_inicializado = True

# Mostrar login se não estiver logado
if not st.session_state.logged_in:
    mostrar_login()
    st.stop()

# =========================================
# 🎨 SISTEMA PRINCIPAL
# =========================================

# Sidebar
with st.sidebar:
    st.title(f"👋 Olá, {st.session_state.nome_usuario}!")
    st.markdown(f"**Tipo:** {st.session_state.tipo_usuario}")
    st.markdown("---")
    
    # Menu
    pagina = st.radio(
        "Navegação",
        ["📊 Dashboard", "👕 Produtos", "📦 Estoque", "👥 Clientes"]
    )
    
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Header
st.title(f"{pagina.split(' ')[1]} - Sistema de Fardamentos")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if pagina == "📊 Dashboard":
    st.header("🎯 Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        escolas = listar_escolas()
        st.metric("Escolas", len(escolas))
    
    with col2:
        total_produtos = 0
        for escola in escolas:
            produtos = listar_produtos(escola[0])
            total_produtos += len(produtos)
        st.metric("Produtos", total_produtos)
    
    with col3:
        st.metric("Sistema", "✅ Online")
    
    with col4:
        st.metric("Versão", "2.0")
    
    st.success("🏭 **Sistema para Fábrica** - Pedidos em produção não consomem estoque automaticamente!")
    
    # Ações rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Cadastrar Produto", use_container_width=True):
            st.session_state.pagina = "👕 Produtos"
            st.rerun()
    
    with col2:
        if st.button("📦 Ver Estoque", use_container_width=True):
            st.session_state.pagina = "📦 Estoque"
            st.rerun()
    
    with col3:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

elif pagina == "👕 Produtos":
    st.header("👕 Gestão de Produtos")
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Lista de Produtos"])
    
    with tab1:
        st.subheader("Novo Produto")
        
        escolas = listar_escolas()
        
        with st.form("form_produto"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Produto*", placeholder="Camiseta Básica")
                categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                tamanho = st.selectbox("Tamanho*", ["PP", "P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
            
            with col2:
                cor = st.text_input("Cor*", value="Branco")
                preco = st.number_input("Preço (R$)*", min_value=0.0, value=29.90)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
                escola = st.selectbox("Escola*", [e[1] for e in escolas])
            
            if st.form_submit_button("✅ Cadastrar Produto", type="primary"):
                if nome and cor and preco > 0:
                    escola_id = next(e[0] for e in escolas if e[1] == escola)
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("Preencha todos os campos obrigatórios (*)")
    
    with tab2:
        st.subheader("Produtos Cadastrados")
        
        escolas = listar_escolas()
        escola_filtro = st.selectbox("Filtrar por escola:", ["Todas"] + [e[1] for e in escolas])
        
        if escola_filtro == "Todas":
            produtos = listar_produtos()
        else:
            escola_id = next(e[0] for e in escolas if e[1] == escola_filtro)
            produtos = listar_produtos(escola_id)
        
        if produtos:
            dados = []
            for prod in produtos:
                escola_nome = next((e[1] for e in escolas if e[0] == prod[7]), "N/A")
                status = "✅" if prod[6] > 5 else "⚠️" if prod[6] > 0 else "❌"
                
                dados.append({
                    'ID': prod[0],
                    'Produto': prod[1],
                    'Categoria': prod[2],
                    'Tamanho': prod[3],
                    'Cor': prod[4],
                    'Preço': f"R$ {prod[5]:.2f}",
                    'Estoque': f"{status} {prod[6]}",
                    'Escola': escola_nome
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado")

elif pagina == "📦 Estoque":
    st.header("📦 Controle de Estoque")
    
    escolas = listar_escolas()
    
    for escola in escolas:
        with st.expander(f"🏫 {escola[1]}", expanded=True):
            produtos = listar_produtos(escola[0])
            
            if produtos:
                # Métricas da escola
                col1, col2, col3 = st.columns(3)
                total_estoque = sum(p[6] for p in produtos)
                produtos_baixo = len([p for p in produtos if p[6] < 5])
                
                with col1:
                    st.metric("Total Produtos", len(produtos))
                with col2:
                    st.metric("Estoque Total", total_estoque)
                with col3:
                    st.metric("Estoque Baixo", produtos_baixo)
                
                # Lista de produtos
                for produto in produtos:
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{produto[1]}** - {produto[3]} - {produto[4]}")
                    
                    with col2:
                        st.write(f"Estoque: {produto[6]}")
                    
                    with col3:
                        if produto[6] < 5:
                            st.error("⚠️ Baixo")
                        elif produto[6] == 0:
                            st.error("❌ Sem estoque")
                        else:
                            st.success("✅ OK")
                    
                    with col4:
                        nova_qtd = st.number_input(
                            "Qtd",
                            min_value=0,
                            value=produto[6],
                            key=f"estoque_{produto[0]}",
                            label_visibility="collapsed"
                        )
            else:
                st.info("Nenhum produto cadastrado para esta escola")

elif pagina == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    
    st.info("""
    **Funcionalidades de Clientes:**
    - Cadastro de novos clientes
    - Listagem de clientes cadastrados
    - Histórico de pedidos por cliente
    - Contatos e informações
    """)
    
    st.success("🏭 **Modo Fábrica Ativo** - Sistema otimizado para produção")

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema Fardamentos v2.0\n\n🔧 **Modo Fábrica**")
