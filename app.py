import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import hashlib
import sqlite3

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
    """Inicializa o banco SQLite"""
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
            
            # Tabela de produtos
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
                    tipo_pedido TEXT DEFAULT 'Venda'
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
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', make_hashes('Admin@2024!'), 'Administrador', 'admin'),
                ('vendedor', make_hashes('Vendas@123'), 'Vendedor', 'vendedor')
            ]
            
            for username, password_hash, nome, tipo in usuarios_padrao:
                try:
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
                    cur.execute('INSERT OR IGNORE INTO escolas (nome) VALUES (?)', (escola,))
                except:
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
            return True, resultado[1], resultado[2]
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
# 🔧 FUNÇÕES DO BANCO DE DADOS
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
def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, descricao, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
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

# FUNÇÕES PARA PEDIDOS
def adicionar_pedido(cliente_id, escola_id, itens, data_entrega, forma_pagamento, observacoes, tipo_pedido="Venda"):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        quantidade_total = sum(item['quantidade'] for item in itens)
        valor_total = sum(item['subtotal'] for item in itens)
        
        cur.execute('''
            INSERT INTO pedidos (cliente_id, escola_id, data_entrega_prevista, forma_pagamento, 
                               quantidade_total, valor_total, observacoes, tipo_pedido)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cliente_id, escola_id, data_entrega, forma_pagamento, quantidade_total, valor_total, observacoes, tipo_pedido))
        
        pedido_id = cur.lastrowid
        
        for item in itens:
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, item['produto_id'], item['quantidade'], item['preco_unitario'], item['subtotal']))
            
            if tipo_pedido == "Venda":
                # Para vendas, reduzir estoque imediatamente
                cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                           (item['quantidade'], item['produto_id']))
            else:
                # Para produção, reservar estoque
                cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado + ? WHERE id = ?", 
                           (item['quantidade'], item['produto_id']))
        
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
        
        # Verificar tipo do pedido
        cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = ?', (pedido_id,))
        resultado = cur.fetchone()
        tipo_pedido = resultado[0] if resultado else "Venda"
        
        if novo_status == 'Entregue':
            data_entrega = datetime.now().strftime("%Y-%m-%d")
            cur.execute('''
                UPDATE pedidos 
                SET status = ?, data_entrega_real = ? 
                WHERE id = ?
            ''', (novo_status, data_entrega, pedido_id))
            
            # Se for pedido de produção finalizado, liberar estoque
            if tipo_pedido == "Produção":
                # Obter itens do pedido
                cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
                itens = cur.fetchall()
                
                for produto_id, quantidade in itens:
                    # Transferir do reservado para o estoque real
                    cur.execute('''
                        UPDATE produtos 
                        SET estoque = estoque + ?, estoque_reservado = estoque_reservado - ? 
                        WHERE id = ?
                    ''', (quantidade, quantidade, produto_id))
                    
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
        
        # Verificar tipo do pedido para restaurar estoque adequadamente
        cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = ?', (pedido_id,))
        resultado = cur.fetchone()
        tipo_pedido = resultado[0] if resultado else "Venda"
        
        # Restaurar estoque
        cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
        itens = cur.fetchall()
        
        for item in itens:
            produto_id, quantidade = item[0], item[1]
            if tipo_pedido == "Venda":
                cur.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))
            else:
                cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado - ? WHERE id = ?", (quantidade, produto_id))
        
        # Excluir pedido
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES PARA RELATÓRIOS
# =========================================

def gerar_relatorio_vendas_por_escola(escola_id=None):
    """Gera relatório de vendas por período e escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                WHERE p.escola_id = ? AND p.tipo_pedido = 'Venda'
                GROUP BY DATE(p.data_pedido)
                ORDER BY data DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    e.nome as escola,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_vendas
                FROM pedidos p
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.tipo_pedido = 'Venda'
                GROUP BY DATE(p.data_pedido), e.nome
                ORDER BY data DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Data', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Vendas (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_producao_por_escola(escola_id=None):
    """Gera relatório de produção por período e escola"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if escola_id:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_estimado
                FROM pedidos p
                WHERE p.escola_id = ? AND p.tipo_pedido = 'Produção'
                GROUP BY DATE(p.data_pedido)
                ORDER BY data DESC
            ''', (escola_id,))
        else:
            cur.execute('''
                SELECT 
                    DATE(p.data_pedido) as data,
                    e.nome as escola,
                    COUNT(*) as total_pedidos,
                    SUM(p.quantidade_total) as total_itens,
                    SUM(p.valor_total) as total_estimado
                FROM pedidos p
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.tipo_pedido = 'Produção'
                GROUP BY DATE(p.data_pedido), e.nome
                ORDER BY data DESC
            ''')
            
        dados = cur.fetchall()
        
        if dados:
            if escola_id:
                df = pd.DataFrame(dados, columns=['Data', 'Total Pedidos', 'Total Itens', 'Total Estimado (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Data', 'Escola', 'Total Pedidos', 'Total Itens', 'Total Estimado (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

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
            tipo = st.selectbox("Tipo", ["admin", "vendedor"])
            
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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Produtos", "📦 Estoque", "📈 Relatórios", "❓ Ajuda"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title("👕 Sistema de Fardamentos")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.header("📊 Dashboard - Visão Geral")
    
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
            pedidos_pendentes += len([p for p in pedidos if p[3] == 'Pendente'])
        st.metric("Pedidos Pendentes", pedidos_pendentes)
    
    with col3:
        st.metric("Clientes Ativos", len(clientes))
    
    with col4:
        produtos_baixo_estoque = 0
        for escola in escolas:
            produtos = listar_produtos_por_escola(escola[0])
            produtos_baixo_estoque += len([p for p in produtos if p[6] < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque)

elif menu == "👥 Clientes":
    st.header("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.subheader("➕ Novo Cliente")
        
        nome = st.text_input("👤 Nome completo*")
        telefone = st.text_input("📞 Telefone")
        email = st.text_input("📧 Email")
        
        if st.button("✅ Cadastrar Cliente", type="primary"):
            if nome:
                sucesso, msg = adicionar_cliente(nome, telefone, email)
                if sucesso:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.error("❌ Nome é obrigatório!")
    
    with tab2:
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
    
    with tab3:
        st.subheader("🗑️ Excluir Cliente")
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
    st.header("👕 Gestão de Produtos")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    escola_selecionada_nome = st.selectbox(
        "🏫 Selecione a Escola:",
        [e[1] for e in escolas],
        key="produtos_escola"
    )
    
    escola_id = next(e[0] for e in escolas if e[1] == escola_selecionada_nome)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Produtos da Escola"])
    
    with tab1:
        st.subheader(f"➕ Novo Produto - {escola_selecionada_nome}")
        
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
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab2:
        st.subheader(f"📋 Produtos - {escola_selecionada_nome}")
        produtos = listar_produtos_por_escola(escola_id)
        
        if produtos:
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
                    'Reservado': produto[7] or 0,
                    'Descrição': produto[8] or 'N/A'
                })
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"👕 Nenhum produto cadastrado para {escola_selecionada_nome}")

elif menu == "📦 Pedidos":
    st.header("📦 Gestão de Pedidos")
    
    escolas = listar_escolas()
    
    if not escolas:
        st.error("❌ Nenhuma escola cadastrada.")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["➕ Novo Pedido", "📋 Todos os Pedidos", "🔄 Gerenciar Pedidos"])
    
    with tab1:
        st.subheader("➕ Novo Pedido")
        
        # Seleção do tipo de pedido
        tipo_pedido = st.radio("📋 Tipo de Pedido:", ["Venda", "Produção"], horizontal=True)
        
        if tipo_pedido == "Produção":
            st.info("📝 **Pedido de Produção**: Itens serão reservados no estoque e só serão disponibilizados quando o pedido for marcado como 'Entregue'")
        
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
                [f"{c[1]} (ID: {c[0]})" for c in clientes]
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("(ID: ")[1].replace(")", ""))
                
                # Produtos da escola
                produtos = listar_produtos_por_escola(escola_pedido_id)
                
                if produtos:
                    st.subheader(f"🛒 Produtos Disponíveis - {escola_pedido_nome}")
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        produto_selecionado = st.selectbox(
                            "Produto:",
                            [f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" for p in produtos],
                            key="produto_pedido"
                        )
                    with col2:
                        quantidade = st.number_input("Quantidade", min_value=1, value=1, key="qtd_pedido")
                    with col3:
                        if st.button("➕ Adicionar Item", use_container_width=True):
                            if 'itens_pedido' not in st.session_state:
                                st.session_state.itens_pedido = []
                            
                            produto_id = next(p[0] for p in produtos if f"{p[1]} - Tamanho: {p[3]} - Cor: {p[4]} - Estoque: {p[6]} - R$ {p[5]:.2f}" == produto_selecionado)
                            produto = next(p for p in produtos if p[0] == produto_id)
                            
                            # Verificar disponibilidade
                            if tipo_pedido == "Venda" and quantidade > produto[6]:
                                st.error("❌ Quantidade indisponível em estoque!")
                            elif tipo_pedido == "Produção" and quantidade > (produto[6] + (produto[7] or 0)):
                                st.error("❌ Quantidade excede capacidade de produção!")
                            else:
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
                                        'preco_unitario': float(produto[5]),
                                        'subtotal': float(produto[5]) * quantidade
                                    }
                                    st.session_state.itens_pedido.append(item)
                                
                                st.success("✅ Item adicionado!")
                                st.rerun()
                    
                    # Mostrar itens adicionados
                    if 'itens_pedido' in st.session_state and st.session_state.itens_pedido:
                        st.subheader("📋 Itens do Pedido")
                        total_pedido = sum(item['subtotal'] for item in st.session_state.itens_pedido)
                        
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
                        
                        # Informações adicionais
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
                                sucesso, resultado = adicionar_pedido(
                                    cliente_id, 
                                    escola_pedido_id,
                                    st.session_state.itens_pedido, 
                                    data_entrega, 
                                    forma_pagamento,
                                    observacoes,
                                    tipo_pedido
                                )
                                if sucesso:
                                    st.success(f"✅ Pedido #{resultado} criado com sucesso! (Tipo: {tipo_pedido})")
                                    del st.session_state.itens_pedido
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erro ao criar pedido: {resultado}")
                            else:
                                st.error("❌ Adicione pelo menos um item ao pedido!")
                    else:
                        st.info("🛒 Adicione itens ao pedido usando o botão 'Adicionar Item'")
                else:
                    st.error(f"❌ Nenhum produto cadastrado para {escola_pedido_nome}.")

