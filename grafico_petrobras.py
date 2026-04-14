import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Baixar dados da Petrobras (PETR4.SA) de 2000 até hoje
ticker = yf.Ticker("PETR4.SA")
dados = ticker.history(start="2000-01-01")

# Criar o gráfico
fig, ax = plt.subplots(figsize=(14, 7))

ax.plot(dados.index, dados["Close"], color="#006400", linewidth=1.2)
ax.fill_between(dados.index, dados["Close"], alpha=0.15, color="#006400")

ax.set_title("Petrobras (PETR4) — Preço de Fechamento (2000 - 2026)", fontsize=16, fontweight="bold")
ax.set_xlabel("Ano", fontsize=12)
ax.set_ylabel("Preço (R$)", fontsize=12)

ax.xaxis.set_major_locator(mdates.YearLocator(2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
plt.xticks(rotation=45)

ax.grid(True, linestyle="--", alpha=0.5)
fig.tight_layout()

plt.savefig("c:/pyhton/curso adv 2026/grafico_petrobras.png", dpi=150)
plt.show()
print("Gráfico salvo em: c:/pyhton/curso adv 2026/grafico_petrobras.png")
