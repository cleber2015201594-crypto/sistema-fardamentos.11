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
                    tipo_pedido TEXT DEFAULT 'Venda',
                    prioridade TEXT DEFAULT 'Normal'
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
            
            # Tabela de histórico de produção
            cur.execute('''
                CREATE TABLE IF NOT EXISTS historico_producao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER REFERENCES pedidos(id),
                    etapa TEXT,
                    status TEXT,
                    data_inicio DATE,
                    data_fim DATE,
                    observacoes TEXT,
                    responsavel TEXT
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
# 🔍 SISTEMA DE BUSCA AVANÇADA
# =========================================

def buscar_produtos(termo, escola_id=None):
    """Busca produtos por nome, categoria, cor ou tamanho"""
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
                WHERE (p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ? OR p.tamanho LIKE ?)
                AND p.escola_id = ?
                ORDER BY p.nome
            ''', (termo, termo, termo, termo, escola_id))
        else:
            cur.execute('''
                SELECT p.*, e.nome as escola_nome 
                FROM produtos p 
                LEFT JOIN escolas e ON p.escola_id = e.id 
                WHERE p.nome LIKE ? OR p.categoria LIKE ? OR p.cor LIKE ? OR p.tamanho LIKE ?
                ORDER BY e.nome, p.nome
            ''', (termo, termo, termo, termo))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []
    finally:
        conn.close()

