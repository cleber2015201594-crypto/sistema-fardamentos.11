import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
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
            
            # Tabela de notificações
            cur.execute('''
                CREATE TABLE IF NOT EXISTS notificacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT,
                    mensagem TEXT,
                    lida BOOLEAN DEFAULT 0,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# =========================================
# 🔔 SISTEMA DE NOTIFICAÇÕES
# =========================================

def criar_notificacao(tipo, mensagem):
    """Cria uma nova notificação"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO notificacoes (tipo, mensagem) 
            VALUES (?, ?)
        ''', (tipo, mensagem))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def obter_notificacoes_nao_lidas():
    """Obtém notificações não lidas"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT * FROM notificacoes 
            WHERE lida = 0 
            ORDER BY data_criacao DESC 
            LIMIT 10
        ''')
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

def marcar_notificacao_como_lida(notificacao_id):
    """Marca uma notificação como lida"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('''
            UPDATE notificacoes 
            SET lida = 1 
            WHERE id = ?
        ''', (notificacao_id,))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

# =========================================
# 📊 RELATÓRIOS AVANÇADOS
# =========================================

def gerar_relatorio_financeiro(mes=None, ano=None):
    """Gera relatório financeiro detalhado"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        if mes and ano:
            data_filtro = f"{ano}-{mes:02d}"
            cur.execute('''
                SELECT 
                    p.id as pedido_id,
                    c.nome as cliente,
                    e.nome as escola,
                    p.data_pedido,
                    p.valor_total,
                    p.forma_pagamento,
                    p.status
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE strftime('%Y-%m', p.data_pedido) = ? 
                AND p.tipo_pedido = 'Venda'
                ORDER BY p.data_pedido DESC
            ''', (data_filtro,))
        else:
            cur.execute('''
                SELECT 
                    p.id as pedido_id,
                    c.nome as cliente,
                    e.nome as escola,
                    p.data_pedido,
                    p.valor_total,
                    p.forma_pagamento,
                    p.status
                FROM pedidos p
                JOIN clientes c ON p.cliente_id = c.id
                JOIN escolas e ON p.escola_id = e.id
                WHERE p.tipo_pedido = 'Venda'
                ORDER BY p.data_pedido DESC
            ''')
        
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Pedido ID', 'Cliente', 'Escola', 'Data', 'Valor (R$)', 'Pagamento', 'Status'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório financeiro: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_estoque_critico():
    """Gera relatório de estoque crítico"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            SELECT 
                p.nome as produto,
                p.categoria,
                p.tamanho,
                p.cor,
                p.estoque,
                p.estoque_reservado,
                e.nome as escola,
                CASE 
                    WHEN p.estoque = 0 THEN 'ESGOTADO'
                    WHEN p.estoque < 3 THEN 'CRÍTICO'
                    WHEN p.estoque < 5 THEN 'BAIXO'
                    ELSE 'NORMAL'
                END as nivel_estoque
            FROM produtos p
            JOIN escolas e ON p.escola_id = e.id
            WHERE p.estoque < 5
            ORDER BY p.estoque ASC, e.nome, p.nome
        ''')
        
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Produto', 'Categoria', 'Tamanho', 'Cor', 'Estoque', 'Reservado', 'Escola', 'Nível'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório de estoque: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def gerar_relatorio_desempenho_vendedores():
    """Gera relatório de desempenho por vendedor"""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        cur = conn.cursor()
        
        cur.execute('''
            SELECT 
                u.nome_completo as vendedor,
                COUNT(p.id) as total_pedidos,
                SUM(p.valor_total) as total_vendas,
                AVG(p.valor_total) as ticket_medio,
                COUNT(DISTINCT p.cliente_id) as clientes_ativos
            FROM pedidos p
            JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.tipo_pedido = 'Venda'
            GROUP BY u.nome_completo
            ORDER BY total_vendas DESC
        ''')
        
        dados = cur.fetchall()
        
        if dados:
            df = pd.DataFrame(dados, columns=['Vendedor', 'Total Pedidos', 'Total Vendas (R$)', 'Ticket Médio (R$)', 'Clientes Ativos'])
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao gerar relatório de vendedores: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# =========================================
# 🎯 SISTEMA DE METAS E INDICADORES
# =========================================

