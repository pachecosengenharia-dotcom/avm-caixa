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

# 1. Configuração de Layout e Design
st.set_page_config(page_title="Engenharia de Avaliações | AVM", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 28px; font-weight: bold; color: #002d62; font-family: 'Helvetica Neue', sans-serif; }
    .subtitle { font-size: 14px; color: #666666; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">Sistema Avançado de Engenharia de Avaliações (AVM)</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Análise Estatística Multifatorial com Índice de Localização Urbana</p>', unsafe_allow_html=True)

# 2. Busca automática de arquivos de dados (.csv)
arquivos_csv = glob.glob("*.csv") + glob.glob("*.CSV")
lista_regioes_arquivos = sorted(list(set(arquivos_csv)))

st.sidebar.header("⚙️ Parâmetros de Avaliação")

if not lista_regioes_arquivos:
    st.error("Nenhum arquivo de base de dados (.csv) foi encontrado no repositório.")
    st.stop()

nomes_regioes = [os.path.splitext(f)[0].replace("_", " ") for f in lista_regioes_arquivos]
regiao_selecionada_nome = st.sidebar.selectbox("Selecione o Município de Avaliação", nomes_regioes)

index_selecionado = nomes_regioes.index(regiao_selecionada_nome)
arquivo_selecionado = lista_regioes_arquivos[index_selecionado]

@st.cache_data
def carregar_dados(caminho_arquivo):
    return pd.read_csv(caminho_arquivo, delimiter=',', encoding='latin-1')

try:
    df_filtrado = carregar_dados(arquivo_selecionado)
except Exception as e:
    st.error(f"Erro ao carregar a base de dados de {regiao_selecionada_nome}: {e}")
    st.stop()

# 3. Entradas técnicas do imóvel
st.sidebar.subheader("📐 Características do Imóvel")
area = st.sidebar.number_input("Área Útil (m²)", min_value=10.0, max_value=1000.0, value=75.0, step=1.0)
quartos = st.sidebar.slider("Quantidade de Quartos", 0, 5, 2)
vagas = st.sidebar.slider("Vagas de Garagem", 0, 4, 1)
conservacao = st.sidebar.selectbox("Estado de Conservação (1=Regular, 2=Bom, 3=Excelente)", [1, 2, 3], index=1)

st.sidebar.subheader("📍 Localização Relativa")
setor_urbano = st.sidebar.number_input(
    "Índice do Setor Urbano (Fator de Bairro)", 
    min_value=0.1, 
    max_value=10.0, 
    value=1.0, 
    step=0.1
)

if 'Setor_Urbano' not in df_filtrado.columns:
    st.error("A coluna 'Setor_Urbano' não foi encontrada na planilha selecionada.")
    st.stop()

if len(df_filtrado) < 6:
    st.warning(f"Dados insuficientes para modelagem em {regiao_selecionada_nome}.")
    st.stop()

# 4. Inteligência Artificial
X = df_filtrado[['Area', 'Quartos', 'Vagas', 'Conservacao', 'Setor_Urbano']]
y = df_filtrado['Preco']

modelo = LinearRegression()
modelo.fit(X, y)

dados_imovel = np.array([[area, quartos, vagas, conservacao, setor_urbano]])
preco_estimado = modelo.predict(dados_imovel)[0]
if preco_estimado < 0: preco_estimado = df_filtrado['Preco'].mean()

r2_score = modelo.score(X, y)
limite_inferior = preco_estimado * 0.85
limite_superior = preco_estimado * 1.15

# Exibição dos resultados na tela
col1, col2, col3 = st.columns(3)
col1.metric("Valor de Mercado Estimado", f"R$ {preco_estimado:,.2f}")
col2.metric("Intervalo Admissível Mínimo", f"R$ {limite_inferior:,.2f}")
col3.metric("Intervalo Admissível Máximo", f"R$ {limite_superior:,.2f}")

st.write(f"**Precisão Estatística do Modelo ($R^2$):** {r2_score*100:.2f}%")

# 5. Gráficos Técnicos
fig, ax = plt.subplots(figsize=(7, 3.5))
sns.scatterplot(data=df_filtrado, x='Area', y='Preco', ax=ax, color='#002d62', alpha=0.6)
ax.scatter([area], [preco_estimado], color='#d9534f', s=150, marker='*')
plt.tight_layout()
st.pyplot(fig)

img_buf = io.BytesIO()
plt.savefig(img_buf, format='png', dpi=300)
img_buf.seek(0)
plt.close()

# 6. Geração do PDF
def gerar_pdf():
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#002d62'))
    estilo_texto = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=10)
    
    story.append(Paragraph("LAUDO DE AVALIAÇÃO TÉCNICA", estilo_titulo))
    story.append(Spacer(1, 15))
    story.append(Image(img_buf, width=460, height=230))
    
    doc.build(story)
    pdf_buf.seek(0)
    return pdf_buf

pdf_data = gerar_pdf()
st.sidebar.download_button(label="📄 Baixar Relatório", data=pdf_data, file_name="Laudo.pdf", mime="application/pdf")
