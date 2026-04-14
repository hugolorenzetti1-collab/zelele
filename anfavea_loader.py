"""
Loader das séries históricas da ANFAVEA (autoveículos Brasil).
Baixa o XLSM oficial e organiza em DataFrame com MultiIndex de colunas.
"""
import requests
import pandas as pd
import os, tempfile

URL = "https://anfavea.com.br/docs/SeriesTemporais_Autoveiculos.xlsm"

CATEGORIAS = ["AUTOVEÍCULOS TOTAL", "AUTOMÓVEIS", "COMERCIAIS LEVES", "CAMINHÕES", "ÔNIBUS"]
METRICAS = ["Emplacamento Total", "Emplacamento Nacionais", "Emplacamento Importados", "Produção", "Exportação"]


def baixar_anfavea():
    """Baixa XLSM e devolve DataFrame com colunas tipo (categoria, métrica)."""
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120"}
    r = requests.get(URL, headers=headers, timeout=60)
    tmp = os.path.join(tempfile.gettempdir(), "anfavea.xlsm")
    with open(tmp, "wb") as f:
        f.write(r.content)

    df = pd.read_excel(tmp, engine="openpyxl", header=None)

    # Linha 5 em diante = dados; coluna 0 = data
    dados = df.iloc[5:, :].copy()
    dados.columns = ["Data"] + [(cat, met) for cat in CATEGORIAS for met in METRICAS]
    dados["Data"] = pd.to_datetime(dados["Data"], errors="coerce")
    dados = dados.dropna(subset=["Data"]).set_index("Data").sort_index()

    # Converter para numérico
    for col in dados.columns:
        dados[col] = pd.to_numeric(dados[col], errors="coerce")

    dados.columns = pd.MultiIndex.from_tuples(dados.columns, names=["Categoria", "Métrica"])
    return dados


def get_serie(categoria, metrica):
    df = baixar_anfavea()
    return df[(categoria, metrica)].dropna()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    df = baixar_anfavea()
    print(f"Período: {df.index.min().strftime('%m/%Y')} a {df.index.max().strftime('%m/%Y')}")
    print(f"Total registros: {len(df)}")
    print(f"Colunas: {len(df.columns)}")
    print("\nÚltimas 3 linhas (Autoveículos Total / Produção):")
    print(df[("AUTOVEÍCULOS TOTAL", "Produção")].tail(3))