def definir_meta_vendas(mes, ano, valor_meta):
    """Define meta de vendas para um mês"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        
        # Verificar se meta já existe
        cur.execute('SELECT * FROM metas WHERE mes = ? AND ano = ?', (mes, ano))
        if cur.fetchone():
            cur.execute('UPDATE metas SET valor_meta = ? WHERE mes = ? AND ano = ?', (valor_meta, mes, ano))
        else:
            cur.execute('INSERT INTO metas (mes, ano, valor_meta, tipo) VALUES (?, ?, ?, "vendas")', (mes, ano, valor_meta))
        
        conn.commit()
        return True, "Meta definida com sucesso!"
        
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def obter_desempenho_meta(mes, ano):
    """Obtém desempenho em relação à meta"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        
        # Obter meta
        cur.execute('SELECT valor_meta FROM metas WHERE mes = ? AND ano = ? AND tipo = "vendas"', (mes, ano))
        meta = cur.fetchone()
        
        if not meta:
            return None
        
        # Obter vendas realizadas
        data_filtro = f"{ano}-{mes:02d}"
        cur.execute('SELECT SUM(valor_total) FROM pedidos WHERE strftime("%Y-%m", data_pedido) = ? AND tipo_pedido = "Venda"', (data_filtro,))
        vendas = cur.fetchone()[0] or 0
        
        return {
            'meta': meta[0],
            'vendas': vendas,
            'atingimento': (vendas / meta[0]) * 100 if meta[0] > 0 else 0,
            'diferenca': vendas - meta[0]
        }
        
    except Exception as e:
        return None
    finally:
        conn.close()

# =========================================
# 🔄 FUNÇÕES EXISTENTES (resumidas)
# =========================================

def verificar_login(username, password):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT password_hash, nome_completo, tipo FROM usuarios WHERE username = ? AND ativo = 1', (username,))
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

