import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
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

# =========================================
# 🔧 FUNÇÕES CORRIGIDAS PARA PEDIDOS E ESTOQUE
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

# FUNÇÃO CORRIGIDA - ADICIONAR PEDIDO
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
            
            cur.execute("SELECT estoque, estoque_reservado FROM produtos WHERE id = ?", (produto_id,))
            produto = cur.fetchone()
            
            if not produto:
                return False, f"Produto ID {produto_id} não encontrado"
            
            estoque_disponivel = produto[0]
            
            if tipo_pedido == "Venda" and quantidade > estoque_disponivel:
                return False, f"Estoque insuficiente para {item['nome']}. Disponível: {estoque_disponivel}"
        
        # INSERIR PEDIDO
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
            
            cur.execute('''
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
            ''', (pedido_id, produto_id, quantidade, preco_unitario, subtotal))
            
            # ATUALIZAR ESTOQUE CORRETAMENTE
            if tipo_pedido == "Venda":
                # VENDA: reduz estoque disponível
                cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", 
                           (quantidade, produto_id))
            else:
                # PRODUÇÃO: reserva estoque
                cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado + ? WHERE id = ?", 
                           (quantidade, produto_id))
        
        conn.commit()
        return True, pedido_id
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÃO CORRIGIDA - LISTAR PEDIDOS
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

# FUNÇÃO CORRIGIDA - ATUALIZAR STATUS
def atualizar_status_pedido(pedido_id, novo_status):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Obter tipo do pedido
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
            cur.execute('''
                UPDATE pedidos 
                SET status = ? 
                WHERE id = ?
            ''', (novo_status, pedido_id))
        
        conn.commit()
        return True, "Status atualizado com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÃO CORRIGIDA - EXCLUIR PEDIDO
def excluir_pedido(pedido_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Obter tipo do pedido e itens
        cur.execute('SELECT tipo_pedido FROM pedidos WHERE id = ?', (pedido_id,))
        resultado = cur.fetchone()
        tipo_pedido = resultado[0] if resultado else "Venda"
        
        cur.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = ?', (pedido_id,))
        itens = cur.fetchall()
        
        # Restaurar estoque corretamente
        for produto_id, quantidade in itens:
            if tipo_pedido == "Venda":
                cur.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?", (quantidade, produto_id))
            else:
                cur.execute("UPDATE produtos SET estoque_reservado = estoque_reservado - ? WHERE id = ?", (quantidade, produto_id))
        
        # Excluir pedido (CASCADE vai excluir os itens automaticamente)
        cur.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# FUNÇÃO CORRIGIDA - ATUALIZAR ESTOQUE
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
# 📊 FUNÇÕES PARA DASHBOARD POR ESCOLA
# =========================================

def obter_metricas_por_escola(escola_id):
    """Obtém métricas específicas por escola"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        
        # Total de pedidos da escola
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE escola_id = ?", (escola_id,))
        total_pedidos = cur.fetchone()[0]
        
        # Pedidos pendentes
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE escola_id = ? AND status = 'Pendente'", (escola_id,))
        pedidos_pendentes = cur.fetchone()[0]
        
        # Pedidos em produção
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE escola_id = ? AND status = 'Em produção'", (escola_id,))
        pedidos_producao = cur.fetchone()[0]
        
        # Total de produtos
        cur.execute("SELECT COUNT(*) FROM produtos WHERE escola_id = ?", (escola_id,))
        total_produtos = cur.fetchone()[0]
        
        # Vendas do mês
        mes_atual = datetime.now().strftime("%Y-%m")
        cur.execute("SELECT SUM(valor_total) FROM pedidos WHERE escola_id = ? AND strftime('%Y-%m', data_pedido) = ? AND tipo_pedido = 'Venda'", 
                   (escola_id, mes_atual))
        vendas_mes = cur.fetchone()[0] or 0
        
        # Alertas de estoque
        cur.execute("SELECT COUNT(*) FROM produtos WHERE escola_id = ? AND estoque < 5", (escola_id,))
        alertas_estoque = cur.fetchone()[0]
        
        return {
            'total_pedidos': total_pedidos,
            'pedidos_pendentes': pedidos_pendentes,
            'pedidos_producao': pedidos_producao,
            'total_produtos': total_produtos,
            'vendas_mes': vendas_mes,
            'alertas_estoque': alertas_estoque
        }
    except Exception as e:
        return {}
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

# Inicializar banco
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
    page_title="Sistema de Fardamentos - Corrigido",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONFIGURAÇÕES
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto
categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]

# =========================================
# 🎨 INTERFACE PRINCIPAL CORRIGIDA
# =========================================

# Sidebar
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal SIMPLIFICADO E FUNCIONAL
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = [
    "📊 Dashboard por Escola", 
    "📦 Gestão de Pedidos",
    "👕 Produtos e Estoque",
    "👥 Clientes"
]
menu = st.sidebar.radio("Navegação", menu_options)

# Header
st.title("👕 Sistema de Fardamentos - Corrigido")
st.markdown("---")

# =========================================
# 📱 PÁGINAS CORRIGIDAS
# =========================================

if menu == "📊 Dashboard por Escola":
    st.header("📊 Dashboard - Visão por Escola")
    
    escolas = listar_escolas()
    
 