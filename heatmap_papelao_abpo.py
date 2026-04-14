import ipeadatapy as ipea
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import webbrowser
import os

# === BUSCAR DADOS DA ABPO ===
print("Buscando dados da ABPO (papelão ondulado)...")
df = ipea.timeseries("ABPO12_PAPEL12")
serie = df["VALUE (Tonelada)"].dropna()

# Montar DataFrame com ano e mês
tabela = pd.DataFrame({
    "Ano": serie.index.year,
    "Mês": serie.index.month,
    "Valor": serie.values
})

# Tabela pivot: linhas=ano, colunas=mês
pivot = tabela.pivot_table(index="Ano", columns="Mês", values="Valor", aggfunc="mean")

meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# === HEATMAP 1: Valores absolutos (toneladas) ===
fig_abs = go.Figure(data=go.Heatmap(
    z=pivot.values,
    x=meses_nomes,
    y=pivot.index,
    colorscale="RdYlGn",
    colorbar=dict(title="Toneladas"),
    hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Expedição: %{z:,.0f} ton<extra></extra>",
))

fig_abs.update_layout(
    title=dict(
        text="Papelão Ondulado (ABPO) — Mapa de Calor da Expedição Mensal<br>"
             f"<span style='font-size:13px; color:gray;'>Valores absolutos em toneladas | Fonte: ABPO via IPEA</span>",
        font=dict(size=18),
    ),
    xaxis_title="Mês",
    yaxis_title="Ano",
    template="plotly_white",
    height=900,
    yaxis=dict(autorange="reversed", dtick=2),
)

# === HEATMAP 2: Participação % do mês no total do ano ===
# Valores exibidos: participação do mês no total do ano
# Coloração: normalizada LINHA A LINHA (dentro de cada ano) para destacar o padrão sazonal
pivot_part = pivot.div(pivot.sum(axis=1), axis=0) * 100

# Coloração: cada linha normalizada pelo desvio em relação à média daquele ano
# Valor colorido = (participação do mês - média do ano) / desvio padrão do ano
# Assim a cor mostra se o mês foi forte/fraco DENTRO daquele ano
media_ano = pivot_part.mean(axis=1)
desv_ano = pivot_part.std(axis=1)
pivot_color = pivot_part.sub(media_ano, axis=0).div(desv_ano, axis=0)

fig_saz = go.Figure(data=go.Heatmap(
    z=pivot_color.values,
    x=meses_nomes,
    y=pivot_part.index,
    colorscale="RdBu_r",
    zmid=0,
    zmin=-2,
    zmax=2,
    colorbar=dict(title="Desvio<br>no ano (σ)"),
    customdata=pivot_part.values,
    hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Participação: %{customdata:.2f}% do ano<br>Desvio: %{z:+.2f}σ<extra></extra>",
    text=[[f"{v:.1f}" if not pd.isna(v) else "" for v in row] for row in pivot_part.values],
    texttemplate="%{text}",
    textfont=dict(size=8),
))

fig_saz.update_layout(
    title=dict(
        text="Participação do Mês no Volume Anual — Papelão Ondulado (ABPO)<br>"
             f"<span style='font-size:13px; color:gray;'>Cada célula mostra o % que o mês representou do total do ano "
             f"(referência: 8,33% = distribuição uniforme)</span>",
        font=dict(size=18),
    ),
    xaxis_title="Mês",
    yaxis_title="Ano",
    template="plotly_white",
    height=900,
    yaxis=dict(autorange="reversed", dtick=2),
)

# === GRÁFICO DE MÉDIA POR MÊS (padrão sazonal consolidado) ===
# Participação média histórica de cada mês no ano
media_por_mes = pivot_part.mean(axis=0)
uniforme = 100 / 12  # referência
cores_barras = ["#2ecc71" if v >= uniforme else "#e74c3c" for v in media_por_mes.values]

fig_medias = go.Figure(data=go.Bar(
    x=meses_nomes,
    y=media_por_mes.values,
    marker_color=cores_barras,
    text=[f"{v:.2f}%" for v in media_por_mes.values],
    textposition="outside",
    hovertemplate="Mês: %{x}<br>Participação média: %{y:.2f}%<extra></extra>",
))

fig_medias.add_hline(y=uniforme, line_dash="dash", line_color="gray", opacity=0.6,
                    annotation_text=f"Uniforme: {uniforme:.2f}%",
                    annotation_position="right")

fig_medias.update_layout(
    title=dict(
        text="Participação Média de Cada Mês no Volume Anual — Papelão Ondulado<br>"
             f"<span style='font-size:13px; color:gray;'>Média histórica (1980-{serie.index.max().year}) "
             f"da participação de cada mês no total anual</span>",
        font=dict(size=18),
    ),
    xaxis_title="Mês",
    yaxis_title="% do volume anual",
    template="plotly_white",
    height=500,
    showlegend=False,
)

# === SALVAR APENAS O HEATMAP DE PARTICIPAÇÃO ===
pasta = os.path.dirname(__file__)
caminho_html = os.path.join(pasta, "heatmap_papelao_abpo.html")
caminho_png = os.path.join(pasta, "heatmap_papelao_abpo.png")

fig_saz.write_html(caminho_html)
fig_saz.write_image(caminho_png, width=1400, height=900, scale=2)

webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print("\nMapa de calor gerado com sucesso!")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
print("\n=== PARTICIPAÇÃO MÉDIA DE CADA MÊS NO ANO ===")
print(f"Referência uniforme: {100/12:.2f}%")
print("\nMeses com MAIOR participação no ano:")
top = media_por_mes.sort_values(ascending=False)
for mes_num, val in top.head(3).items():
    print(f"  {meses_nomes[mes_num-1]}: {val:.2f}%")
print("\nMeses com MENOR participação:")
for mes_num, val in top.tail(3).items():
    print(f"  {meses_nomes[mes_num-1]}: {val:.2f}%")