elif menu == "📈 Relatórios":
    st.header("📈 Relatórios Detalhados")
    
    escolas = listar_escolas()
    
    tab1, tab2 = st.tabs(["📊 Vendas por Escola", "🏭 Produção por Escola"])
    
    with tab1:
        st.subheader("📊 Relatório de Vendas por Escola")
        
        escola_relatorio = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e[1] for e in escolas],
            key="relatorio_vendas"
        )
        
        if escola_relatorio == "Todas as escolas":
            relatorio_vendas = gerar_relatorio_vendas_por_escola()
        else:
            escola_id = next(e[0] for e in escolas if e[1] == escola_relatorio)
            relatorio_vendas = gerar_relatorio_vendas_por_escola(escola_id)
        
        if not relatorio_vendas.empty:
            st.dataframe(relatorio_vendas, use_container_width=True)
        else:
            st.info("📊 Nenhum dado de venda disponível")
    
    with tab2:
        st.subheader("🏭 Relatório de Produção por Escola")
        
        escola_producao = st.selectbox(
            "Selecione a escola:",
            ["Todas as escolas"] + [e[1] for e in escolas],
            key="relatorio_producao"
        )
        
        if escola_producao == "Todas as escolas":
            relatorio_producao = gerar_relatorio_producao_por_escola()
        else:
            escola_id = next(e[0] for e in escolas if e[1] == escola_producao)
            relatorio_producao = gerar_relatorio_producao_por_escola(escola_id)
        
        if not relatorio_producao.empty:
            st.dataframe(relatorio_producao, use_container_width=True)
        else:
            st.info("🏭 Nenhum dado de produção disponível")

elif menu == "❓ Ajuda":
    st.header("❓ Ajuda e Informações")
    
    st.subheader("👋 Bem-vindo ao Sistema de Fardamentos!")
    
    st.markdown("""
    ### 🎯 Sistema de Produção Integrado
    
    **Pedidos de Venda vs Produção:**
    - **📦 Venda**: Consome estoque imediatamente
    - **🏭 Produção**: Reserva estoque e libera quando finalizado
    
    ### 🔄 Fluxo de Produção:
    1. **Cria pedido de produção** → Itens são reservados
    2. **Produz os itens** → Status "Em produção" 
    3. **Finaliza produção** → Status "Entregue" libera estoque
    4. **Estoque disponível** para vendas
    
    ### 👥 Login Padrão:
    - **Admin**: `admin` / `Admin@2024!`
    - **Vendedor**: `vendedor` / `Vendas@123`
    """)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v9.0\n\n🏫 Organizado por Escola\n🔄 Sistema de Produção")

if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()