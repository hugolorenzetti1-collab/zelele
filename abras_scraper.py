"""
Scraper dos dados históricos da ABRAS - Consumo nos Lares
Extrai todos os dados desde 2001 diretamente do site.
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

URL = "https://www.abras.com.br/economia-e-pesquisa/consumo-nos-lares/historico"
MESES = {"Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
         "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12}


def parse_pct(s):
    """Converte string tipo '14,19%' ou '-2,23%' para float."""
    if not s or s in ("", "-", "—"):
        return None
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def baixar_dados_abras():
    """Baixa e parseia todos os dados históricos da ABRAS."""
    print(f"Baixando dados do site da ABRAS: {URL}")
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")

    registros = []  # lista de dicts: {ano, mes, data, nominal_mom, nominal_yoy, nominal_ytd, real_mom, real_yoy, real_ytd}

    for tabela in tables:
        ano_atual = None
        tem_nominal = False

        for linha in tabela.find_all("tr"):
            cels = [c.get_text(strip=True) for c in linha.find_all(["th", "td"])]
            if not cels:
                continue

            # Detecta linha de ano
            texto_completo = " | ".join(cels)
            m_ano = re.search(r"(\d{4})", texto_completo)
            if "Total Brasil" in texto_completo and m_ano:
                ano_atual = int(m_ano.group(1))
                tem_nominal = "NOMINAL" in texto_completo
                continue

            # Ignora cabeçalhos de colunas
            if cels[0] in ("Mês", "Mes") or "Mês" in (cels[0] if cels else ""):
                continue

            # Detecta linha de dados (começa com abreviatura de mês)
            nome_mes = cels[0]
            if nome_mes not in MESES or ano_atual is None:
                continue

            mes_num = MESES[nome_mes]

            if tem_nominal and len(cels) >= 8:
                # formato: Mês | MoM_N | YoY_N | YTD_N | Mês | MoM_R | YoY_R | YTD_R
                registro = {
                    "ano": ano_atual,
                    "mes": mes_num,
                    "nominal_mom": parse_pct(cels[1]),
                    "nominal_yoy": parse_pct(cels[2]),
                    "nominal_ytd": parse_pct(cels[3]),
                    "real_mom": parse_pct(cels[5]),
                    "real_yoy": parse_pct(cels[6]),
                    "real_ytd": parse_pct(cels[7]),
                }
            elif len(cels) >= 4:
                # formato: Mês | MoM | YoY | YTD (só REAL)
                registro = {
                    "ano": ano_atual,
                    "mes": mes_num,
                    "nominal_mom": None,
                    "nominal_yoy": None,
                    "nominal_ytd": None,
                    "real_mom": parse_pct(cels[1]),
                    "real_yoy": parse_pct(cels[2]),
                    "real_ytd": parse_pct(cels[3]),
                }
            else:
                continue

            registro["data"] = pd.Timestamp(year=ano_atual, month=mes_num, day=1)
            registros.append(registro)

    df = pd.DataFrame(registros)
    df = df.sort_values("data").reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = baixar_dados_abras()
    print(f"\nTotal de registros: {len(df)}")
    print(f"Período: {df['data'].min().strftime('%m/%Y')} a {df['data'].max().strftime('%m/%Y')}")
    print("\nPrimeiros registros:")
    print(df.head())
    print("\nÚltimos registros:")
    print(df.tail())

    # Salvar como CSV
    import os
    caminho = os.path.join(os.path.dirname(__file__), "abras_consumo_lares_historico.csv")
    df.to_csv(caminho, index=False, encoding="utf-8-sig", decimal=",", sep=";")
    print(f"\nDados salvos em: {caminho}")
