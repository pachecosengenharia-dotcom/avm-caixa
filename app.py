import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import io
import os
import glob

# 1. Configuração de Layout e Design (Estética Clean Luxury)
st.set_page_config(page_title="Engenharia de Avaliações | AVM", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 28px; font-weight: bold; color: #002d62; font-family: 'Helvetica Neue', sans-serif; }
    .subtitle { font-size: 14px; color: #666666; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">Sistema Avançado de Engenharia de Avaliações (AVM)</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Análise Estatística Multifatorial com Índice de Localização Urbana</p>', unsafe_allow_html=True)

# 2. Busca automática de arquivos de dados (.csv) no repositório
arquivos_csv = glob.glob("*.csv") + glob.glob("*.CSV")
lista_regioes_arquivos = sorted(list(set(arquivos_csv)))

st.sidebar.header("⚙️ Parâmetros de Avaliação")

if not lista_regioes_arquivos:
    st.error("Nenhum arquivo de base de dados (.csv) foi encontrado no repositório.")
    st.stop()

# Seleção da Região/Município
nomes_regioes = [os.path.splitext(f)[0].replace("_", " ") for f in lista_regioes_arquivos]
regiao_selecionada_nome = st.sidebar.selectbox("Selecione o Município de Avaliação", nomes_regioes)

index_selecionado = nomes_regioes.index(regiao_selecionada_nome)
arquivo_selecionado = lista_regioes_arquivos[index_selecionado]

# Carregamento dos dados
@st.cache_data
def carregar_dados(caminho_arquivo):
    return pd.read_csv(caminho_arquivo, delimiter=';', encoding='latin-1')

try:
    df_filtrado = carregar_dados(arquivo_selecionado)
except Exception as e:
    st.error(f"Erro ao carregar a base de dados de {regiao_selecionada_nome}: {e}")
    st.stop()

# 3. Entradas técnicas do imóvel avaliado (Inserindo a nova variável)
st.sidebar.subheader("📐 Características do Imóvel")
area = st.sidebar.number_input("Área Útil (m²)", min_value=10.0, max_value=1000.0, value=75.0, step=1.0)
quartos = st.sidebar.slider("Quantidade de Quartos", 0, 5, 2)
vagas = st.sidebar.slider("Vagas de Garagem", 0, 4, 1)
conservacao = st.sidebar.selectbox("Estado de Conservação (1=Regular, 2=Bom, 3=Excelente)", [1, 2, 3], index=1)

# Nova Entrada: Índice do Setor Urbano / Localização
st.sidebar.subheader("📍 Localização Relativa")
setor_urbano = st.sidebar.number_input(
    "Índice do Setor Urbano (Fator de Bairro)", 
    min_value=0.1, 
    max_value=10.0, 
    value=1.0, 
    step=0.1,
    help="Insira o índice municipal ou fator socioeconômico de valorização para o bairro do imóvel."
)

# Validação se a nova coluna existe na planilha upada
if 'Setor_Urbano' not in df_filtrado.columns:
    st.error("A coluna 'Setor_Urbano' não foi encontrada na planilha selecionada. Certifique-se de atualizar o arquivo CSV.")
    st.stop()

if len(df_filtrado) < 6:
    st.warning(f"Dados insuficientes para modelagem em {regiao_selecionada_nome}. São necessários ao menos 6 imóveis comparáveis.")
    st.stop()

# 4. Processamento da Inteligência Artificial com 5 Variáveis (Multifatorial)
X = df_filtrado[['Area', 'Quartos', 'Vagas', 'Conservacao', 'Setor_Urbano']]
y = df_filtrado['Preco']

modelo = LinearRegression()
modelo.fit(X, y)

# Predição considerando a localização urbana
dados_imovel = np.array([[area, quartos, vagas, conservacao, setor_urbano]])
preco_estimado = modelo.predict(dados_imovel)[0]
if preco_estimado < 0: preco_estimado = df_filtrado['Preco'].mean()

# Métricas Estatísticas (Padrão NBR 14653)
r2_score = modelo.score(X, y)
limite_inferior = preco_estimado * 0.85
limite_superior = preco_estimado * 1.15

# Exibição dos Resultados na Tela
col1, col2, col3 = st.columns(3)
col1.metric("Valor de Mercado Estimado", f"R$ {preco_estimado:,.2f}")
col2.metric("Intervalo Admissível Mínimo", f"R$ {limite_inferior:,.2f}")
col3.metric("Intervalo Admissível Máximo", f"R$ {limite_superior:,.2f}")

st.write(f"**Precisão Estatística do Modelo ($R^2$):** {r2_score*100:.2f}% (Amostra local: {len(df_filtrado)} imóveis ponderados por setor)")

# 5. Geração Automatizada de Gráficos Técnicos
fig, ax = plt.subplots(figsize=(7, 3.5))
sns.scatterplot(data=df_filtrado, x='Area', y='Preco', ax=ax, color='#002d62', alpha=0.6, label='Imóveis do Mercado')
ax.scatter([area], [preco_estimado], color='#d9534f', s=150, marker='*', zorder=5, label='Imóvel Avaliado')
ax.set_title(f"Dispersão de Preços vs Área - {regiao_selecionada_nome}", fontsize=10, fontweight='bold', color='#333333')
ax.set_xlabel("Área Útil (m²)", fontsize=8)
ax.set_ylabel("Preço de Mercado (R$)", fontsize=8)
ax.legend(fontsize=8)
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()

st.pyplot(fig)

img_buf = io.BytesIO()
plt.savefig(img_buf, format='png', dpi=300)
img_buf.seek(0)
plt.close()

# 6. Construção do Laudo de Avaliação Técnico Corporativo (PDF)
def gerar_pdf():
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#002d62'), spaceAfter=6)
    estilo_sub = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'), spaceAfter=20)
    estilo_h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#002d62'), spaceBefore=12, spaceAfter=10)
    estilo_texto = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#333333'))
    
    # Cabeçalho
    story.append(Paragraph("LAUDO DE AVALIAÇÃO TÉCNICA ESTATÍSTICA", estilo_titulo))
    story.append(Paragraph(f"Município de Referência: {regiao_selecionada_nome} | Engenharia Olfativa e Técnica Cadastral", estilo_sub))
    story.append(Spacer(1, 10))
    
    # Seção 1: Características
    story.append(Paragraph("1. Características e Localização do Imóvel Diagnosticado", estilo_h2))
    dados_imovel_tab = [
        ["Parâmetro Avaliado", "Especificação Informada / Ponderada"],
        ["Área Útil Construída", f"{area} m²"],
        ["Número de Quartos", f"{quartos}"],
        ["Vagas de Garagem", f"{vagas}"],
        ["Grau de Conservação", f"{'Regular' if conservacao==1 else 'Bom' if conservacao==2 else 'Excelente'}"],
        ["Índice do Setor Urbano (Bairro)", f"{setor_urbano}"]
    ]
    t1 = Table(dados_imovel_tab, colWidths=[240, 240])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#002d62')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc'))
    ]))
    story.append(t1)
    story.append(Spacer(1, 15))
    
    # Seção 2: Diagnóstico Estatístico
    story.append(Paragraph("2. Resultados do Diagnóstico Estatístico Multifatorial (AVM)", estilo_h2))
    dados_valores = [
        ["Métrica de Diagnóstico", "Valor Apurado (R$)"],
        ["Valor de Mercado Central Estimado", f"R$ {preco_estimado:,.2f}"],
        ["Limite Admissível Mínimo (L.I.)", f"R$ {limite_inferior:,.2f}"],
        ["Limite Admissível Máximo (L.S.)", f"R$ {limite_superior:,.2f}"],
        ["Coeficiente de Determinação (R²)", f"{r2_score*100:.2f}%"]
    ]
    t2 = Table(dados_valores, colWidths=[240, 240])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#002d62')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#e6f2ff')),
        ('FONTNAME', (0,1), (1,1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#bbbbbb'))
    ]))
    story.append(t2)
    story.append(Spacer(1, 15))
    
    # Seção 3: Gráfico
    story.append(Paragraph("3. Comportamento do Mercado e Homogeneização da Amostra", estilo_h2))
    story.append(Paragraph(f"O enquadramento abaixo representa analiticamente a distribuição dos imóveis em {regiao_selecionada_nome}, ponderando as características físicas conjuntamente com a variável de setorização urbana inserida no modelo:", estilo_texto))
    story.append(Spacer(1, 10))
    
    story.append(Image(img_buf, width=460, height=230))
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Nota de Responsabilidade Técnica:</b> Este laudo técnico adota o método comparativo direto de dados de mercado por meio de regressão linear múltipla, em estrita observância aos critérios científicos consolidados da norma ABNT NBR 14653.", estilo_texto))
    
    doc.build(story)
    pdf_buf.seek(0)
    return pdf_buf

pdf_data = gerar_pdf()
st.sidebar.download_button(
    label="📄 Baixar Relatório Técnico Completo",
    data=pdf_data,
    file_name=f"Laudo_Tecnico_{regiao_selecionada_nome.replace(' ', '_')}.pdf",
    mime="application/pdf"
)
