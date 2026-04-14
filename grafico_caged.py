"""
Gráfico do CAGED - Variação Anual de Empregos Formais no Brasil
Mescla duas séries do IPEA:
- CAGED12_SALDO12 (1999-2019) - CAGED antigo
- CAGED12_SALDON12 (2020-2026) - Novo CAGED
"""
import ipeadatapy as ipea
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import webbrowser
import os

# === BUSCAR E MESCLAR DADOS DO CAGED ===
print("Buscando CAGED antigo (1999-2019)...")
df_antigo = ipea.timeseries("CAGED12_SALDO12")
serie_antiga = df_antigo["VALUE (Pessoa)"].dropna()

print("Buscando Novo CAGED (2020-2026)...")
df_novo = ipea.timeseries("CAGED12_SALDON12")
serie_nova = df_novo["VALUE (Pessoa)"].dropna()

# Mesclar
serie = pd.concat([
    serie_antiga[serie_antiga.index < "2020-01-01"],
    serie_nova
]).sort_index()
serie = serie[~serie.index.duplicated(keep="last")]

print(f"Série mesclada: {len(serie)} registros, de {serie.index.min().strftime('%m/%Y')} a {serie.index.max().strftime('%m/%Y')}")

ultimo_valor = serie.iloc[-1]
ultimo_mes = serie.index[-1].strftime("%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Variação Anual: últimos 12 meses vs 12 meses anteriores (em empregos)
soma_12m = serie.rolling(window=12).sum()
variacao_12m = soma_12m - soma_12m.shift(12)
var_clean = variacao_12m.dropna()
cores_var = ["#2ecc71" if v >= 0 else "#e74c3c" for v in var_clean.values]
var_atual = var_clean.iloc[-1]

# === GRÁFICO ===
fig = go.Figure()

fig.add_trace(go.Bar(
    x=var_clean.index, y=var_clean.values,
    marker_color=cores_var,
    name="Variação Anual",
    hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:+,.0f} empregos<extra></extra>",
))

fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

# === CAIXA DESTACANDO O ÚLTIMO MÊS DA VARIAÇÃO ===
mes_var = var_clean.index[-1].strftime("%m/%Y")
cor_ultimo = "#2ecc71" if var_atual >= 0 else "#e74c3c"
sinal = "+" if var_atual >= 0 else ""
fig.add_annotation(
    x=0.99, y=0.98,
    xref="paper", yref="paper",
    text=f"<b>ÚLTIMO MÊS ({mes_var})</b><br>"
         f"<span style='font-size:22px; color:{cor_ultimo};'><b>{sinal}{var_atual:,.0f}</b></span><br>"
         f"<span style='font-size:11px; color:#555;'>variação anual (empregos)</span>",
    showarrow=False,
    align="center",
    xanchor="right", yanchor="top",
    bordercolor=cor_ultimo,
    borderwidth=2,
    borderpad=10,
    bgcolor="rgba(255, 255, 255, 0.95)",
    font=dict(size=12, color="#333"),
)

fig.update_layout(
    title=dict(
        text=f"CAGED — Variação Anual de Empregos Formais no Brasil ({serie.index.min().year} - {serie.index.max().year})<br>"
             f"<span style='font-size:13px; color:gray;'>"
             f"Diferença entre o saldo dos últimos 12 meses e o saldo dos 12 meses anteriores | "
             f"Variação atual: {var_atual:+,.0f} empregos | "
             f"Atualizado em: {data_atualizacao} | Fontes: CAGED (antigo + novo) via IPEA</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=False,
    xaxis_title="Mês/Ano",
    yaxis_title="Variação Anual (empregos)",
    yaxis=dict(tickformat=",.0f"),
    height=700,
)

# === SALVAR ===
pasta = os.path.dirname(__file__)
caminho_html = os.path.join(pasta, "grafico_caged.html")
caminho_png = os.path.join(pasta, "grafico_caged.png")

fig.write_html(caminho_html)
fig.write_image(caminho_png, width=1600, height=800, scale=2)

webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print(f"\nGráfico gerado com sucesso!")
print(f"Último saldo mensal: {ultimo_valor:+,.0f} ({ultimo_mes})")
print(f"Variação anual: {var_atual:+,.0f} empregos")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
