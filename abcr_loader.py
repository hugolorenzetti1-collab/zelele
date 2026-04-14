"""
Loader do Índice ABCR (Fluxo de Veículos em Rodovias) — ABCR / melhoresrodovias.org.br.
Baixa o XLSX oficial mais recente e extrai a série mensal.
Série desde jan/1999 (1999=100).
"""
import requests
import pandas as pd
import os, tempfile, re

PAGE_URL = "https://melhoresrodovias.org.br/indice-abcr_2/"
HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/120"}

# Mapa de regiões → índice da coluna LEVES na aba "(C) Original"
# Estrutura da aba (C): [Data, Brasil-L, Brasil-P, Brasil-T, _, SP-L, SP-P, SP-T, _, RJ-L, ...]
REGIOES_COLS = {
    "Brasil": 1, "São Paulo": 5, "Rio de Janeiro": 9, "Minas Gerais": 13,
    "Paraná": 17, "Rio Grande do Sul": 21, "Santa Catarina": 25,
}
TIPOS_OFFSET = {"LEVES": 0, "PESADOS": 1, "TOTAL": 2}


def achar_url_xlsx():
    """Varre o HTML da página da ABCR e devolve a URL do XLSX mais recente."""
    r = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
    links = re.findall(r'href=["\']([^"\']+abcr_\d{4}\.xlsx)["\']', r.text)
    if not links:
        raise RuntimeError("Nenhum XLSX ABCR encontrado na página.")
    # Pegar o mais recente pela data no nome (abcr_MMAA.xlsx)
    def data_arquivo(url):
        m = re.search(r"abcr_(\d{2})(\d{2})\.xlsx", url)
        if m:
            mes, ano = int(m.group(1)), int(m.group(2))
            # Assume ano 20YY
            ano_full = 2000 + ano
            return ano_full * 100 + mes
        return 0
    return sorted(set(links), key=data_arquivo, reverse=True)[0]


def baixar_abcr(regiao="Brasil", tipo="TOTAL", dessazonalizado=False):
    """Baixa série ABCR (número índice, 1999=100)."""
    url = achar_url_xlsx()
    tmp = os.path.join(tempfile.gettempdir(), os.path.basename(url))
    if not os.path.exists(tmp):
        r = requests.get(url, headers=HEADERS, timeout=60)
        with open(tmp, "wb") as f:
            f.write(r.content)

    sheet = "(D) Dessazonalizado" if dessazonalizado else "(C) Original"
    df = pd.read_excel(tmp, sheet_name=sheet, header=None)

    col_base = REGIOES_COLS[regiao]
    col = col_base + TIPOS_OFFSET[tipo]
    dados = df.iloc[3:, [0, col]].copy()
    dados.columns = ["data", "valor"]
    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    dados = dados.dropna(subset=["data"]).set_index("data").sort_index()
    dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce")
    return dados["valor"].dropna()


if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    s = baixar_abcr("Brasil", "TOTAL")
    print(f"URL usada: {achar_url_xlsx()}")
    print(f"Período: {s.index.min().strftime('%m/%Y')} a {s.index.max().strftime('%m/%Y')} ({len(s)} registros)")
    print("\nÚltimos 5:")
    print(s.tail(5))
