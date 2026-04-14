import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import webbrowser
import os

# Baixar dados atualizados da Petrobras
print("Buscando dados atualizados da Petrobras...")
ticker = yf.Ticker("PETR4.SA")
dados = ticker.history(start="2000-01-01")

ultima_cotacao = dados["Close"].iloc[-1]
data_atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

# Calcular variação anual
preco_anual = dados["Close"].resample("YE").last()
variacao_anual = preco_anual.pct_change() * 100
variacao_anual = variacao_anual.dropna()

anos = [d.year for d in variacao_anual.index]
valores = variacao_anual.values
cores = ["#2ecc71" if v >= 0 else "#e74c3c" for v in valores]

# Criar gráfico com 2 painéis (preço + variação anual)
fig = make_subplots(
    rows=2, cols=1,
    row_heights=[0.6, 0.4],
    vertical_spacing=0.08,
    subplot_titles=("Preço de Fechamento", "Variação Anual (%)")
)

# Calcular médias móveis
dados["MM21"] = dados["Close"].rolling(window=21).mean()
dados["MM50"] = dados["Close"].rolling(window=50).mean()
dados["MM200"] = dados["Close"].rolling(window=200).mean()

# Gráfico de preço
fig.add_trace(go.Scatter(
    x=dados.index,
    y=dados["Close"],
    mode="lines",
    name="PETR4",
    line=dict(color="#006400", width=1.5),
    fill="tozeroy",
    fillcolor="rgba(0, 100, 0, 0.1)",
    hovertemplate="Data: %{x|%d/%m/%Y}<br>Preço: R$ %{y:.2f}<extra></extra>"
), row=1, col=1)

# Médias móveis
fig.add_trace(go.Scatter(
    x=dados.index, y=dados["MM21"], mode="lines", name="MM 21",
    line=dict(color="#e67e22", width=1.2, dash="dot"),
    hovertemplate="MM21: R$ %{y:.2f}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=dados.index, y=dados["MM50"], mode="lines", name="MM 50",
    line=dict(color="#3498db", width=1.2, dash="dash"),
    hovertemplate="MM50: R$ %{y:.2f}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=dados.index, y=dados["MM200"], mode="lines", name="MM 200",
    line=dict(color="#e74c3c", width=1.5),
    hovertemplate="MM200: R$ %{y:.2f}<extra></extra>"
), row=1, col=1)

# Gráfico de variação anual (linhas segmentadas verde/vermelho com sombra)
for i in range(len(anos) - 1):
    cor_segmento = "#2ecc71" if valores[i + 1] >= 0 else "#e74c3c"
    fill_cor = "rgba(46, 204, 113, 0.15)" if valores[i + 1] >= 0 else "rgba(231, 76, 60, 0.15)"
    # Sombra (fill até zero)
    fig.add_trace(go.Scatter(
        x=[anos[i], anos[i + 1], anos[i + 1], anos[i]],
        y=[valores[i], valores[i + 1], 0, 0],
        fill="toself",
        fillcolor=fill_cor,
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    ), row=2, col=1)
    # Linha
    fig.add_trace(go.Scatter(
        x=[anos[i], anos[i + 1]],
        y=[valores[i], valores[i + 1]],
        mode="lines",
        line=dict(color=cor_segmento, width=2.5),
        hoverinfo="skip",
        showlegend=False,
    ), row=2, col=1)

fig.add_trace(go.Scatter(
    x=anos,
    y=valores,
    mode="markers+text",
    name="Variação %",
    marker=dict(size=8, color=cores, line=dict(width=1, color="white")),
    hovertemplate="Ano: %{x}<br>Variação: %{y:.1f}%<extra></extra>",
    text=[f"{v:.1f}%" for v in valores],
    textposition="top center",
    textfont=dict(size=9),
), row=2, col=1)

fig.update_layout(
    title=dict(
        text=f"Petrobras (PETR4) — Análise Histórica (2000 - 2026)<br>"
             f"<span style='font-size:13px; color:gray;'>Última cotação: R$ {ultima_cotacao:.2f} | Atualizado em: {data_atualizacao}</span>",
        font=dict(size=18),
    ),
    template="plotly_white",
    hovermode="x unified",
    showlegend=True,
    legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.7)"),
    height=900,
)

fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
fig.update_yaxes(title_text="Variação (%)", row=2, col=1)
fig.update_xaxes(title_text="Ano", row=2, col=1)

# Linha de referência zero no gráfico de variação
fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)

# Salvar e abrir no navegador
caminho = os.path.join(os.path.dirname(__file__), "grafico_petrobras_interativo.html")
fig.write_html(caminho)
webbrowser.open(f"file:///{caminho.replace(os.sep, '/')}")
print(f"Gráfico atualizado e aberto no navegador!")
print(f"Última cotação: R$ {ultima_cotacao:.2f}")
