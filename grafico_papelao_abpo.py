import ipeadatapy as ipea
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import webbrowser
import os

# === BUSCAR DADOS DA ABPO ===
print("Buscando dados da ABPO (papelão ondulado)...")
df = ipea.timeseries("ABPO12_PAPEL12")
serie = df["VALUE (Tonelada)"].dropna()

# Cortar últimos 10 anos
data_corte = serie.index.max() - pd.DateOffset(years=10)
serie = serie[serie.index >= data_corte]

ultimo_valor = serie.iloc[-1]
ultimo_mes = serie.index[-1].strftime("%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Variação acumulada: soma dos últimos 12 meses vs soma dos 12 meses anteriores
soma_12m = serie.rolling(window=12).sum()
variacao_12m = (soma_12m / soma_12m.shift(12) - 1) * 100
variacao_12m = variacao_12m.dropna()
datas_var = variacao_12m.index
valores_var = variacao_12m.values
cores_var = ["#2ecc71" if v >= 0 else "#e74c3c" for v in valores_var]

# Médias móveis (em meses)
mm12 = serie.rolling(window=12).mean()
mm24 = serie.rolling(window=24).mean()

# === GRÁFICO ===
fig = make_subplots(
    rows=2, cols=1,
    row_heights=[0.6, 0.4],
    vertical_spacing=0.1,
    subplot_titles=("Expedição Mensal de Papelão Ondulado (toneladas)",
                    "Variação Acumulada 12 meses vs 12 meses anteriores (%)")
)

# Série mensal
fig.add_trace(go.Scatter(
    x=serie.index, y=serie.values, mode="lines", name="Expedição mensal",
    line=dict(color="#8B4513", width=1.2),
    fill="tozeroy", fillcolor="rgba(139, 69, 19, 0.1)",
    hovertemplate="Mês: %{x|%m/%Y}<br>Expedição: %{y:,.0f} ton<extra></extra>"
), row=1, col=1)

# MM 12 meses
fig.add_trace(go.Scatter(
    x=mm12.index, y=mm12.values, mode="lines", name="Média 12 meses",
    line=dict(color="#e67e22", width=2, dash="dash"),
    hovertemplate="MM12: %{y:,.0f} ton<extra></extra>"
), row=1, col=1)

# MM 24 meses
fig.add_trace(go.Scatter(
    x=mm24.index, y=mm24.values, mode="lines", name="Média 24 meses",
    line=dict(color="#3498db", width=2),
    hovertemplate="MM24: %{y:,.0f} ton<extra></extra>"
), row=1, col=1)

# Variação mensal (12m vs 12m anteriores) - colunas verticais
fig.add_trace(go.Bar(
    x=datas_var, y=valores_var,
    marker_color=cores_var,
    name="Variação 12m (%)",
    hovertemplate="Mês: %{x|%m/%Y}<br>Variação 12m: %{y:.1f}%<extra></extra>",
    text=[f"{v:+.1f}%" for v in valores_var],
    textposition="outside",
    textfont=dict(size=9),
    showlegend=False,
), row=2, col=1)

ano_ini = serie.index.min().year
ano_fim = serie.index.max().year

fig.update_layout(
    title=dict(
        text=f"Papelão Ondulado — ABPO ({ano_ini} - {ano_fim})<br>"
             f"<span style='font-size:13px; color:gray;'>"
             f"Última expedição: {ultimo_valor:,.0f} ton ({ultimo_mes}) | "
             f"Atualizado em: {data_atualizacao} | Fonte: ABPO via IPEA</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=True,
    legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.7)"),
    height=850,
)

fig.update_yaxes(title_text="Toneladas", row=1, col=1, tickformat=",.0f")
fig.update_yaxes(title_text="Variação (%)", row=2, col=1)
fig.update_xaxes(title_text="Mês/Ano", row=2, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

# Salvar HTML (interativo) e PNG (imagem)
pasta = os.path.dirname(__file__)
caminho_html = os.path.join(pasta, "grafico_papelao_abpo.html")
caminho_png = os.path.join(pasta, "grafico_papelao_abpo.png")

fig.write_html(caminho_html)
fig.write_image(caminho_png, width=1600, height=900, scale=2)

webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print(f"\nGráfico gerado com sucesso!")
print(f"Última expedição: {ultimo_valor:,.0f} toneladas ({ultimo_mes})")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
