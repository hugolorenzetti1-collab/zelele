"""
Gráfico de Consumo de Energia Elétrica no Brasil
Série ELETRO12_CEET12 (IPEA) - Consumo total em GWh (mensal, desde 1976)
"""
import ipeadatapy as ipea
import plotly.graph_objects as go
from datetime import datetime
import webbrowser
import os

# === BUSCAR DADOS ===
print("Buscando dados de consumo de energia elétrica (IPEA)...")
df = ipea.timeseries("ELETRO12_CEET12")
serie = df["VALUE (GWh)"].dropna()

print(f"Série: {len(serie)} registros, de {serie.index.min().strftime('%m/%Y')} a {serie.index.max().strftime('%m/%Y')}")

ultimo_valor = serie.iloc[-1]
ultimo_mes = serie.index[-1].strftime("%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Variação Anual ABSOLUTA: soma 12m vs soma 12m anteriores (em GWh)
soma_12m = serie.rolling(window=12).sum()
variacao_12m = soma_12m - soma_12m.shift(12)
var_clean = variacao_12m.dropna()
cores_var = ["#2ecc71" if v >= 0 else "#e74c3c" for v in var_clean.values]
var_atual = var_clean.iloc[-1]
mes_var = var_clean.index[-1].strftime("%m/%Y")

# Variação Anual PERCENTUAL: média 12m / média 12m anteriores (= soma_12m/soma_anterior)
media_12m = serie.rolling(window=12).mean()
variacao_pct = (media_12m / media_12m.shift(12) - 1) * 100
var_pct_clean = variacao_pct.dropna()
var_pct_atual = var_pct_clean.iloc[-1]

# === GRÁFICO ===
fig = go.Figure()

fig.add_trace(go.Bar(
    x=var_clean.index, y=var_clean.values,
    marker_color=cores_var,
    name="Variação Anual",
    hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:+,.0f} GWh<extra></extra>",
))

fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

# Caixa do último mês
cor_ultimo = "#2ecc71" if var_atual >= 0 else "#e74c3c"
sinal = "+" if var_atual >= 0 else ""
fig.add_annotation(
    x=0.99, y=0.98, xref="paper", yref="paper",
    text=f"<b>ÚLTIMO MÊS ({mes_var})</b><br>"
         f"<span style='font-size:22px; color:{cor_ultimo};'><b>{sinal}{var_atual:,.0f}</b></span><br>"
         f"<span style='font-size:11px; color:#555;'>variação anual (GWh)</span>",
    showarrow=False, align="center",
    xanchor="right", yanchor="top",
    bordercolor=cor_ultimo, borderwidth=2, borderpad=10,
    bgcolor="rgba(255, 255, 255, 0.95)",
    font=dict(size=12, color="#333"),
)

fig.update_layout(
    title=dict(
        text=f"Consumo de Energia Elétrica no Brasil — Variação Anual ({serie.index.min().year} - {serie.index.max().year})<br>"
             f"<span style='font-size:13px; color:gray;'>"
             f"Diferença entre o consumo dos últimos 12 meses e dos 12 meses anteriores | "
             f"Variação atual: {var_atual:+,.0f} GWh | "
             f"Atualizado em: {data_atualizacao} | Fonte: IPEA (ELETRO12_CEET12)</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=False,
    xaxis_title="Mês/Ano",
    yaxis_title="Variação Anual (GWh)",
    yaxis=dict(tickformat=",.0f"),
    height=700,
)

# === SALVAR ===
pasta = os.path.dirname(__file__)
caminho_html = os.path.join(pasta, "grafico_energia.html")
caminho_png = os.path.join(pasta, "grafico_energia.png")
fig.write_html(caminho_html)
fig.write_image(caminho_png, width=1600, height=800, scale=2)
webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print(f"\nGráfico gerado!")
print(f"Último consumo mensal: {ultimo_valor:,.0f} GWh ({ultimo_mes})")
print(f"Variação anual: {var_atual:+,.0f} GWh")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
