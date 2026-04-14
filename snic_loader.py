"""
Loader dos dados de produção/despacho/consumo de cimento (SNIC).
Mescla os PDFs 2017-2024 + 2018-2025 para ter série completa.
"""
import requests
import pandas as pd
import pdfplumber
import os, tempfile, re

URLS = {
    "producao": {
        "2018-2025": "https://www.snic.org.br/assets/pdf/numeros/1772458939.pdf",
        "2017-2024": "https://www.snic.org.br/assets/pdf/numeros/1752521100.pdf",
    },
    "despacho": {
        "2018-2025": "https://www.snic.org.br/assets/pdf/numeros/1772458920.pdf",
        "2017-2024": "https://www.snic.org.br/assets/pdf/numeros/1752521111.pdf",
    },
    "consumo": {
        "2018-2025": "https://www.snic.org.br/assets/pdf/numeros/1772458909.pdf",
        "2017-2024": "https://www.snic.org.br/assets/pdf/numeros/1752521122.pdf",
    },
}

MESES_NUM = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
             "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def parse_pdf_snic(caminho_pdf):
    """Extrai série mensal do PDF SNIC. Retorna DataFrame: linhas=mês, colunas=anos."""
    with pdfplumber.open(caminho_pdf) as pdf:
        texto = pdf.pages[0].extract_text()

    linhas = texto.split("\n")
    # Encontrar linha com anos
    anos = []
    for l in linhas:
        # linha tipo: "2018 2019 2020 2021* 2022* 2023 2024* 2025**"
        if re.match(r"^\s*(\d{4}\*?\*?\s*)+\s*$", l):
            tokens = l.split()
            anos = [int(re.match(r"(\d{4})", t).group(1)) for t in tokens]
            # Detectar erro de digitação no PDF: anos duplicados (ex.: 2024* 2024**)
            # → quando o segundo é "**" (preliminar) e o primeiro "*", incrementar o segundo
            for i in range(1, len(anos)):
                if anos[i] == anos[i-1] and tokens[i].endswith("**"):
                    anos[i] = anos[i] + 1
            break

    if not anos:
        return None

    registros = []
    for l in linhas:
        m = re.match(r"^(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(.+)$", l.strip(), re.IGNORECASE)
        if m:
            mes_nome = m.group(1).lower()
            mes = MESES_NUM[mes_nome]
            valores_raw = m.group(2).split()
            # Juntar valores quebrados (ex: "5 .371.895" → "5.371.895")
            valores = []
            i = 0
            while i < len(valores_raw):
                v = valores_raw[i]
                if i + 1 < len(valores_raw) and valores_raw[i+1].startswith("."):
                    v = v + valores_raw[i+1]
                    i += 2
                else:
                    i += 1
                valores.append(v)

            # Converter para float
            for j, val in enumerate(valores):
                if j >= len(anos):
                    break
                val_clean = val.replace(".", "").replace(",", ".")
                if val_clean in ("-", "—", ""):
                    continue
                try:
                    registros.append({
                        "data": pd.Timestamp(year=anos[j], month=mes, day=1),
                        "valor": float(val_clean),
                    })
                except ValueError:
                    pass

    df = pd.DataFrame(registros)
    df = df.sort_values("data").drop_duplicates("data", keep="last").set_index("data")
    return df["valor"]


