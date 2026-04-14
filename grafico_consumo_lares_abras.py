"""
Gráfico do Consumo nos Lares - ABRAS
Dados direto do site da ABRAS (histórico completo desde 2001).
"""
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import webbrowser
import os
from abras_scraper import baixar_dados_abras

# === BUSCAR DADOS DIRETAMENTE DO SITE DA ABRAS ===
print("Buscando dados da ABRAS (consumo nos lares)...")
df = baixar_dados_abras()
df = df.set_index("data")

# real_yoy = mês vs mesmo mês do ano anterior (ajustado pela inflação)
serie_yoy = df["real_yoy"].dropna()

ultimo_yoy = serie_yoy.iloc[-1]
ultimo_mes = serie_yoy.index[-1].strftime("%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Média móvel 12 meses corridos (da YoY)
mm12_yoy = serie_yoy.rolling(window=12).mean().dropna()
cores = ["#2ecc71" if v >= 0 else "#e74c3c" for v in mm12_yoy.values]

# === GRÁFICO ===
fig = go.Figure()

fig.add_trace(go.Bar(
    x=mm12_yoy.index, y=mm12_yoy.values,
    marker_color=cores,
    name="Média 12 meses corridos",
    hovertemplate="Mês: %{x|%m/%Y}<br>Média 12m YoY: %{y:+.2f}%<extra></extra>",
))

fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

# === MARCAR EVENTOS: COPAS DO MUNDO E ELEIÇÕES BRASILEIRAS ===
copas = [
    ("2002-05-31", "2002-06-30", "Copa 2002"),
    ("2006-06-09", "2006-07-09", "Copa 2006"),
    ("2010-06-11", "2010-07-11", "Copa 2010"),
    ("2014-06-12", "2014-07-13", "Copa 2014"),
    ("2018-06-14", "2018-07-15", "Copa 2018"),
    ("2022-11-20", "2022-12-18", "Copa 2022"),
    ("2026-06-11", "2026-07-19", "Copa 2026"),
]

eleicoes = [
    ("2002-10-01", "2002-10-31", "Eleição 2002"),
    ("2004-10-01", "2004-10-31", "Eleição 2004"),
    ("2006-10-01", "2006-10-31", "Eleição 2006"),
    ("2008-10-01", "2008-10-31", "Eleição 2008"),
    ("2010-10-01", "2010-10-31", "Eleição 2010"),
    ("2012-10-01", "2012-10-31", "Eleição 2012"),
    ("2014-10-01", "2014-10-31", "Eleição 2014"),
    ("2016-10-01", "2016-10-31", "Eleição 2016"),
    ("2018-10-01", "2018-10-31", "Eleição 2018"),
    ("2020-11-01", "2020-11-30", "Eleição 2020"),
    ("2022-10-01", "2022-10-31", "Eleição 2022"),
    ("2024-10-01", "2024-10-31", "Eleição 2024"),
    ("2026-10-01", "2026-10-31", "Eleição 2026"),
]

for inicio, fim, rotulo in copas:
    fig.add_vrect(
        x0=pd.Timestamp(inicio), x1=pd.Timestamp(fim),
        fillcolor="gold", opacity=0.45,
        line_width=0,
    )
    fig.add_annotation(
        x=pd.Timestamp(inicio) + (pd.Timestamp(fim) - pd.Timestamp(inicio)) / 2,
        y=1, yref="paper",
        text=rotulo, showarrow=False,
        font=dict(size=9, color="#8B4513"),
        yshift=-8,
    )

for inicio, fim, rotulo in eleicoes:
    fig.add_vrect(
        x0=pd.Timestamp(inicio), x1=pd.Timestamp(fim),
        fillcolor="#f1c40f", opacity=0.25,
        line_width=0,
    )
    fig.add_annotation(
        x=pd.Timestamp(inicio) + (pd.Timestamp(fim) - pd.Timestamp(inicio)) / 2,
        y=0, yref="paper",
        text=rotulo, showarrow=False,
        font=dict(size=7, color="#7d6608"),
        yshift=8, textangle=-90,
    )

fig.update_layout(
    title=dict(
        text=f"Consumo nos Lares — ABRAS ({df.index.min().year} - {df.index.max().year})<br>"
             f"<span style='font-size:14px; color:gray;'>"
             f"Média dos últimos 12 meses corridos — YoY Real (mês vs mesmo mês ano anterior)<br>"
             f"Última: {ultimo_yoy:+.2f}% ({ultimo_mes}) | "
             f"Atualizado em: {data_atualizacao} | Fonte: ABRAS (site oficial)</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=False,
    xaxis_title="Mês/Ano",
    yaxis_title="Média 12m YoY (%)",
    height=650,
)

# === SALVAR ===
pasta = os.path.dirname(__file__)
caminho_html = os.path.join(pasta, "grafico_consumo_lares_abras.html")
caminho_png = os.path.join(pasta, "grafico_consumo_lares_abras.png")

fig.write_html(caminho_html)
fig.write_image(caminho_png, width=1600, height=800, scale=2)

webbrowser.open(f"file:///{caminho_html.replace(os.sep, '/')}")

print(f"\nGráfico gerado com sucesso!")
print(f"Período: {df.index.min().strftime('%m/%Y')} a {df.index.max().strftime('%m/%Y')}")
print(f"Total de registros: {len(df)}")
print(f"Última YoY: {ultimo_yoy:+.2f}%")
print(f"HTML: {caminho_html}")
print(f"PNG:  {caminho_png}")