def buscar_clientes(termo):
    """Busca clientes por nome, telefone ou email"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        termo = f"%{termo}%"
        
        cur.execute('''
            SELECT * FROM clientes 
            WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
            ORDER BY nome
        ''', (termo, termo, termo))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []
    finally:
        conn.close()

def buscar_pedidos(termo, tipo_filtro="todos"):
    """Busca pedidos por ID, cliente ou escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        termo = f"%{termo}%"
        
        if tipo_filtro == "todos":
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE c.nome LIKE ? OR e.nome LIKE ? OR CAST(p.id AS TEXT) LIKE ?
                ORDER BY p.data_pedido DESC
            ''', (termo, termo, termo))
        else:
            cur.execute('''
                SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE (c.nome LIKE ? OR e.nome LIKE ? OR CAST(p.id AS TEXT) LIKE ?)
                AND p.tipo_pedido = ?
                ORDER BY p.data_pedido DESC
            ''', (termo, termo, termo, tipo_filtro))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 📊 FUNÇÕES PARA DASHBOARD AVANÇADO
# =========================================

def obter_metricas_gerais():
    """Obtém métricas gerais para o dashboard"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor()
        
        # Total de pedidos
        cur.execute("SELECT COUNT(*) FROM pedidos")
        total_pedidos = cur.fetchone()[0]
        
        # Pedidos pendentes
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'Pendente'")
        pedidos_pendentes = cur.fetchone()[0]
        
        # Pedidos em produção
        cur.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'Em produção'")
        pedidos_producao = cur.fetchone()[0]
        
        # Total de clientes
        cur.execute("SELECT COUNT(*) FROM clientes")
        total_clientes = cur.fetchone()[0]
        
        # Total de produtos
        cur.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cur.fetchone()[0]
        
        # Vendas do mês
        mes_atual = datetime.now().strftime("%Y-%m")
        cur.execute("SELECT SUM(valor_total) FROM pedidos WHERE strftime('%Y-%m', data_pedido) = ? AND tipo_pedido = 'Venda'", (mes_atual,))
        vendas_mes = cur.fetchone()[0] or 0
        
        # Alertas de estoque
        cur.execute("SELECT COUNT(*) FROM produtos WHERE estoque < 5")
        alertas_estoque = cur.fetchone()[0]
        
        return {
            'total_pedidos': total_pedidos,
            'pedidos_pendentes': pedidos_pendentes,
            'pedidos_producao': pedidos_producao,
            'total_clientes': total_clientes,
            'total_produtos': total_produtos,
            'vendas_mes': vendas_mes,
            'alertas_estoque': alertas_estoque
        }
    except Exception as e:
        st.error(f"Erro ao obter métricas: {e}")
        return {}
    finally:
        conn.close()

def obter_dados_grafico_vendas(periodo='30d'):
    """Obtém dados para gráfico de vendas"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if periodo == '30d':
            data_inicio = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            query = '''
                SELECT DATE(data_pedido) as data, SUM(valor_total) as total
                FROM pedidos 
                WHERE data_pedido >= ? AND tipo_pedido = 'Venda'
                GROUP BY DATE(data_pedido)
                ORDER BY data
            '''
        elif periodo == '7d':
            data_inicio = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            query = '''
                SELECT DATE(data_pedido) as data, SUM(valor_total) as total
                FROM pedidos 
                WHERE data_pedido >= ? AND tipo_pedido = 'Venda'
                GROUP BY DATE(data_pedido)
                ORDER BY data
            '''
        else:  # 12 meses
            data_inicio = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            query = '''
                SELECT strftime('%Y-%m', data_pedido) as mes, SUM(valor_total) as total
                FROM pedidos 
                WHERE data_pedido >= ? AND tipo_pedido = 'Venda'
                GROUP BY strftime('%Y-%m', data_pedido)
                ORDER BY mes
            '''
        
        cur.execute(query, (data_inicio,))
        dados = cur.fetchall()
        
        if dados:
            if periodo in ['7d', '30d']:
                df = pd.DataFrame(dados, columns=['Data', 'Total Vendas (R$)'])
            else:
                df = pd.DataFrame(dados, columns=['Mês', 'Total Vendas (R$)'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao obter dados do gráfico: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def obter_dados_comparativo_escolas():
    """Obtém dados comparativos entre escolas"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            SELECT 
                e.nome as escola,
                COUNT(p.id) as total_pedidos,
                SUM(CASE WHEN p.tipo_pedido = 'Venda' THEN p.valor_total ELSE 0 END) as total_vendas,
                SUM(CASE WHEN p.tipo_pedido = 'Produção' THEN p.quantidade_total ELSE 0 END) as total_producao,
                COUNT(DISTINCT pr.id) as total_produtos
            FROM escolas e
            LEFT JOIN pedidos p ON e.id = p.escola_id
            LEFT JOIN produtos pr ON e.id = pr.escola_id
            GROUP BY e.id, e.nome
            ORDER BY total_vendas DESC
        ''')
        
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Escola', 'Total Pedidos', 'Vendas (R$)', 'Produção (Un)', 'Produtos'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao obter dados comparativos: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🏭 CONTROLE DE PRODUÇÃO AVANÇADO
# =========================================

def adicionar_etapa_producao(pedido_id, etapa, responsavel, observacoes=""):
    """Adiciona uma etapa ao histórico de produção"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_inicio = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute('''
            INSERT INTO historico_producao (pedido_id, etapa, status, data_inicio, responsavel, observacoes)
            VALUES (?, ?, 'Em andamento', ?, ?, ?)
        ''', (pedido_id, etapa, data_inicio, responsavel, observacoes))
        
        conn.commit()
        return True, "Etapa de produção registrada!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def finalizar_etapa_producao(historico_id):
    """Finaliza uma etapa de produção"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        data_fim = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute('''
            UPDATE historico_producao 
            SET status = 'Concluído', data_fim = ?
            WHERE id = ?
        ''', (data_fim, historico_id))
        
        conn.commit()
        return True, "Etapa finalizada!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def obter_historico_producao(pedido_id):
    """Obtém o histórico de produção de um pedido"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            SELECT * FROM historico_producao 
            WHERE pedido_id = ?
            ORDER BY data_inicio DESC
        ''', (pedido_id,))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao obter histórico: {e}")
        return []
    finally:
        conn.close()

