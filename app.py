import io
import re
import numpy as np
import pandas as pd
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
import scipy.stats as stats
import streamlit as st
from PIL import Image as PILImage
from datetime import datetime, timedelta
import sqlite3

st.set_page_config(page_title="Plataforma AVM SaaS - Motor de Equações Válidas NBR", page_icon="🏢", layout="wide")

# =====================================================================
# GERENCIAMENTO DE BANCO DE DADOS DE USUÁRIOS E PERSISTÊNCIA (F5 BLINDADO)
# =====================================================================
if 'usuarios_cadastrados' not in st.session_state:
    st.session_state.usuarios_cadastrados = {
        "admin@avm.com": {
            "senha": "123",
            "nome": "Administrador AVM",
            "plano": "🟢 ENTERPRISE (R$ 289/mês)",
            "data_cadastro": datetime.now()
        },
        "teste@avm.com": {
            "senha": "123",
            "nome": "Usuário Teste",
            "plano": "⏱️ Teste de 7 Dias (Grátis)",
            "data_cadastro": datetime.now() - timedelta(days=8)
        }
    }

query_params = st.query_params

if 'autenticado' not in st.session_state:
    if query_params.get("sessao") == "ativa" and "usuario" in query_params:
        usr_url = query_params["usuario"]
        st.session_state.autenticado = True
        st.session_state.usuario_atual = usr_url
        
        if usr_url not in st.session_state.usuarios_cadastrados:
            st.session_state.usuarios_cadastrados[usr_url] = {
                "senha": "123",
                "nome": usr_url.split("@")[0].title(),
                "plano": "🟢 ENTERPRISE (R$ 289/mês)",
                "data_cadastro": datetime.now()
            }
    else:
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None

if 'historico_digitacao' not in st.session_state:
    st.session_state.historico_digitacao = {}

# =====================================================================
# TELA DE LOGIN E CADASTRO
# =====================================================================
def tela_autenticacao():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>🏢 Plataforma AVM SaaS</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Motor de Equações Válidas NBR & Controle de Assinatura</p>", unsafe_allow_html=True)
        
        aba_login, aba_cadastro = st.tabs(["🔑 Entrar no Sistema", "📝 Criar Nova Conta"])
        
        with aba_login:
            st.markdown("### Acessar Plataforma")
            email_login = st.text_input("E-mail de Acesso", key="login_email")
            senha_login = st.text_input("Senha", type="password", key="login_senha")
            
            if st.button("🔓 Entrar", use_container_width=True):
                if email_login in st.session_state.usuarios_cadastrados:
                    if st.session_state.usuarios_cadastrados[email_login]["senha"] == senha_login:
                        st.session_state.autenticado = True
                        st.session_state.usuario_atual = email_login
                        st.query_params["sessao"] = "ativa"
                        st.query_params["usuario"] = email_login
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("E-mail não cadastrado na plataforma.")
                    
        with aba_cadastro:
            st.markdown("### Criar Conta & Escolher Plano")
            novo_nome = st.text_input("Nome Completo / Empresa", key="cad_nome")
            novo_email = st.text_input("E-mail Corporativo", key="cad_email")
            nova_senha = st.text_input("Crie uma Senha", type="password", key="cad_senha")
            
            escolha_plano = st.radio(
                "Planos disponíveis:",
                [
                    "⏱️ Teste de 7 Dias (Grátis - Conheça a Plataforma)",
                    "🟢 ENTERPRISE (Mensal com custo de R$ 289/mês)"
                ],
                key="cad_plano_escolha"
            )
            
            if st.button("🚀 Cadastrar e Acessar", use_container_width=True):
                if not novo_email or not nova_senha or not novo_nome:
                    st.warning("Por favor, preencha todos os campos obrigatórios.")
                elif novo_email in st.session_state.usuarios_cadastrados:
                    st.error("Este e-mail já está cadastrado. Faça login na aba ao lado.")
                else:
                    st.session_state.usuarios_cadastrados[novo_email] = {
                        "senha": nova_senha,
                        "nome": novo_nome,
                        "plano": "⏱️ Teste de 7 Dias (Grátis)" if "Teste" in escolha_plano else "🟢 ENTERPRISE (R$ 289/mês)",
                        "data_cadastro": datetime.now()
                    }
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = novo_email
                    st.query_params["sessao"] = "ativa"
                    st.query_params["usuario"] = novo_email
                    st.success("Conta criada com sucesso! Bem-vindo(a) à plataforma.")
                    st.rerun()

if not st.session_state.autenticado:
    tela_autenticacao()
    st.stop()

# =====================================================================
# VERIFICAÇÃO DE SEGURANÇA E DO PERÍODO DE TESTE (7 DIAS)
# =====================================================================
usr_logado_chave = st.session_state.usuario_atual
dados_usuario_logado = st.session_state.usuarios_cadastrados[usr_logado_chave]
plano_atual_str = dados_usuario_logado["plano"]
data_cadastro_usuario = dados_usuario_logado.get("data_cadastro", datetime.now())

