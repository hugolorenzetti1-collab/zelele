"""Gráfico ABCR — Fluxo de Veículos nas Rodovias (Brasil TOTAL) — variação anual."""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import plotly.graph_objects as go
from datetime import datetime
import webbrowser, os
from abcr_loader import baixar_abcr

print("Baixando Índice ABCR...")
serie = baixar_abcr("Brasil", "TOTAL")
print(f"Série: {len(serie)} registros, {serie.index.min().strftime('%m/%Y')} a {serie.index.max().strftime('%m/%Y')}")

ultimo_valor = serie.iloc[-1]
ultimo_mes = serie.index[-1].strftime("%m/%Y")
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Variação Anual: média últimos 12m - média 12m anteriores (em pontos de índice)
media_12m = serie.rolling(window=12).mean()
variacao_12m = media_12m - media_12m.shift(12)
var_clean = variacao_12m.dropna()
cores_var = ["#2ecc71" if v >= 0 else "#e74c3c" for v in var_clean.values]
var_atual = var_clean.iloc[-1]
mes_var = var_clean.index[-1].strftime("%m/%Y")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=var_clean.index, y=var_clean.values,
    marker_color=cores_var,
    hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:+.2f} pontos<extra></extra>",
))
fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

cor_ultimo = "#2ecc71" if var_atual >= 0 else "#e74c3c"
sinal = "+" if var_atual >= 0 else ""
fig.add_annotation(
    x=0.99, y=0.98, xref="paper", yref="paper",
    text=f"<b>ÚLTIMO MÊS ({mes_var})</b><br>"
         f"<span style='font-size:22px; color:{cor_ultimo};'><b>{sinal}{var_atual:.2f}</b></span><br>"
         f"<span style='font-size:11px; color:#555;'>variação anual (pontos)</span>",
    showarrow=False, align="center",
    xanchor="right", yanchor="top",
    bordercolor=cor_ultimo, borderwidth=2, borderpad=10,
    bgcolor="rgba(255,255,255,0.95)",
    font=dict(size=12, color="#333"),
)

fig.update_layout(
    title=dict(
        text=f"Índice ABCR — Fluxo de Veículos Total Brasil ({serie.index.min().year} - {serie.index.max().year})<br>"
             f"<span style='font-size:13px; color:gray;'>"
             f"Variação Anual (média 12m − média 12m anteriores) | Último índice: {ultimo_valor:.2f} ({ultimo_mes}) | "
             f"Variação atual: {var_atual:+.2f} pts | "
             f"Atualizado em: {data_atualizacao} | Fonte: ABCR (melhoresrodovias.org.br)</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=False,
    xaxis_title="Mês/Ano",
    yaxis_title="Variação Anual (pontos de índice)",
    height=700,
)

pasta = os.path.dirname(__file__)
fig.write_html(os.path.join(pasta, "grafico_abcr.html"))
fig.write_image(os.path.join(pasta, "grafico_abcr.png"), width=1600, height=800, scale=2)
webbrowser.open(f"file:///{os.path.join(pasta, 'grafico_abcr.html').replace(os.sep, '/')}")

print(f"\nGráfico gerado!")
print(f"Último índice: {ultimo_valor:.2f} ({ultimo_mes})")
print(f"Variação anual: {var_atual:+.2f} pontos")