def obter_pedidos_atrasados():
    """Obtém pedidos com entrega atrasada"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        cur.execute('''
            SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            JOIN escolas e ON p.escola_id = e.id
            WHERE p.data_entrega_prevista < ? AND p.status NOT IN ('Entregue', 'Cancelado')
            ORDER BY p.data_entrega_prevista ASC
        ''', (hoje,))
        
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao obter pedidos atrasados: {e}")
        return []
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN (Restante do código...)
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
    page_title="Sistema de Fardamentos - Melhorado",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CONFIGURAÇÕES ESPECÍFICAS
tamanhos_infantil = ["2", "4", "6", "8", "10", "12"]
tamanhos_adulto = ["PP", "P", "M", "G", "GG"]
todos_tamanhos = tamanhos_infantil + tamanhos_adulto

categorias_produtos = ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios", "Outros"]
etapas_producao = ["Corte", "Costura", "Estamparia", "Acabamento", "Qualidade", "Embalagem"]

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
menu_options = ["📊 Dashboard Interativo", "🔍 Busca Avançada", "📦 Pedidos", "🏭 Controle Produção", "👥 Clientes", "👕 Produtos", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header dinâmico
st.title("👕 Sistema de Fardamentos - Melhorado")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA MELHORADAS
# =========================================

if menu == "📊 Dashboard Interativo":
    st.header("📊 Dashboard Interativo")
    
    # Métricas em tempo real
    metricas = obter_metricas_gerais()
    
    if metricas:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📦 Total Pedidos", metricas['total_pedidos'])
            st.metric("⏳ Pendentes", metricas['pedidos_pendentes'])
        
        with col2:
            st.metric("🏭 Em Produção", metricas['pedidos_producao'])
            st.metric("👥 Total Clientes", metricas['total_clientes'])
        
        with col3:
            st.metric("👕 Total Produtos", metricas['total_produtos'])
            st.metric("💰 Vendas do Mês", f"R$ {metricas['vendas_mes']:,.2f}")
        
        with col4:
            st.metric("🚨 Alertas Estoque", metricas['alertas_estoque'])
            cor = "red" if metricas['alertas_estoque'] > 0 else "green"
            st.markdown(f"<span style='color: {cor}'>⚠️ {metricas['alertas_estoque']} produtos com estoque baixo</span>", unsafe_allow_html=True)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Evolução de Vendas")
        periodo = st.selectbox("Período:", ["7d", "30d", "12m"], key="periodo_vendas")
        
        dados_vendas = obter_dados_grafico_vendas(periodo)
        if not dados_vendas.empty:
            if periodo in ['7d', '30d']:
                fig = px.line(dados_vendas, x='Data', y='Total Vendas (R$)', 
                             title=f'Vendas dos Últimos {periodo}')
            else:
                fig = px.bar(dados_vendas, x='Mês', y='Total Vendas (R$)', 
                            title='Vendas dos Últimos 12 Meses')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Nenhum dado de venda disponível")
    
    with col2:
        st.subheader("🏫 Comparativo entre Escolas")
        dados_escolas = obter_dados_comparativo_escolas()
        if not dados_escolas.empty:
            fig = px.bar(dados_escolas, x='Escola', y=['Vendas (R$)', 'Produção (Un)'], 
                        title='Desempenho por Escola', barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🏫 Nenhum dado comparativo disponível")
    
    # Alertas e Ações Rápidas
    st.subheader("🚨 Alertas e Ações Rápidas")
    
    # Pedidos atrasados
    pedidos_atrasados = obter_pedidos_atrasados()
    if pedidos_atrasados:
        st.warning(f"⚠️ **{len(pedidos_atrasados)} pedidos atrasados!**")
        for pedido in pedidos_atrasados[:3]:  # Mostrar apenas os 3 primeiros
            st.error(f"Pedido #{pedido[0]} - {pedido[11]} - Atrasado desde {pedido[5]}")
    else:
        st.success("✅ Nenhum pedido atrasado")
    
    # Ações rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Novo Pedido Venda", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    with col2:
        if st.button("🏭 Novo Pedido Produção", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    with col3:
        if st.button("🔍 Buscar Itens", use_container_width=True):
            st.session_state.menu = "🔍 Busca Avançada"
            st.rerun()

elif menu == "🔍 Busca Avançada":
    st.header("🔍 Busca Avançada")
    
    tab1, tab2, tab3 = st.tabs(["🔎 Buscar Produtos", "👥 Buscar Clientes", "📦 Buscar Pedidos"])
    
    with tab1:
        st.subheader("🔎 Buscar Produtos")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            termo_produto = st.text_input("Digite o termo de busca:", placeholder="Nome, categoria, cor, tamanho...")
        with col2:
            escolas = listar_escolas()
            escola_filtro = st.selectbox("Filtrar por escola:", ["Todas"] + [e[1] for e in escolas])
        
        if termo_produto:
            escola_id = None if escola_filtro == "Todas" else next(e[0] for e in escolas if e[1] == escola_filtro)
            resultados = buscar_produtos(termo_produto, escola_id)
            
            if resultados:
                st.success(f"🔍 Encontrados {len(resultados)} produtos")
                
                dados = []
                for produto in resultados:
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
                        'Escola': produto[10]
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("🔍 Nenhum produto encontrado")
        else:
            st.info("🔍 Digite um termo para buscar produtos")
    
    with tab2:
        st.subheader("👥 Buscar Clientes")
        
        termo_cliente = st.text_input("Digite o termo de busca:", placeholder="Nome, telefone, email...", key="busca_cliente")
        
        if termo_cliente:
            resultados = buscar_clientes(termo_cliente)
            
            if resultados:
                st.success(f"🔍 Encontrados {len(resultados)} clientes")
                
                dados = []
                for cliente in resultados:
                    dados.append({
                        'ID': cliente[0],
                        'Nome': cliente[1],
                        'Telefone': cliente[2] or 'N/A',
                        'Email': cliente[3] or 'N/A',
                        'Data Cadastro': cliente[4]
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("🔍 Nenhum cliente encontrado")
        else:
            st.info("🔍 Digite um termo para buscar clientes")
    
    with tab3:
        st.subheader("📦 Buscar Pedidos")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            termo_pedido = st.text_input("Digite o termo de busca:", placeholder="ID do pedido, cliente, escola...", key="busca_pedido")
        with col2:
            tipo_filtro = st.selectbox("Tipo:", ["todos", "Venda", "Produção"])
        
        if termo_pedido:
            resultados = buscar_pedidos(termo_pedido, tipo_filtro)
            
            if resultados:
                st.success(f"🔍 Encontrados {len(resultados)} pedidos")
                
                dados = []
                for pedido in resultados:
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
                        'Escola': pedido[12],
                        'Status': status_info,
                        'Data': pedido[4],
                        'Valor': f"R$ {float(pedido[9]):.2f}"
                    })
                
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("🔍 Nenhum pedido encontrado")
        else:
            st.info("🔍 Digite um termo para buscar pedidos")

elif menu == "🏭 Controle Produção":
    st.header("🏭 Controle de Produção Avançado")
    
    tab1, tab2, tab3 = st.tabs(["📋 Timeline Produção", "⏰ Pedidos Atrasados", "📊 Métricas Produção"])
    
    with tab1:
        st.subheader("📋 Timeline de Produção")
        
        # Selecionar pedido para acompanhar
        pedidos_producao = listar_pedidos_por_escola()
        pedidos_producao = [p for p in pedidos_producao if p[11] == "Produção" and p[3] != "Entregue"]
        
        if pedidos_producao:
            pedido_selecionado = st.selectbox(
                "Selecione o pedido para acompanhar:",
                [f"#{p[0]} - {p[11]} - {p[12]} - {p[3]}" for p in pedidos_producao]
            )
            
            if pedido_selecionado:
                pedido_id = int(pedido_selecionado.split("#")[1].split(" -")[0])
                
                # Mostrar histórico atual
                historico = obter_historico_producao(pedido_id)
                
                if historico:
                    st.subheader("📅 Histórico de Produção")
                    for etapa in historico:
                        col1, col2, col3, col4 = st.columns([2,1,1,1])
                        with col1:
                            status_icon = "🟢" if etapa[3] == "Concluído" else "🟡" if etapa[3] == "Em andamento" else "⚪"
                            st.write(f"{status_icon} **{etapa[2]}**")
                        with col2:
                            st.write(f"👤 {etapa[6]}")
                        with col3:
                            st.write(f"📅 {etapa[4]}")
                        with col4:
                            if etapa[3] == "Em andamento":
                                if st.button("✅ Finalizar", key=f"fin_{etapa[0]}"):
                                    sucesso, msg = finalizar_etapa_producao(etapa[0])
                                    if sucesso:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                
                # Adicionar nova etapa
                st.subheader("➕ Nova Etapa de Produção")
                with st.form("nova_etapa"):
                    nova_etapa = st.selectbox("Etapa:", etapas_producao)
                    responsavel = st.text_input("Responsável:", value=st.session_state.nome_usuario)
                    observacoes = st.text_area("Observações:")
                    
                    if st.form_submit_button("➕ Adicionar Etapa"):
                        sucesso, msg = adicionar_etapa_producao(pedido_id, nova_etapa, responsavel, observacoes)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("🏭 Nenhum pedido em produção no momento")
    
    with tab2:
        st.subheader("⏰ Pedidos Atrasados")
        
        pedidos_atrasados = obter_pedidos_atrasados()
        
        if pedidos_atrasados:
            st.error(f"🚨 **{len(pedidos_atrasados)} PEDIDOS ATRASADOS**")
            
            for pedido in pedidos_atrasados:
                dias_atraso = (datetime.now() - datetime.strptime(pedido[5], "%Y-%m-%d")).days
                
                with st.expander(f"🚨 Pedido #{pedido[0]} - {pedido[11]} - {dias_atraso} dias atrasado", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Cliente:** {pedido[11]}")
                        st.write(f"**Escola:** {pedido[12]}")
                        st.write(f"**Data Prevista:** {pedido[5]}")
                    with col2:
                        st.write(f"**Status:** {pedido[3]}")
                        st.write(f"**Valor:** R$ {float(pedido[9]):.2f}")
                        st.write(f"**Dias de Atraso:** {dias_atraso}")
                    
                    # Ação rápida para atualizar status
                    novo_status = st.selectbox(
                        "Atualizar status:",
                        ["Em produção", "Pronto para entrega", "Entregue"],
                        key=f"status_atraso_{pedido[0]}"
                    )
                    if st.button("🔄 Atualizar", key=f"btn_atraso_{pedido[0]}"):
                        # Função para atualizar status (já existe no código original)
                        sucesso, msg = atualizar_status_pedido(pedido[0], novo_status)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.success("✅ Nenhum pedido atrasado!")
    
    with tab3:
        st.subheader("📊 Métricas de Produção")
        
        # Métricas básicas de produção
        metricas = obter_metricas_gerais()
        pedidos_producao = [p for p in listar_pedidos_por_escola() if p[11] == "Produção"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏭 Pedidos em Produção", metricas['pedidos_producao'])
        with col2:
            total_itens_producao = sum(p[8] for p in pedidos_producao if p[3] in ['Pendente', 'Em produção'])
            st.metric("📦 Itens para Produzir", total_itens_producao)
        with col3:
            pedidos_hoje = len([p for p in pedidos_producao if p[4].startswith(datetime.now().strftime("%Y-%m-%d"))])
            st.metric("📅 Produções Hoje", pedidos_hoje)

# Rodapé
st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema Fardamentos v10.0\n\n📊 **Dashboard Interativo**\n🔍 **Busca Avançada**\n🏭 **Controle Produção**")

if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()