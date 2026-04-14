"""
Gráfico do Boi Gordo CEPEA/ESALQ
Dados diários direto do site CEPEA (desde 1997).
URL retorna arquivo XLS direto.
"""
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import webbrowser
import os

URL_CEPEA = "https://cepea.org.br/br/indicador/series/boi-gordo.aspx?id=2"

# === BAIXAR XLS DIRETO DO CEPEA ===
print("Baixando série histórica do Boi Gordo CEPEA/ESALQ...")
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
r = requests.get(URL_CEPEA, headers=headers, timeout=60)

pasta = os.path.dirname(__file__)
caminho_xls = os.path.join(pasta, "boi_gordo_cepea.xls")
with open(caminho_xls, "wb") as f:
    f.write(r.content)

# === LER XLS (precisa ignorar erros de corrupção do formato CEPEA) ===
df_raw = pd.read_excel(
    caminho_xls,
    engine="xlrd",
    engine_kwargs={"ignore_workbook_corruption": True},
    skiprows=3, header=None,
    names=["Data", "Valor_BRL", "Valor_USD"],
)

# Limpar
df_raw = df_raw.dropna(subset=["Data", "Valor_BRL"])
df_raw["Data"] = pd.to_datetime(df_raw["Data"], format="%d/%m/%Y", errors="coerce")
df_raw = df_raw.dropna(subset=["Data"]).set_index("Data").sort_index()
df_raw["Valor_BRL"] = pd.to_numeric(df_raw["Valor_BRL"], errors="coerce")
serie = df_raw["Valor_BRL"].dropna()

print(f"Série: {len(serie)} registros, de {serie.index.min().strftime('%d/%m/%Y')} a {serie.index.max().strftime('%d/%m/%Y')}")

ultimo_valor = serie.iloc[-1]
ultima_data = serie.index[-1].strftime("%d/%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Médias móveis
mm21 = serie.rolling(window=21).mean()
mm50 = serie.rolling(window=50).mean()
mm200 = serie.rolling(window=200).mean()

# === GRÁFICO ===
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=serie.index, y=serie.values,
    mode="lines", name="Boi Gordo (R$/@)",
    line=dict(color="#8B4513", width=1.5),
    fill="tozeroy", fillcolor="rgba(139, 69, 19, 0.1)",
    hovertemplate="Data: %{x|%d/%m/%Y}<br>R$ %{y:.2f}/arroba<extra></extra>",
))

fig.add_trace(go.Scatter(
    x=mm21.index, y=mm21.values, mode="lines", name="MM 21",
    line=dict(color="#e67e22", width=1.2, dash="dot"),
    hovertemplate="MM21: R$ %{y:.2f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=mm50.index, y=mm50.values, mode="lines", name="MM 50",
    line=dict(color="#3498db", width=1.2, dash="dash"),
    hovertemplate="MM50: R$ %{y:.2f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=mm200.index, y=mm200.values, mode="lines", name="MM 200",
    line=dict(color="#e74c3c", width=1.5),
    hovertemplate="MM200: R$ %{y:.2f}<extra></extra>",
))

# Caixa do último valor
fig.add_annotation(
    x=0.99, y=0.98, xref="paper", yref="paper",
    text=f"<b>ÚLTIMO PREGÃO ({ultima_data})</b><br>"
         f"<span style='font-size:22px; color:#8B4513;'><b>R$ {ultimo_valor:.2f}</b></span><br>"
         f"<span style='font-size:11px; color:#555;'>R$ por arroba</span>",
    showarrow=False, align="center",
    xanchor="right", yanchor="top",
    bordercolor="#8B4513", borderwidth=2, borderpad=10,
    bgcolor="rgba(255, 255, 255, 0.95)",
    font=dict(size=12, color="#333"),
)

fig.update_layout(
    title=dict(
        text=f"Boi Gordo CEPEA/B3 — Cotação Diária ({serie.index.min().year} - {serie.index.max().year})<br>"
             f"<span style='font-size:13px; color:gray;'>"
             f"Última cotação: R$ {ultimo_valor:.2f}/arroba ({ultima_data}) | "
             f"Total de pregões: {len(serie):,} | "
             f"Atualizado em: {data_atualizacao} | Fonte: CEPEA/ESALQ (site oficial)</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=True,
    legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.7)"),
    xaxis_title="Data",
    yaxis_title="R$ / arroba",
    height=750,
)

# === SALVAR ===
caminho_html = os.path.join(pasta, "grafico_boi_cepea.html")
caminho_png = os.path.join(pasta, "grafico_boi_cepea.png")
fig.write_html(caminho_html)
fig.write_image(caminho_png, width=1600, height=800, scale=2)
webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print(f"\nGráfico gerado!")
print(f"Última cotação: R$ {ultimo_valor:.2f}/arroba ({ultima_data})")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