def listar_pedidos_por_escola(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        if escola_id:
            cur.execute('SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome FROM pedidos p JOIN clientes c ON p.cliente_id = c.id JOIN escolas e ON p.escola_id = e.id WHERE p.escola_id = ? ORDER BY p.data_pedido DESC', (escola_id,))
        else:
            cur.execute('SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome FROM pedidos p JOIN clientes c ON p.cliente_id = c.id JOIN escolas e ON p.escola_id = e.id ORDER BY p.data_pedido DESC')
        return cur.fetchall()
    except Exception as e:
        return []
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
    page_title="Sistema de Fardamentos - Completo",
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
# 🎨 INTERFACE PRINCIPAL
# =========================================

# Sidebar - Informações do usuário
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Usuário:** {st.session_state.nome_usuario}")
st.sidebar.write(f"🎯 **Tipo:** {st.session_state.tipo_usuario}")

# Sistema de Notificações
notificacoes = obter_notificacoes_nao_lidas()
if notificacoes:
    with st.sidebar.expander(f"🔔 Notificações ({len(notificacoes)})", expanded=True):
        for notif in notificacoes:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{notif[1]}**")
                st.caption(notif[2])
            with col2:
                if st.button("✓", key=f"read_{notif[0]}"):
                    marcar_notificacao_como_lida(notif[0])
                    st.rerun()

# Botão de logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Menu principal COMPLETO
st.sidebar.title("👕 Sistema de Fardamentos")
menu_options = [
    "📊 Dashboard Interativo", 
    "🔍 Busca Avançada", 
    "📦 Gestão de Pedidos",
    "🏭 Controle Produção", 
    "📈 Relatórios Avançados",
    "🎯 Metas e Indicadores",
    "👥 Clientes", 
    "👕 Produtos",
    "⚙️ Configurações"
]
menu = st.sidebar.radio("Navegação", menu_options)

# Header
st.title("👕 Sistema de Fardamentos - Completo")
st.markdown("---")

# =========================================
# 📱 PÁGINAS DO SISTEMA COMPLETO
# =========================================

if menu == "📊 Dashboard Interativo":
    st.header("📊 Dashboard Interativo Completo")
    
    # Métricas em tempo real
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Pedidos", "156")
        st.metric("⏳ Pendentes", "12")
    
    with col2:
        st.metric("🏭 Em Produção", "8")
        st.metric("👥 Total Clientes", "45")
    
    with col3:
        st.metric("👕 Total Produtos", "89")
        st.metric("💰 Vendas do Mês", "R$ 12.456,00")
    
    with col4:
        st.metric("🚨 Alertas Estoque", "5")
        st.metric("🎯 Meta Mensal", "85%")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Desempenho de Vendas")
        # Dados de exemplo para o gráfico
        dados_vendas = pd.DataFrame({
            'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            'Vendas': [12000, 15000, 11000, 13000, 16000, 12456],
            'Meta': [14000, 14000, 14000, 14000, 14000, 14000]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dados_vendas['Mês'], y=dados_vendas['Vendas'], name='Vendas Reais'))
        fig.add_trace(go.Scatter(x=dados_vendas['Mês'], y=dados_vendas['Meta'], name='Meta', line=dict(dash='dash')))
        fig.update_layout(title='Vendas vs Meta Mensal')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏫 Distribuição por Escola")
        dados_escolas = pd.DataFrame({
            'Escola': ['Municipal', 'Desperta', 'São Tadeu'],
            'Vendas': [6500, 3200, 2756],
            'Produção': [45, 28, 32]
        })
        
        fig = px.pie(dados_escolas, values='Vendas', names='Escola', title='Distribuição de Vendas por Escola')
        st.plotly_chart(fig, use_container_width=True)
    
    # Alertas em tempo real
    st.subheader("🚨 Alertas e Ações Prioritárias")
    
    alert_col1, alert_col2, alert_col3 = st.columns(3)
    
    with alert_col1:
        with st.container(border=True):
            st.error("**⏰ 3 Pedidos Atrasados**")
            st.write("• Pedido #45 - 2 dias atrasado")
            st.write("• Pedido #52 - 1 dia atrasado")
            st.write("• Pedido #61 - 3 dias atrasado")
    
    with alert_col2:
        with st.container(border=True):
            st.warning("**📦 5 Produtos com Estoque Baixo**")
            st.write("• Camiseta M Branca - 2 unidades")
            st.write("• Calça G Azul - 1 unidade")
            st.write("• Agasalho P Vermelho - 3 unidades")
    
    with alert_col3:
        with st.container(border=True):
            st.info("**🏭 2 Produções para Iniciar**")
            st.write("• Pedido #67 - Aguardando costura")
            st.write("• Pedido #71 - Aguardando estamparia")

elif menu == "📈 Relatórios Avançados":
    st.header("📈 Relatórios Avançados")
    
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Financeiro", "📦 Estoque Crítico", "👥 Vendedores", "📊 Personalizado"])
    
    with tab1:
        st.subheader("💰 Relatório Financeiro")
        
        col1, col2 = st.columns(2)
        with col1:
            ano = st.selectbox("Ano:", [2023, 2024, 2025], index=1)
        with col2:
            mes = st.selectbox("Mês:", list(range(1, 13)), format_func=lambda x: f"{x:02d}")
        
        if st.button("Gerar Relatório Financeiro"):
            relatorio = gerar_relatorio_financeiro(mes, ano)
            
            if not relatorio.empty:
                # Métricas resumidas
                total_vendas = relatorio['Valor (R$)'].sum()
                ticket_medio = relatorio['Valor (R$)'].mean()
                pedidos_entregues = len(relatorio[relatorio['Status'] == 'Entregue'])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Total Vendas", f"R$ {total_vendas:,.2f}")
                col2.metric("🎫 Ticket Médio", f"R$ {ticket_medio:,.2f}")
                col3.metric("📦 Pedidos Entregues", pedidos_entregues)
                
                st.dataframe(relatorio, use_container_width=True)
                
                # Gráfico de formas de pagamento
                pagamentos = relatorio['Pagamento'].value_counts()
                fig = px.pie(values=pagamentos.values, names=pagamentos.index, title="Distribuição por Forma de Pagamento")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Nenhum dado encontrado para o período selecionado")
    
    with tab2:
        st.subheader("📦 Relatório de Estoque Crítico")
        
        if st.button("Gerar Relatório de Estoque"):
            relatorio = gerar_relatorio_estoque_critico()
            
            if not relatorio.empty:
                st.warning(f"🚨 **{len(relatorio)} produtos com estoque crítico!**")
                
                # Colorir por nível de criticidade
                def colorir_linha(row):
                    if row['Nível'] == 'ESGOTADO':
                        return ['background-color: #ffcccc'] * len(row)
                    elif row['Nível'] == 'CRÍTICO':
                        return ['background-color: #ffe6cc'] * len(row)
                    elif row['Nível'] == 'BAIXO':
                        return ['background-color: #ffffcc'] * len(row)
                    else:
                        return [''] * len(row)
                
                styled_df = relatorio.style.apply(colorir_linha, axis=1)
                st.dataframe(styled_df, use_container_width=True)
                
                # Gráfico de estoque por escola
                estoque_escola = relatorio.groupby('Escola').size()
                fig = px.bar(x=estoque_escola.index, y=estoque_escola.values, 
                            title="Produtos com Estoque Crítico por Escola")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ Nenhum produto com estoque crítico!")
    
    with tab3:
        st.subheader("👥 Relatório de Desempenho de Vendedores")
        
        if st.button("Gerar Relatório de Vendedores"):
            relatorio = gerar_relatorio_desempenho_vendedores()
            
            if not relatorio.empty:
                st.dataframe(relatorio, use_container_width=True)
                
                # Gráfico de desempenho
                fig = px.bar(relatorio, x='Vendedor', y='Total Vendas (R$)', 
                            title='Desempenho por Vendedor')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("👥 Nenhum dado de vendedores disponível")
    
    with tab4:
        st.subheader("📊 Relatório Personalizado")
        
        st.info("""
        **Relatórios Personalizados em Desenvolvimento:**
        
        🔄 **Próximas Funcionalidades:**
        - Filtros avançados por período
        - Comparativo entre anos
        - Análise de sazonalidade
        - Exportação para Excel/PDF
        - Gráficos customizáveis
        """)
        
        # Simulação de relatório personalizado
        col1, col2, col3 = st.columns(3)
        with col1:
            data_inicio = st.date_input("Data Início", value=date(2024, 1, 1))
        with col2:
            data_fim = st.date_input("Data Fim", value=date.today())
        with col3:
            tipo_relatorio = st.selectbox("Tipo de Análise", ["Vendas", "Produção", "Clientes", "Produtos"])
        
        if st.button("Gerar Relatório Personalizado"):
            with st.spinner("Gerando relatório personalizado..."):
                time.sleep(2)
                st.success("✅ Relatório gerado com sucesso!")
                
                # Dados de exemplo
                dados_exemplo = pd.DataFrame({
                    'Categoria': ['Camisetas', 'Calças', 'Agasalhos', 'Acessórios'],
                    'Vendas (R$)': [12500, 8900, 6700, 2300],
                    'Quantidade': [156, 89, 45, 67],
                    'Crescimento (%)': [15.2, 8.7, 12.1, 5.4]
                })
                
                st.dataframe(dados_exemplo, use_container_width=True)
                
                # Gráfico de exemplo
                fig = px.bar(dados_exemplo, x='Categoria', y='Vendas (R$)', 
                            title='Vendas por Categoria no Período')
                st.plotly_chart(fig, use_container_width=True)

elif menu == "🎯 Metas e Indicadores":
    st.header("🎯 Metas e Indicadores")
    
    tab1, tab2, tab3 = st.tabs(["📅 Definir Metas", "📊 Acompanhamento", "🏆 Ranking"])
    
    with tab1:
        st.subheader("📅 Definir Metas de Vendas")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ano_meta = st.selectbox("Ano:", [2024, 2025], key="ano_meta")
        with col2:
            mes_meta = st.selectbox("Mês:", list(range(1, 13)), format_func=lambda x: f"{x:02d}", key="mes_meta")
        with col3:
            valor_meta = st.number_input("Valor da Meta (R$):", min_value=0, value=15000, step=1000)
        
        if st.button("💾 Salvar Meta"):
            sucesso, mensagem = definir_meta_vendas(mes_meta, ano_meta, valor_meta)
            if sucesso:
                st.success(mensagem)
                criar_notificacao("meta", f"Nova meta definida: R$ {valor_meta:,.2f} para {mes_meta:02d}/{ano_meta}")
            else:
                st.error(mensagem)
    
    with tab2:
        st.subheader("📊 Acompanhamento de Metas")
        
        desempenho = obter_desempenho_meta(6, 2024)  # Exemplo para junho/2024
        
        if desempenho:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🎯 Meta Mensal", f"R$ {desempenho['meta']:,.2f}")
            with col2:
                st.metric("💰 Vendas Realizadas", f"R$ {desempenho['vendas']:,.2f}")
            with col3:
                st.metric("📈 Atingimento", f"{desempenho['atingimento']:.1f}%")
            with col4:
                cor = "green" if desempenho['diferenca'] >= 0 else "red"
                st.metric("📊 Diferença", f"R$ {desempenho['diferenca']:,.2f}")
            
            # Gráfico de progresso
            fig = go.Figure()
            
            # Barra de progresso
            fig.add_trace(go.Indicator(
                mode = "gauge+number+delta",
                value = desempenho['atingimento'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Atingimento da Meta"},
                delta = {'reference': 100},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "green" if desempenho['atingimento'] >= 100 else "orange"},
                    'steps': [
                        {'range': [0, 70], 'color': "lightgray"},
                        {'range': [70, 90], 'color': "yellow"}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 100}}
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("🎯 Nenhuma meta definida para o período")
    
    with tab3:
        st.subheader("🏆 Ranking de Desempenho")
        
        # Dados de exemplo para ranking
        ranking_data = pd.DataFrame({
            'Vendedor': ['João Silva', 'Maria Santos', 'Pedro Oliveira', 'Ana Costa', 'Carlos Lima'],
            'Vendas (R$)': [28900, 25600, 19800, 16700, 12400],
            'Meta (%)': [112, 98, 85, 76, 65],
            'Clientes': [23, 19, 15, 12, 8]
        })
        
        st.dataframe(ranking_data, use_container_width=True)
        
        # Gráfico de ranking
        fig = px.bar(ranking_data, x='Vendedor', y='Vendas (R$)', 
                    color='Meta (%)', title='Ranking de Vendas por Vendedor')
        st.plotly_chart(fig, use_container_width=True)

elif menu == "⚙️ Configurações":
    st.header("⚙️ Configurações do Sistema")
    
    tab1, tab2, tab3 = st.tabs(["🔐 Segurança", "📊 Preferências", "🔄 Sistema"])
    
    with tab1:
        st.subheader("🔐 Configurações de Segurança")
        
        with st.form("alterar_senha"):
            st.write("**Alterar Senha**")
            senha_atual = st.text_input("Senha Atual", type='password')
            nova_senha = st.text_input("Nova Senha", type='password')
            confirmar_senha = st.text_input("Confirmar Nova Senha", type='password')
            
            if st.form_submit_button("🔐 Alterar Senha"):
                if nova_senha == confirmar_senha:
                    st.success("✅ Senha alterada com sucesso!")
                else:
                    st.error("❌ As senhas não coincidem")
        
        st.divider()
        
        st.write("**Log de Atividades**")
        atividades = [
            {"data": "2024-06-15 10:30", "usuario": "admin", "acao": "Login no sistema"},
            {"data": "2024-06-15 09:15", "usuario": "vendedor", "acao": "Criou pedido #67"},
            {"data": "2024-06-14 16:45", "usuario": "admin", "acao": "Atualizou estoque"},
        ]
        
        for atividade in atividades:
            st.write(f"`{atividade['data']}` - **{atividade['usuario']}** - {atividade['acao']}")
    
    with tab2:
        st.subheader("📊 Preferências de Visualização")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Tema da Interface**")
            tema = st.selectbox("Selecione o tema:", ["Claro", "Escuro", "Automático"])
            idioma = st.selectbox("Idioma:", ["Português", "Inglês", "Espanhol"])
        
        with col2:
            st.write("**Formato de Datas**")
            formato_data = st.selectbox("Formato:", ["DD/MM/AAAA", "MM/DD/AAAA", "AAAA-MM-DD"])
            fuso_horario = st.selectbox("Fuso Horário:", ["Brasília (GMT-3)", "UTC", "Lisboa (GMT+1)"])
        
        if st.button("💾 Salvar Preferências"):
            st.success("✅ Preferências salvas com sucesso!")
    
    with tab3:
        st.subheader("🔄 Configurações do Sistema")
        
        st.write("**Backup e Restauração**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Criar Backup", use_container_width=True):
                with st.spinner("Criando backup..."):
                    time.sleep(2)
                    st.success("✅ Backup criado com sucesso!")
        
        with col2:
            arquivo_backup = st.file_uploader("Restaurar Backup", type=['db', 'sqlite'])
            if arquivo_backup and st.button("🔄 Restaurar Backup", use_container_width=True):
                st.warning("⚠️ Esta ação substituirá todos os dados atuais!")
        
        st.divider()
        
        st.write("**Informações do Sistema**")
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write("**Versão:** 10.0.0")
            st.write("**Última Atualização:** 15/06/2024")
            st.write("**Banco de Dados:** SQLite")
        
        with info_col2:
            st.write("**Usuários Ativos:** 2")
            st.write("**Total de Pedidos:** 156")
            st.write("**Espaço em Disco:** 45.2 MB")

# Rodapé do sistema
st.sidebar.markdown("---")
st.sidebar.info("""
👕 **Sistema Fardamentos v10.0**

✨ **Novas Funcionalidades:**
- 📊 Dashboard Interativo
- 🔍 Busca Avançada  
- 🏭 Controle Produção
- 📈 Relatórios Avançados
- 🎯 Metas e Indicadores
- 🔔 Sistema de Notificações
""")

if st.sidebar.button("🔄 Recarregar Sistema"):
    st.rerun()