MESES_PT = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def baixar_preliminares():
    """Extrai vendas mensais dos boletins preliminares SNIC.
    Para cada ID, busca o boletim e extrai mês/ano DO PRÓPRIO TÍTULO INTERNO (mais confiável)."""
    import html as html_lib
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120"}
    r = requests.get("https://www.snic.org.br/numeros-resultados-preliminares.php",
                     headers=headers, timeout=30)
    # Pegar todos IDs únicos da listagem
    ids = sorted(set(re.findall(r"id=(\d+)", r.text)), key=int, reverse=True)
    ids = [i for i in ids if int(i) > 100]  # filtrar IDs absurdos

    boletins = []
    for id_bol in ids:
        url_bol = f"https://www.snic.org.br/numeros-resultados-preliminares-ver.php?id={id_bol}"
        rb = requests.get(url_bol, headers=headers, timeout=30)
        txt = re.sub(r"<[^>]+>", " ", rb.text)
        txt = html_lib.unescape(txt)
        txt = re.sub(r"\s+", " ", txt)
        # Pegar APENAS o título do boletim (depois do menu)
        # O padrão é "Resultados Preliminares Resultados Preliminares de <mês> <ano>"
        # ou seja, o segundo "Resultados Preliminares" indica o título real
        matches = list(re.finditer(r"Resultados Preliminares de (\w+) (\d{4})", txt))
        if not matches:
            continue
        # O título do boletim é o PRIMEIRO match após "Resultados Preliminares" (singleton no menu)
        m = matches[0]
        mes_nome = m.group(1).lower().replace("ç", "c")
        if mes_nome not in MESES_PT:
            continue
        boletins.append((id_bol, MESES_PT[mes_nome], int(m.group(2)), txt))

    PADROES_VALOR = [
        # "vendas de cimento em <mes> totalizaram X,Y milhões"
        r"vendas?\s+(?:de\s+cimento\s+)?em\s+\w+\s+(?:de\s+\d{4}\s+)?totaliz\w+\s+(\d+(?:,\d+)?)\s+milh",
        # "em <mes> totalizando X,Y milhões"
        r"em\s+\w+\s+totaliz\w+\s+(\d+(?:,\d+)?)\s+milh",
        # "comercialização ... <mes> ... X,Y milhões"
        r"comercializa\w+[^.]{0,150}?em\s+\w+[^.]{0,80}?(\d+(?:,\d+)?)\s+milh",
        r"em\s+\w+[^.]{0,150}?comercializa\w+[^.]{0,80}?(\d+(?:,\d+)?)\s+milh",
        # "vendas ... <mes> ... X,Y milhões"
        r"vendas?\s+(?:de\s+cimento\s+)?[^.]{0,150}?em\s+\w+[^.]{0,80}?(\d+(?:,\d+)?)\s+milh",
        # último recurso: primeiro "X,Y milhões de toneladas" do texto
        r"(\d+(?:,\d+)?)\s+milh[\w\s]+toneladas?",
    ]

    registros = {}
    for id_bol, mes, ano, txt_completo in boletins:
        # Cortar para começar logo após "Download do arquivo" (início do conteúdo)
        idx = txt_completo.find("Download do arquivo")
        txt = txt_completo[idx:] if idx > 0 else txt_completo

        for padrao in PADROES_VALOR:
            m = re.search(padrao, txt, re.IGNORECASE)
            if m:
                val = float(m.group(1).replace(",", "."))
                if 3.0 <= val <= 8.0:  # filtro: vendas mensais 3-8M ton
                    data = pd.Timestamp(year=ano, month=mes, day=1)
                    registros[data] = val * 1_000_000
                    break

    if not registros:
        return pd.Series(dtype=float)
    s = pd.Series(registros).sort_index()
    s.index.name = "data"
    return s


def baixar_snic(tipo="producao", incluir_preliminar=True):
    """Baixa e mescla os PDFs (2017-2024 + 2018-2025) + boletins preliminares."""
    if tipo not in URLS:
        raise ValueError(f"Tipo deve ser: {list(URLS.keys())}")
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120"}
    series = []
    for periodo, url in URLS[tipo].items():
        tmp = os.path.join(tempfile.gettempdir(), f"snic_{tipo}_{periodo}.pdf")
        if not os.path.exists(tmp):
            r = requests.get(url, headers=headers, timeout=60)
            with open(tmp, "wb") as f:
                f.write(r.content)
        s = parse_pdf_snic(tmp)
        if s is not None:
            series.append(s)

    # Mesclar — duplicatas usam a versão mais recente (2018-2025)
    serie_mesclada = pd.concat(series).sort_index()
    serie_mesclada = serie_mesclada[~serie_mesclada.index.duplicated(keep="last")]

    # Adicionar preliminares (somente para vendas/consumo, e só meses depois do último PDF)
    if incluir_preliminar and tipo in ("consumo",):
        try:
            prelim = baixar_preliminares()
            ultimo_pdf = serie_mesclada.index.max()
            novos = prelim[prelim.index > ultimo_pdf]
            if not novos.empty:
                serie_mesclada = pd.concat([serie_mesclada, novos]).sort_index()
        except Exception as e:
            print(f"Aviso: falha ao buscar preliminares: {e}")

    return serie_mesclada


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    s = baixar_snic("producao")
    print(f"Período: {s.index.min().strftime('%m/%Y')} a {s.index.max().strftime('%m/%Y')}")
    print(f"Registros: {len(s)}")
    print("\nÚltimos 5:")
    print(s.tail(5))