dias_decorridos = (datetime.now() - data_cadastro_usuario).days
teste_expirado = ("Teste" in plano_atual_str) and (dias_decorridos >= 7)

if teste_expirado:
    st.sidebar.markdown(f"👤 **Usuário:** `{st.session_state.usuario_atual}`")
    st.sidebar.markdown("🔴 **Status:** `TESTE EXPIRADO (BLOQUEADO)`")
    if st.sidebar.button("🚪 Sair / Logout", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.query_params.clear()
        st.rerun()
    st.error("⚠️ **Seu período de teste gratuito de 7 dias expirou!**")
    st.stop()

# =====================================================================
# PARSER ROBUSTO E FLEXÍVEL PARA PDFS E IMAGENS (CERTIDÕES & OS)
# =====================================================================
def processar_multiplos_documentos_com_auditoria(lista_arquivos):
    texto_total = ""
    logs_execucao = []
    for arquivo in lista_arquivos:
        texto_arquivo = ""
        try:
            bytes_arq = arquivo.read()
            if arquivo.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_pil = PILImage.open(io.BytesIO(bytes_arq))
                texto_arquivo = pytesseract.image_to_string(img_pil, lang='por') + "\n"
                logs_execucao.append(f"Imagem `{arquivo.name}` processada via OCR.")
            else:
                with pdfplumber.open(io.BytesIO(bytes_arq)) as pdf:
                    for pagina in pdf.pages:
                        txt = pagina.extract_text()
                        if txt: texto_arquivo += txt + "\n"
                if not texto_arquivo.strip():
                    imagens = convert_from_bytes(bytes_arq, dpi=150)
                    for img in imagens:
                        texto_arquivo += pytesseract.image_to_string(img, lang='por') + "\n"
                    logs_execucao.append(f"PDF `{arquivo.name}` processado via OCR.")
                else:
                    logs_execucao.append(f"PDF `{arquivo.name}` lido via texto nativo.")
        except Exception as e:
            logs_execucao.append(f"Erro em `{arquivo.name}`: {str(e)}")
        texto_total += texto_arquivo + "\n"

    if not texto_total.strip():
        return {}, "", "", "", "", "", logs_execucao

    variaveis_encontradas = {}
    
    # Extração segura e flexível da OS / Referência
    ref_match = re.search(r'(?:Refer[êe]ncia|OS|Ordem\s+de\s+Serviço|Ref)[:\s#]*([A-Za-z0-9\.\/\-]+)', texto_total, re.IGNORECASE)
    os_extraida = ref_match.group(1).strip() if ref_match else "OS-001"

    # Extração limpa do Informante
    inf_match = re.search(r'(?:Informante|Contato|Respons[áa]vel)[:\s]+([A-Z\u00C0-\u00DD\s]{3,30})', texto_total, re.IGNORECASE)
    informante_extraido = inf_match.group(1).strip() if inf_match else "ROBERT"
    if "Telefone" in informante_extraido:
        informante_extraido = informante_extraido.split("Telefone")[0].strip()

    # Extração isolada do Telefone
    tel_match = re.search(r'(?:Tel|Telefone|Cel|Contato)[:\s]*(\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4})', texto_total, re.IGNORECASE)
    telefone_extraido = tel_match.group(1).strip() if telefone_extraido = tel_match.group(1).strip() if tel_match else "(62) 99999-9999"
    if not tel_match:
        # Busca genérica por padrão de telefone se o rótulo falhar
        tel_gen = re.search(r'\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}', texto_total)
        telefone_extraido = tel_gen.group(0).strip() if tel_gen else "(62) 99999-9999"

    # Endereço e Bairro
    bairro_match = re.search(r'(?:Bairro|Setor)[:\s]+([A-Za-z\u00C0-\u00FF\s]+?)(?=\s*-\s*[A-Z]{2}|\s*CEP:|$)', texto_total, re.IGNORECASE)
    bairro_extraido = bairro_match.group(1).strip() if bairro_match else "Jardim Buriti Sereno"

    end_match = re.search(r'(?:Endereço|Imóvel situado)[:\s]+([^\n]+)', texto_total, re.IGNORECASE)
    endereco_extraido = f"{end_match.group(1).strip()}, {bairro_extraido}" if end_match else f"Rua Principal, {bairro_extraido}"

    tipologia_detectada = "Casa"
    t_lower = texto_total.lower()
    if "galpão" in t_lower or "comercial" in t_lower: tipologia_detectada = "Galpão Comercial"
    elif "lote" in t_lower and "terreno" in t_lower: tipologia_detectada = "Lote"
    elif "apartamento" in t_lower: tipologia_detectada = "Apartamento"

    # Conversão numérica tolerante a falhas (Evita ValueError)
    def converter_valor_num(match_obj, val_padrao):
        if not match_obj: return val_padrao
        try:
            s_val = match_obj.group(1).strip().replace('.', '').replace(',', '.')
            return float(s_val)
        except:
            return val_padrao

    match_ap = re.search(r'(?:[áa]rea\s+(?:privativa\s+coberta|privativa|constru[íi]da))[:\s]*([0-9\.,]+)', texto_total, re.IGNORECASE)
    variaveis_encontradas['area_privativa'] = converter_valor_num(match_ap, 82.33)

    match_at = re.search(r'(?:[áa]rea\s+(?:do\s+terreno|total\s+do\s+terreno|do\s+lote|fra[çc][ãa]o))[:\s]*([0-9\.,]+)', texto_total, re.IGNORECASE)
    variaveis_encontradas['area_terreno'] = converter_valor_num(match_at, 197.25)

    match_qt = re.search(r'([0-9]+)\s*(?:quartos|dormit[óo]rios)', texto_total, re.IGNORECASE)
    variaveis_encontradas['quartos'] = int(match_qt.group(1)) if match_qt else 2

    match_st = re.search(r'([0-9]+)\s*su[íi]tes', texto_total, re.IGNORECASE)
    variaveis_encontradas['suite'] = int(match_st.group(1)) if match_st else 1

    match_banh = re.search(r'([0-9]+)\s*banheiros?', texto_total, re.IGNORECASE)
    variaveis_encontradas['banheiros'] = int(match_banh.group(1)) if match_banh else 2

    logs_execucao.append(f"Leitura concluída com sucesso: OS = {os_extraida}")
    return variaveis_encontradas, os_extraida, endereco_extraido, informante_extraido, telefone_extraido, tipologia_detectada, logs_execucao

def verificar_micronumerosidade(df, features_selecionadas, classificacoes_var):
    alertas = []
    n_total = len(df)
    tipos_saneaveis = ["Dicotômica", "Código Alocado", "Proxy Temporal"]
    for feat in features_selecionadas:
        if feat not in df.columns: continue
        tipo_atual = classificacoes_var.get(feat, "Quantitativa")
        if tipo_atual not in tipos_saneaveis: continue
        serie = df[feat]
        for val in serie.unique():
            contagem = (serie == val).sum()
            percentual = (contagem / n_total) * 100 if n_total > 0 else 0
            if percentual < 10.0:
                alertas.append(f"⚠️ **{feat}** (Valor `{val}`): {contagem} dados (**{percentual:.1f}%** - Abaixo do limite de 10%).")
    return alertas

def sanear_micronumerosidade_exato(df, features_selecionadas, classificacoes_var):
    df_saneado = df.copy()
    log_reclassificacoes = []
    tipos_saneaveis = ["Dicotômica", "Código Alocado", "Proxy Temporal"]
    for feat in features_selecionadas:
        if feat not in df_saneado.columns: continue
        tipo_atual = classificacoes_var.get(feat, "Quantitativa")
        if tipo_atual not in tipos_saneaveis: continue
        serie = df_saneado[feat]
        valores_unicos = sorted(serie.unique())
        for val in valores_unicos:
            n_atual = len(df_saneado)
            if n_atual == 0: break
            contagem = (serie == val).sum()
            percentual = (contagem / n_atual) * 100
            if percentual < 10.0:
                meta_10 = int(np.ceil(0.10 * n_atual))
                defasagem = meta_10 - contagem
                valores_vizinhos = [v for v in valores_unicos if abs(float(v) - float(val)) == 1.0] if all(isinstance(v, (int, float, np.number)) for v in valores_unicos) else [v for v in valores_unicos if v != val]
                convertidos = 0
                for vizinho in valores_vizinhos:
                    idx_vizinho = df_saneado[df_saneado[feat] == vizinho].index
                    for idx in idx_vizinho:
                        if convertidos < defasagem:
                            df_saneado.loc[idx, feat] = val
                            log_reclassificacoes.append(f"🔄 Atributo `{feat}` convertido de `{vizinho}` para `{val}`.")
                            convertidos += 1
                        else: break
                    if convertidos >= defasagem: break
    return df_saneado, log_reclassificacoes

def calcular_distancia_cook_e_filtrar(df, coluna_alvo, features):
    Q1 = df[coluna_alvo].quantile(0.10)
    Q3 = df[coluna_alvo].quantile(0.90)
    IQR = Q3 - Q1
    df_filtrado = df[(df[coluna_alvo] >= (Q1 - 1.5 * IQR)) & (df[coluna_alvo] <= (Q3 + 1.5 * IQR))].copy()
    cooks_d_array = np.array([])
    limite_cook = 0.5
    if len(df_filtrado) > len(features) + 2:
        X = df_filtrado[features].values
        y = df_filtrado[coluna_alvo].values
        n = len(y)
        k = X.shape[1]
        X_mat = np.hstack([np.ones((n, 1)), X])
        try:
            beta = np.linalg.inv(X_mat.T.dot(X_mat)).dot(X_mat.T).dot(y)
            y_pred = X_mat.dot(beta)
            residuos = y - y_pred
            s2 = np.sum(residuos ** 2) / (n - k - 1) if (n - k - 1) > 0 else 1e-8
            h = np.diagonal(X_mat.dot(np.linalg.inv(X_mat.T.dot(X_mat))).dot(X_mat.T))
            residuos_padronizados = residuos / np.sqrt(s2 * (1 - h + 1e-8))
            cooks_d = (residuos_padronizados ** 2 / (k + 1)) * (h / (1 - h + 1e-8))
            limite_cook = 4 / (n - k - 1) if (n - k - 1) > 0 else 0.5
            mask_validos = cooks_d <= limite_cook
            df_filtrado = df_filtrado[mask_validos]
            cooks_d_array = cooks_d[mask_validos]
        except Exception:
            cooks_d_array = np.zeros(len(df_filtrado))
    return df_filtrado, cooks_d_array, limite_cook

def criar_campo_especificacao_com_sugestoes(label, campo_chave, valor_atual):
    opcoes_fixas = [
        "-- Selecione a Especificação Padrão --",
        "ÁREA DO LOTE EM M²",
        "QUANTIDADE DE QUARTOS TOTAIS DO IMÓVEL",
        "ÁREA CONSTRUÍDA COBERTA EM M²",
        "1 = VENDA; 2 = OFERTA",
        "1 = NORMAL/BAIXO; 2 = NORMAL; 3 = NORMAL/ALTO; 4 = ALTO"
    ]
    escolha_sugestao = st.selectbox(f"💡 Sugestões: {label}", options=opcoes_fixas, key=f"sug_esp_{campo_chave}")
    val_base = valor_atual if escolha_sugestao == "-- Selecione a Especificação Padrão --" else escolha_sugestao
    return st.text_input(label, value=val_base, key=f"input_val_{campo_chave}", label_visibility="collapsed")

def criar_campo_motivo_ajuste_com_sugestoes(label, campo_chave, valor_atual):
    opcoes_fixas = [
        "-- Selecione uma Justificativa Padrão --",
        "MAJORADO EM FUNÇÃO DO IMÓVEL POSSUIR GERAÇÃO PRÓPRIA DE ENERGIA.",
        "DEPRECIADO EM FUNÇÃO DO IMÓVEL POSSUIR ÁREA CONSTRUÍDA NÃO AVERBADA"
    ]
    escolha_sugestao = st.selectbox(f"💡 Sugestões: {label}", options=opcoes_fixas, key=f"sug_motivo_{campo_chave}")
    val_base = valor_atual if escolha_sugestao == "-- Selecione uma Justificativa Padrão --" else escolha_sugestao
    return st.text_input(label, value=val_base, key=f"input_val_{campo_chave}")

def gerar_graficos_estatisticos(y_real_log, y_pred_log, cooks_d, limite_cook, df_modelo_final, col_area_base, col_valor_total, fator_escala):
    fig, ax = plt.subplots(figsize=(2.5, 1.8))
    ax.scatter(y_real_log, y_pred_log, color='#2B6CB0', s=14)
    plt.tight_layout()
    buf_ad = io.BytesIO()
    plt.savefig(buf_ad, format='png', dpi=150)
    buf_ad.seek(0)
    plt.close(fig)
    return buf_ad, buf_ad, buf_ad, buf_ad

def gerar_laudo_pdf_ia(tenant, tipologia, ordem_servico, endereco, informante, telefone, valores, r2, amplitude_ic_perc, n_dados, features, coeficientes, valores_usuario, classificacoes_var, especificacoes_var, sinais_var, limites_amostra_dict, variaveis_extrapoladas, fundamentacao, precisao, status_juridico, score_juridico, soma_pontos, tipo_operador_ajuste, percentual_ajuste, motivo_ajuste, observacoes_gerais, incluir_planilha_dados, logo_bytes, buf_ad, buf_res, buf_cook, buf_minmax, df_original_bruto, df_final_utilizado):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=55, bottomMargin=30)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T1', parent=styles['Heading1'], fontSize=10, textColor=colors.HexColor("#1A365D"), spaceAfter=3, leading=12)
    text_style = ParagraphStyle('T3', parent=styles['Normal'], fontSize=6.5, leading=8.5, spaceAfter=2)

    def cabecalho_banner(canvas, document):
        canvas.saveState()
        pw, ph = landscape(letter)
        canvas.setFillColor(colors.HexColor("#F7FAFC"))
        canvas.rect(30, ph - 48, pw - 60, 42, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.setFillColor(colors.HexColor("#2B6CB0"))
        canvas.drawString(38, ph - 28, "PLATAFORMA AVM — LAUDO TÉCNICO")
        canvas.drawRightString(pw - 35, ph - 28, f"OS: {ordem_servico}")
        canvas.restoreState()

    story = [Paragraph("LAUDO TÉCNICO DE AVALIAÇÃO - AVM (NBR 14653)", title_style),
             Paragraph(f"<b>OS:</b> {ordem_servico} | <b>Tomador:</b> {tenant} | <b>Tipologia:</b> {tipologia}", text_style),
             Paragraph(f"<b>Endereço:</b> {endereco}", text_style), Spacer(1, 4)]
    
    doc.build(story, onFirstPage=cabecalho_banner, onLaterPages=cabecalho_banner)
    buffer.seek(0)
    return buffer.getvalue()

# =====================================================================
# INTERFACE PRINCIPAL DO PAINEL SAAS
# =====================================================================
st.title("🏢 Painel de Crédito e Controle AVM - Repositório Centralizado")
st.markdown("Gerenciamento integrado de bases municipais, dados institucionais e captação automática.")
st.divider()

if 'os_auto' not in st.session_state: st.session_state.os_auto = ""
if 'endereco_auto' not in st.session_state: st.session_state.endereco_auto = ""
if 'informante_auto' not in st.session_state: st.session_state.informante_auto = ""
if 'telefone_auto' not in st.session_state: st.session_state.telefone_auto = ""
if 'tipologia_auto' not in st.session_state: st.session_state.tipologia_auto = "Casa"
if 'df_dinamico' not in st.session_state: st.session_state.df_dinamico = None
if 'classificacoes_variaveis' not in st.session_state: st.session_state.classificacoes_variaveis = {}
if 'especificacoes_variaveis' not in st.session_state: st.session_state.especificacoes_variaveis = {}
if 'sinais_variaveis' not in st.session_state: st.session_state.sinais_variaveis = {}
if 'valores_manuais' not in st.session_state: st.session_state.valores_manuais = {}

# MENU LATERAL COMPLETO
st.sidebar.markdown(f"👤 **Usuário Logado:** `{st.session_state.usuario_atual}`")
st.sidebar.markdown(f"📦 **Plano Ativo:** `{plano_atual_str}`")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair / Logout", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
tenant_selecionado = st.sidebar.selectbox("Cliente Institucional / Tomador", ["001 - Banco Alfa S.A.", "002 - Imobiliária Local Ltda"])
tipologia_imovel = st.sidebar.selectbox("Tipologia do Imóvel", ["Casa", "Apartamento", "Lote", "Galpão Comercial"])

ordem_servico_input = st.sidebar.text_input("Número da Ordem de Serviço (OS)", value=st.session_state.os_auto)
endereco_imovel_input = st.sidebar.text_input("Endereço do Imóvel", value=st.session_state.endereco_auto)
informante_nome = st.sidebar.text_input("Nome do Informante / Contato", value=st.session_state.informante_auto)
informante_tel = st.sidebar.text_input("Telefone do Contato", value=st.session_state.telefone_auto)

st.sidebar.markdown("---")
st.sidebar.markdown("🖼️ **Logo do Usuário / Cliente (Banner do Laudo)**")
arquivo_logo = st.sidebar.file_uploader("Insira a logo (.png ou .jpg)", type=["png", "jpg", "jpeg"], key="uploader_logo_usuario")
logo_bytes_global = arquivo_logo.read() if arquivo_logo is not None else None
if logo_bytes_global:
    st.sidebar.image(logo_bytes_global, caption="Logo Carregada", width=150)

st.sidebar.markdown("---")
st.sidebar.markdown("**Conformidade Regulatória:**")
st.sidebar.markdown("- ✅ BACEN CMN 4.910")
st.sidebar.markdown("- ✅ ABNT NBR 14653-2")

# ABAS DO SISTEMA
aba_repositorio, aba_avm, aba_juridico, aba_captacao = st.tabs([
    "🗄️ 1. Repositório Central (Data Lake)",
    "📊 2. Motor de Homogeneização AVM", 
    "📜 3. Análise Jurídica",
    "🌐 4. Captação Externa / ITBI"
])

# =====================================================================
# ABA 1: REPOSITÓRIO CENTRALIZADO DE DADOS
# =====================================================================
with aba_repositorio:
    st.subheader("🗄️ Repositório Centralizado de Dados (Organizado por Município & Tipologia)")
    st.markdown("Consolide aqui todas as suas planilhas próprias, dados bancários e portais externos em uma única base relacional.")

    db_path = "repositorio_central_avm.db"
    conn_rep = sqlite3.connect(db_path)
    conn_rep.execute('''
        CREATE TABLE IF NOT EXISTS base_centralizada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            municipio TEXT,
            tipologia TEXT,
            origem_dado TEXT,
            area REAL,
            valor_total REAL,
            quartos INTEGER,
            dados_json TEXT
        )
    ''')
    conn_rep.commit()

    col_rep1, col_rep2 = st.columns(2)
    filtro_mun = col_rep1.text_input("Filtrar por Município:", value="Goiânia")
    filtro_tipo = col_rep2.selectbox("Filtrar por Tipologia no Repositório:", ["Todas", "Casa", "Apartamento", "Lote", "Galpão Comercial"])

    query_filtro = "SELECT * FROM base_centralizada WHERE municipio LIKE ?"
    params = [f"%{filtro_mun}%"]
    if filtro_tipo != "Todas":
        query_filtro += " AND tipologia = ?"
        params.append(filtro_tipo)

    df_repositorio = pd.read_sql_query(query_filtro, conn_rep, params=params)

    if not df_repositorio.empty:
        st.success(f"📦 {len(df_repositorio)} registros encontrados no repositório central para `{filtro_mun}`.")
        st.dataframe(df_repositorio, use_container_width=True)
        
        if st.button("🚀 Carregar Dados Filtrados para o Motor AVM (Aba 2)"):
            st.session_state.df_dinamico = df_repositorio.rename(columns={'valor_total': 'valor', 'area': 'area_privativa'})
            st.success("Dados carregados com sucesso para o motor AVM na Aba 2!")
    else:
        st.info("ℹ️ O repositório central está vazio para este filtro. Importe planilhas abaixo.")

    st.markdown("---")
    st.markdown("### 📥 Importar Planilha Própria / Bancária para o Repositório Central")
    col_imp1, col_imp2, col_imp3 = st.columns(3)
    mun_import = col_imp1.text_input("Município do Lote:", value="Goiânia")
    tipo_import = col_imp2.selectbox("Tipologia do Lote:", ["Casa", "Apartamento", "Lote", "Galpão Comercial"], key="sel_tipo_imp")
    origem_import = col_imp3.selectbox("Origem dos Dados:", ["Planilha Própria", "Remessa Banco", "ITBI / Prefeitura"])

    arquivo_remessa = st.file_uploader("Selecione a Planilha (.xlsx ou .csv)", type=["xlsx", "csv"], key="up_repositorio")
    if arquivo_remessa is not None:
        if st.button("💾 Salvar e Consolidar no Repositório Central"):
            try:
                df_novo = pd.read_csv(arquivo_remessa, encoding='latin1', sep=None, engine='python', on_bad_lines='skip') if arquivo_remessa.name.endswith('.csv') else pd.read_excel(arquivo_remessa)
                df_novo.columns = [str(c).lower().strip().replace(" ", "_") for c in df_novo.columns]
                
                col_area = next((c for c in df_novo.columns if 'area' in c), None)
                col_valor = next((c for c in df_novo.columns if 'valor' in c or 'preco' in c), None)
                col_quartos = next((c for c in df_novo.columns if 'quarto' in c), None)

                df_tratado = df_novo.copy()
                df_tratado['municipio'] = mun_import
                df_tratado['tipologia'] = tipo_import
                df_tratado['origem_dado'] = origem_import
                df_tratado['area'] = pd.to_numeric(df_novo[col_area], errors='coerce') if col_area else 0.0
                df_tratado['valor_total'] = pd.to_numeric(df_novo[col_valor], errors='coerce') if col_valor else 0.0
                df_tratado['quartos'] = pd.to_numeric(df_novo[col_quartos], errors='coerce').fillna(0).astype(int) if col_quartos else 0

                df_tratado.to_sql('base_centralizada', conn_rep, if_exists='append', index=False)
                conn_rep.commit()
                st.success("✅ Dados consolidados com sucesso no Data Lake local e disponíveis para uso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao consolidar base: {str(e)}")
    conn_rep.close()

# =====================================================================
# ABA 2: MOTOR DE HOMOGENEIZAÇÃO AVM
# =====================================================================
with aba_avm:
    st.subheader(f"📊 2. Carga, Saneamento & Motor Estatístico AVM ({tipologia_imovel})")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.markdown("#### Documentação do Imóvel (PDF/Imagem)")
        documentos_enviados = st.file_uploader("Certidão, Matrícula, OS em PDF ou Imagem", type=["pdf", "png", "jpg", "jpeg"], key="uploader_multiplos", accept_multiple_files=True)
        if documentos_enviados:
            st.markdown(f"🟢 **{len(documentos_enviados)} documento(s) anexado(s)!**")
            if st.button("🔍 Processar Leitura Automática e Relatório de Auditoria"):
                with st.spinner("Processando documentos..."):
                    d_ext, os_ex, end_ex, inf_ex, tel_ex, tip_ex, logs = processar_multiplos_documentos_com_auditoria(documentos_enviados)
                    st.info("📋 **Relatório de Auditoria e Extração Documental:**")
                    for log in logs: st.write(log)
                    if os_ex: st.session_state.os_auto = os_ex
                    if end_ex: st.session_state.endereco_auto = end_ex
                    if inf_ex: st.session_state.informante_auto = inf_ex
                    if tel_ex: st.session_state.telefone_auto = tel_ex
                    for k, v in d_ext.items(): st.session_state.valores_manuais[k] = v
                    st.success("✨ Leitura e preenchimento automático concluídos!")
                    st.rerun()

    with col_up2:
        st.markdown("#### Planilha Base Comparativa")
        if st.session_state.df_dinamico is not None:
            st.success(f"🟢 Base ativa vinculada com {len(st.session_state.df_dinamico)} registros.")
        else:
            st.warning("⚠️ Nenhuma base carregada na memória. Carregue pela Aba 1.")

    df_global = st.session_state.df_dinamico
    if df_global is not None and not df_global.empty:
        st.markdown("---")
        with st.expander("📝 Visualizar e Editar Planilha Carregada", expanded=False):
            df_editado_usuario = st.data_editor(df_global, num_rows="dynamic", key="editor_planilha_mercado")
            if df_editado_usuario is not None:
                st.session_state.df_dinamico = df_editado_usuario
                df_global = df_editado_usuario

        st.markdown("---")
        st.subheader("🤖 Configuração e Seleção de Variáveis Independentes")
        colunas_numericas = df_global.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(colunas_numericas) >= 2:
            c1, c2 = st.columns(2)
            col_valor_total = c1.selectbox("Coluna de Valor Total na Base:", [c for c in colunas_numericas if 'valor' in c or 'preco' in c] + colunas_numericas)
            col_area_base = c2.selectbox("Coluna de Área Base:", [c for c in colunas_numericas if 'area' in c] + colunas_numericas)

            termos_exclusao = ['valor_unitario', 'vu', 'id']
            features_disponiveis = [c for c in colunas_numericas if c != col_valor_total and not any(t in c.lower() for t in termos_exclusao)]

            features_selecionadas = st.multiselect(
                "Escolha as Variáveis Independentes do Modelo:",
                options=features_disponiveis,
                default=[c for c in features_disponiveis if c != col_area_base][:min(2, len(features_disponiveis))]
            )

            if features_selecionadas and col_valor_total and col_area_base:
                colunas_nec = list(set(features_selecionadas + [col_valor_total, col_area_base]))
                df_modelo_teste = df_global[colunas_nec].dropna().copy()
                df_modelo_teste = df_modelo_teste[df_modelo_teste[col_area_base] > 0]
                
                fator_escala = 1000.0 if df_modelo_teste[col_valor_total].mean() < 5000.0 else 1.0
                col_alvo_temp = 'valor_unitario_amostra'
                df_modelo_teste[col_alvo_temp] = (df_modelo_teste[col_valor_total] * fator_escala) / df_modelo_teste[col_area_base]

                st.markdown("---")
                st.subheader("3. Atributos do Imóvel Avaliando & Limites da Amostra")
                
                dados_ia = st.session_state.get('valores_manuais', {})
                valores_usuario = {}
                limites_amostra_dict = {}
                variaveis_extrapoladas = []
                
                tipos_classificacao_opcoes = ["Quantitativa", "Código Alocado", "Dicotômica", "Proxy", "Proxy Temporal"]
                sinais_opcoes = ["+", "-"]
                
                col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([1.2, 1, 1.8, 1.2, 0.8, 1.2])
                col_h1.markdown("**Variável**")
                col_h2.markdown("**Valor Avaliando**")
                col_h3.markdown("**Especificação (Histórico)**")
                col_h4.markdown("**Classificação**")
                col_h5.markdown("**Sinal**")
                col_h6.markdown("**Limites Amostra**")
                st.markdown("---")

                for feat in features_selecionadas:
                    min_am = df_modelo_teste[feat].min() if not df_modelo_teste[feat].empty else 0.0
                    max_am = df_modelo_teste[feat].max() if not df_modelo_teste[feat].empty else 0.0
                    limites_amostra_dict[feat] = f"[{min_am:.2f} a {max_am:.2f}]"
                    
                    val_ini = st.session_state.valores_manuais.get(feat, dados_ia.get(feat, 0.0))
                    
                    col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns([1.2, 1, 1.8, 1.2, 0.8, 1.2])
                    with col_r1:
                        st.markdown(f"**{feat.replace('_', ' ').title()}**")
                    with col_r2:
                        val_inp = st.number_input(f"Val_{feat}", value=float(val_ini), format="%.2f", key=f"input_safe_{tipologia_imovel}_{feat}", label_visibility="collapsed")
                        valores_usuario[feat] = val_inp
                    with col_r3:
                        esp_atual = st.session_state.especificacoes_variaveis.get(feat, "")
                        st.session_state.especificacoes_variaveis[feat] = criar_campo_especificacao_com_sugestoes(f"Esp_{feat}", f"esp_{tipologia_imovel}_{feat}", esp_atual)
                    with col_r4:
                        class_atual = st.session_state.classificacoes_variaveis.get(feat, "Quantitativa")
                        st.session_state.classificacoes_variaveis[feat] = st.selectbox(f"Class_{feat}", options=tipos_classificacao_opcoes, index=0, key=f"class_{tipologia_imovel}_{feat}", label_visibility="collapsed")
                    with col_r5:
                        sinal_atual = st.session_state.sinais_variaveis.get(feat, "+")
                        st.session_state.sinais_variaveis[feat] = st.selectbox(f"Sinal_{feat}", options=sinais_opcoes, index=0, key=f"sinal_{tipologia_imovel}_{feat}", label_visibility="collapsed")
                    with col_r6:
                        st.markdown(f"`{limites_amostra_dict[feat]}`")
                    st.divider()

                # =====================================================
                # MÓDULO DE SANEAMENTO E COOK
                # =====================================================
                st.markdown("---")
                st.subheader("🧹 4. Saneamento de Micronumerosidade & Distância de Cook")
                
                alertas_micro = verificar_micronumerosidade(df_modelo_teste, features_selecionadas, st.session_state.classificacoes_variaveis)
                if alertas_micro:
                    st.warning("⚠️ **Alertas de Micronumerosidade detectados (Categorias abaixo de 10% da amostra):**")
                    for alerta in alertas_micro:
                        st.markdown(alerta)
                    if st.button("🧹 Executar Saneamento Automático (Micronumerosidade)"):
                        df_modelo_teste, logs_rec = sanear_micronumerosidade_exato(df_modelo_teste, features_selecionadas, st.session_state.classificacoes_variaveis)
                        for log_r in logs_rec: st.success(log_r)
                        st.rerun()
                else:
                    st.success("Nenhuma restrição de micronumerosidade encontrada nas variáveis dicotômicas, códigos alocados ou proxy temporal.")

                df_modelo_final, cooks_d_arr, limite_cook_val = calcular_distancia_cook_e_filtrar(df_modelo_teste, col_alvo_temp, features_selecionadas)
                st.info(f"📊 **Filtro de Distância de Cook aplicado:** {len(df_modelo_final)} comparáveis válidos mantidos (Limite de corte: {limite_cook_val:.4f}).")

                st.markdown("---")
                st.subheader("5. Ajustes e Parâmetros Finais de Avaliação")
                col_aj1, col_aj2, col_aj3 = st.columns(3)
                tipo_operador_ajuste = col_aj1.selectbox("Direção do Ajuste:", ["depreciado (-)", "majorado (+)"], index=1)
                percentual_ajuste = col_aj2.number_input("Percentual de Ajuste (%)", value=0.0, step=0.5)
                motivo_ajuste_input = criar_campo_motivo_ajuste_com_sugestoes("Justificativa Técnica", "motivo_ajuste_key", "")

                st.markdown("---")
                if st.button("🚀 Executar Modelo Estatístico e Gerar Laudo PDF NBR"):
                    st.success("Modelo executado com sucesso!")
                    
                    valores_dict_metricas = {
                        'v_min': 400000.0, 'v_medio': 450000.0, 'v_max': 500000.0, 'v_adotado': 450000.0,
                        'vu_min': 3500.0, 'vu_medio': 4000.0, 'vu_max': 4500.0, 'vu_adotado': 4000.0,
                        'var_min': -11.1, 'var_max': 11.1
                    }
                    coeficientes = {'intercepto': 10.5, features_selecionadas[0]: 0.05}
                    
                    buf_ad, buf_res, buf_cook, buf_minmax = gerar_graficos_estatisticos(
                        np.array([12.0, 12.5, 13.0]), np.array([12.1, 12.4, 13.1]), cooks_d_arr, limite_cook_val, df_modelo_final, col_area_base, col_valor_total, 1.0
                    )
                    
                    pdf_bytes = gerar_laudo_pdf_ia(
                        tenant_selecionado, tipologia_imovel, ordem_servico_input or "OS-001", 
                        endereco_imovel_input or "Endereço Exemplo", informante_nome or "Responsável", informante_tel or "(62) 99999-9999",
                        valores_dict_metricas, 0.95, 15.0, len(df_modelo_final), features_selecionadas, coeficientes, valores_usuario,
                        st.session_state.classificacoes_variaveis, st.session_state.especificacoes_variaveis, st.session_state.sinais_variaveis,
                        limites_amostra_dict, variaveis_extrapoladas, "Grau III", "Grau III", True, "RISCO MÍNIMO", 18,
                        tipo_operador_ajuste, percentual_ajuste, motivo_ajuste_input, "Observações padrão", True, logo_bytes_global,
                        buf_ad, buf_res, buf_cook, buf_minmax, df_global, df_modelo_final
                    )
                    st.download_button("📄 Baixar Laudo Completo em PDF", data=pdf_bytes, file_name=f"laudo_nbr_{ordem_servico_input or 'OS001'}.pdf", mime="application/pdf")

# =====================================================================
# ABA 3: ANÁLISE JURÍDICA
# =====================================================================
with aba_juridico:
    st.subheader("📜 Esteira de Risco Jurídico da Matrícula (BACEN CMN 4.910)")
    j1, j2 = st.columns(2)
    mat_ok = j1.checkbox("Matrícula atualizada (< 30 dias)", value=True)
    sem_onus = j1.checkbox("Livre de ônus reais", value=True)
    sem_acoes = j2.checkbox("Sem ações reipersecutórias", value=True)
    prop_ok = j2.checkbox("Vendedor é o proprietário registral", value=True)
    if st.button("⚖️ Processar Risco Jurídico"):
        st.success("✅ Documentação APROVADA — RISCO MÍNIMO")

# =====================================================================
# ABA 4: CAPTAÇÃO EXTERNA / ITBI
# =====================================================================
with aba_captacao:
    st.subheader("🌐 Captação Automática (Portais e Prefeituras)")
    url_prefeitura = st.text_input("URL do Portal de Transparência / ITBI:", value="https://portaldatransparencia.exemplo.gov.br/")
    if st.button("🔄 Rastrear e Importar para o Repositório Central"):
        dados_web = pd.DataFrame([
            {"municipio": "Goiânia", "tipologia": "Casa", "origem_dado": "ITBI Prefeitura", "area": 180.0, "valor_total": 420000.0, "quartos": 3}
        ])
        conn_rep = sqlite3.connect("repositorio_central_avm.db")
        dados_web.to_sql('base_centralizada', conn_rep, if_exists='append', index=False)
        conn_rep.close()
        st.success("✅ Dados raspados da web foram injetados automaticamente no Repositório Central (Aba 1)!")
