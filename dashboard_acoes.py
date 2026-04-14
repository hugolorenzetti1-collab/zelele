import dash
from dash import dcc, html, callback, Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import ipeadatapy as ipea
import pandas as pd
import webbrowser
from threading import Timer
from datetime import datetime, timedelta
from abras_scraper import baixar_dados_abras
from anfavea_loader import baixar_anfavea
from abcr_loader import baixar_abcr

# Cache dos dados da ABRAS (evita rebaixar toda hora)
_CACHE_ABRAS = {"df": None}
_CACHE_CAGED = {"serie": None}
_CACHE_CEPEA = {}
_CACHE_ANFAVEA = {"df": None}
_CACHE_ABCR = {}

def get_abcr_serie(codigo):
    """codigo = 'Regiao|TIPO'"""
    if codigo in _CACHE_ABCR:
        return _CACHE_ABCR[codigo]
    regiao, tipo = codigo.split("|")
    s = baixar_abcr(regiao, tipo)
    _CACHE_ABCR[codigo] = s
    return s

def get_anfavea_serie(codigo):
    """codigo no formato 'CATEGORIA|METRICA'"""
    if _CACHE_ANFAVEA["df"] is None:
        _CACHE_ANFAVEA["df"] = baixar_anfavea()
    cat, met = codigo.split("|")
    s = _CACHE_ANFAVEA["df"][(cat, met)].dropna()
    ultimo_real = s[s > 0].index.max()
    return s.loc[:ultimo_real]

def get_cepea_serie(codigo):
    """codigo pode ser:
       - só um id (ex.: '2') → usa URL de boi-gordo (compat antiga)
       - 'slug|id' (ex.: 'milho|77') → usa o slug correto"""
    if codigo in _CACHE_CEPEA:
        return _CACHE_CEPEA[codigo]
    import requests, os, tempfile
    if "|" in codigo:
        slug, cepea_id = codigo.split("|", 1)
    else:
        slug, cepea_id = "boi-gordo", codigo
    url = f"https://cepea.org.br/br/indicador/series/{slug}.aspx?id={cepea_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=60)
    tmp_path = os.path.join(tempfile.gettempdir(), f"cepea_{slug}_{cepea_id}.xls")
    with open(tmp_path, "wb") as f:
        f.write(r.content)
    df_raw = pd.read_excel(
        tmp_path, engine="xlrd",
        engine_kwargs={"ignore_workbook_corruption": True},
        skiprows=3, header=None,
        names=["Data", "Valor_BRL", "Valor_USD"],
    )
    df_raw = df_raw.dropna(subset=["Data", "Valor_BRL"])
    df_raw["Data"] = pd.to_datetime(df_raw["Data"], format="%d/%m/%Y", errors="coerce")
    df_raw = df_raw.dropna(subset=["Data"]).set_index("Data").sort_index()
    serie = pd.to_numeric(df_raw["Valor_BRL"], errors="coerce").dropna()
    _CACHE_CEPEA[codigo] = serie
    return serie

def get_abras_df():
    if _CACHE_ABRAS["df"] is None:
        _CACHE_ABRAS["df"] = baixar_dados_abras().set_index("data")
    return _CACHE_ABRAS["df"]

def get_caged_serie():
    if _CACHE_CAGED["serie"] is None:
        antigo = ipea.timeseries("CAGED12_SALDO12")["VALUE (Pessoa)"].dropna()
        novo = ipea.timeseries("CAGED12_SALDON12")["VALUE (Pessoa)"].dropna()
        s = pd.concat([antigo[antigo.index < "2020-01-01"], novo]).sort_index()
        s = s[~s.index.duplicated(keep="last")]
        _CACHE_CAGED["serie"] = s.astype(float)
    return _CACHE_CAGED["serie"]

# === ATIVOS DISPONÍVEIS ===
# Formato: "Nome exibido": {"fonte": "yf" ou "ipea", "codigo": "ticker ou código IPEA", "unidade": "R$", "descricao": "..."}
ativos = {
    # --- AÇÕES B3 ---
    "Petrobras PN (PETR4)": {"fonte": "yf", "codigo": "PETR4.SA", "unidade": "R$"},
    "Petrobras ON (PETR3)": {"fonte": "yf", "codigo": "PETR3.SA", "unidade": "R$"},
    "Vale (VALE3)": {"fonte": "yf", "codigo": "VALE3.SA", "unidade": "R$"},
    "Itaú Unibanco (ITUB4)": {"fonte": "yf", "codigo": "ITUB4.SA", "unidade": "R$"},
    "Bradesco (BBDC4)": {"fonte": "yf", "codigo": "BBDC4.SA", "unidade": "R$"},
    "Banco do Brasil (BBAS3)": {"fonte": "yf", "codigo": "BBAS3.SA", "unidade": "R$"},
    "Ambev (ABEV3)": {"fonte": "yf", "codigo": "ABEV3.SA", "unidade": "R$"},
    "WEG (WEGE3)": {"fonte": "yf", "codigo": "WEGE3.SA", "unidade": "R$"},
    "Magazine Luiza (MGLU3)": {"fonte": "yf", "codigo": "MGLU3.SA", "unidade": "R$"},
    "B3 (B3SA3)": {"fonte": "yf", "codigo": "B3SA3.SA", "unidade": "R$"},
    "Suzano (SUZB3)": {"fonte": "yf", "codigo": "SUZB3.SA", "unidade": "R$"},
    "JBS (JBSS3)": {"fonte": "yf", "codigo": "JBSS3.SA", "unidade": "R$"},
    "Eletrobras (ELET3)": {"fonte": "yf", "codigo": "ELET3.SA", "unidade": "R$"},
    "Nubank (NU)": {"fonte": "yf", "codigo": "NU", "unidade": "US$"},
    "Cemig (CMIG4)": {"fonte": "yf", "codigo": "CMIG4.SA", "unidade": "R$"},
    "Localiza (RENT3)": {"fonte": "yf", "codigo": "RENT3.SA", "unidade": "R$"},
    # --- COMMODITIES BRASIL (IPEA/DERAL) ---
    "Boi Gordo - Brasil (R$/arroba)": {"fonte": "ipea", "codigo": "DERAL12_PRBGO12", "unidade": "R$/arroba"},
    "Boi Gordo - CEPEA/B3 diário (R$/arroba)": {"fonte": "cepea", "codigo": "boi-gordo|2", "unidade": "R$/arroba"},
    "Milho - CEPEA/ESALQ diário (R$/60kg)": {"fonte": "cepea", "codigo": "milho|77", "unidade": "R$/60kg"},
    "Milho - Brasil (R$/60kg)": {"fonte": "ipea", "codigo": "DERAL12_PRMI12", "unidade": "R$/60kg"},
    "Soja - Brasil (R$/60kg)": {"fonte": "ipea", "codigo": "DERAL12_PRSO12", "unidade": "R$/60kg"},
    "Milho Atacado SP (R$/60kg)": {"fonte": "ipea", "codigo": "DEPAE12_ATMI12", "unidade": "R$/60kg"},
    # --- PAPELÃO ONDULADO (ABPO) ---
    "Papelão Ondulado - ABPO (ton/mês)": {"fonte": "ipea", "codigo": "ABPO12_PAPEL12", "unidade": "ton"},
    # --- MERCADO DE TRABALHO (CAGED) ---
    "CAGED - Saldo de Empregos Formais": {"fonte": "caged", "codigo": "caged", "unidade": "empregos", "tipo": "caged"},
    # --- ENERGIA ELÉTRICA ---
    "Energia Elétrica - Consumo Total (GWh)": {"fonte": "ipea", "codigo": "ELETRO12_CEET12", "unidade": "GWh", "tipo": "var_anual"},
    # --- AUTOVEÍCULOS (ANFAVEA) ---
    "Autoveículos - Produção Total (un)": {"fonte": "anfavea", "codigo": "AUTOVEÍCULOS TOTAL|Produção", "unidade": "unidades", "tipo": "var_anual"},
    "Autoveículos - Emplacamento Total (un)": {"fonte": "anfavea", "codigo": "AUTOVEÍCULOS TOTAL|Emplacamento Total", "unidade": "unidades", "tipo": "var_anual"},
    "Autoveículos - Exportação Total (un)": {"fonte": "anfavea", "codigo": "AUTOVEÍCULOS TOTAL|Exportação", "unidade": "unidades", "tipo": "var_anual"},
    "Automóveis - Produção (un)": {"fonte": "anfavea", "codigo": "AUTOMÓVEIS|Produção", "unidade": "unidades", "tipo": "var_anual"},
    "Caminhões - Produção (un)": {"fonte": "anfavea", "codigo": "CAMINHÕES|Produção", "unidade": "unidades", "tipo": "var_anual"},
    # --- FLUXO DE VEÍCULOS (ABCR) ---
    "ABCR - Fluxo Total Brasil (índice)": {"fonte": "abcr", "codigo": "Brasil|TOTAL", "unidade": "pontos", "tipo": "var_anual"},
    "ABCR - Veículos Leves Brasil (índice)": {"fonte": "abcr", "codigo": "Brasil|LEVES", "unidade": "pontos", "tipo": "var_anual"},
    "ABCR - Veículos Pesados Brasil (índice)": {"fonte": "abcr", "codigo": "Brasil|PESADOS", "unidade": "pontos", "tipo": "var_anual"},
    # --- CONSUMO NOS LARES (ABRAS - direto do site, desde 2001) ---
    "Consumo nos Lares - ABRAS (média 12m YoY real)": {"fonte": "abras", "codigo": "real_yoy", "unidade": "%", "tipo": "abras_mm12"},
    "Vendas Supermercados - Real (índice)": {"fonte": "ipea", "codigo": "PMC12_VRSUPTN12", "unidade": "índice"},
    "Vendas Supermercados - Nominal (índice)": {"fonte": "ipea", "codigo": "PMC12_VNSUPTN12", "unidade": "índice"},
    # --- CELULOSE E PAPEL ---
    "Produção Industrial - Celulose e Papel (índice)": {"fonte": "ipea", "codigo": "PIMPFN12_QIIGNN812", "unidade": "índice"},
    "Consumo Aparente - Celulose e Papel (índice)": {"fonte": "ipea", "codigo": "GAC12_CAPAPEL12", "unidade": "índice"},
    # --- COMMODITIES INTERNACIONAIS ---
    "Milho Internacional (US$/ton)": {"fonte": "ipea", "codigo": "IFS12_MAIZE12", "unidade": "US$/ton"},
    "Soja Internacional (US$/ton)": {"fonte": "ipea", "codigo": "IFS12_SOJAGP12", "unidade": "US$/ton"},
    "Milho CME (Corn)": {"fonte": "yf", "codigo": "ZC=F", "unidade": "US¢/bushel"},
    "Boi Gordo CME (Live Cattle)": {"fonte": "yf", "codigo": "LE=F", "unidade": "US¢/lb"},
    "Soja CME (Soybean)": {"fonte": "yf", "codigo": "ZS=F", "unidade": "US¢/bushel"},
    "Café Arábica (Coffee)": {"fonte": "yf", "codigo": "KC=F", "unidade": "US¢/lb"},
    "Petróleo WTI": {"fonte": "yf", "codigo": "CL=F", "unidade": "US$/barril"},
    "Petróleo Brent": {"fonte": "yf", "codigo": "BZ=F", "unidade": "US$/barril"},
    "Ouro": {"fonte": "yf", "codigo": "GC=F", "unidade": "US$/oz"},
    "Prata": {"fonte": "yf", "codigo": "SI=F", "unidade": "US$/oz"},
    # --- ÍNDICES / CÂMBIO ---
    "Dólar/Real (USDBRL)": {"fonte": "yf", "codigo": "BRL=X", "unidade": "R$"},
    "Euro/Real (EURBRL)": {"fonte": "yf", "codigo": "EURBRL=X", "unidade": "R$"},
    "Ibovespa (^BVSP)": {"fonte": "yf", "codigo": "^BVSP", "unidade": "pts"},
    "S&P 500": {"fonte": "yf", "codigo": "^GSPC", "unidade": "pts"},
    "Bitcoin USD": {"fonte": "yf", "codigo": "BTC-USD", "unidade": "US$"},
}


def buscar_dados(ativo_info, start):
    """Busca dados de um ativo, seja via Yahoo Finance ou IPEA."""
    fonte = ativo_info["fonte"]
    codigo = ativo_info["codigo"]

    if fonte == "yf":
        try:
            dados = yf.Ticker(codigo).history(start=start)
        except Exception:
            dados = pd.DataFrame()
        if dados.empty:
            try:
                dados = yf.Ticker(codigo).history(period="max")
            except Exception:
                dados = pd.DataFrame()
        if not dados.empty:
            return dados["Close"].dropna()
        return pd.Series(dtype=float)

    elif fonte == "ipea":
        try:
            df = ipea.timeseries(codigo)
            col_valor = [c for c in df.columns if "VALUE" in c.upper()]
            if col_valor:
                serie = df[col_valor[0]].dropna()
            else:
                serie = df.iloc[:, -1].dropna()
            serie.index = pd.to_datetime(serie.index)
            serie = serie[serie.index >= start]
            serie = serie.astype(float)
            return serie
        except Exception:
            return pd.Series(dtype=float)

    elif fonte == "abras":
        try:
            df = get_abras_df()
            serie = df[codigo].dropna()
            serie = serie[serie.index >= start]
            return serie.astype(float)
        except Exception:
            return pd.Series(dtype=float)

    elif fonte == "caged":
        try:
            s = get_caged_serie()
            s = s[s.index >= start]
            return s
        except Exception:
            return pd.Series(dtype=float)

    elif fonte == "cepea":
        try:
            s = get_cepea_serie(codigo)
            s = s[s.index >= start]
            return s
        except Exception:
            return pd.Series(dtype=float)

    elif fonte == "anfavea":
        try:
            s = get_anfavea_serie(codigo)
            s = s[s.index >= start]
            return s
        except Exception:
            return pd.Series(dtype=float)

    elif fonte == "abcr":
        try:
            s = get_abcr_serie(codigo)
            s = s[s.index >= start]
            return s
        except Exception:
            return pd.Series(dtype=float)

    return pd.Series(dtype=float)


# === APP DASH ===
app = dash.Dash(__name__)
server = app.server  # exposto para o gunicorn (deploy Render)

# Organizar opções do dropdown por categoria
opcoes_dropdown = []
categorias = {
    "AÇÕES B3": [k for k in ativos if ativos[k]["fonte"] == "yf" and ativos[k]["unidade"] == "R$" and "(" in k and "SA" in ativos[k]["codigo"]],
    "COMMODITIES BRASIL": [k for k in ativos if (ativos[k]["fonte"] == "ipea" and "Brasil" in k) or "Atacado" in k or "CEPEA" in k],
    "PAPELÃO / CELULOSE": [k for k in ativos if "Papelão" in k or "Celulose" in k or "Produção Industrial" in k],
    "CONSUMO / VAREJO": [k for k in ativos if "Lares" in k or "Supermercados" in k],
    "MERCADO DE TRABALHO": [k for k in ativos if "CAGED" in k],
    "ENERGIA": [k for k in ativos if "Energia" in k],
    "AUTOVEÍCULOS (ANFAVEA)": [k for k in ativos if "Autoveículos" in k or "Automóveis" in k or "Caminhões" in k],
    "RODOVIAS (ABCR)": [k for k in ativos if "ABCR" in k],
    "COMMODITIES INTERNACIONAIS": [k for k in ativos if "CME" in k or "Coffee" in k or "Petróleo" in k or "Ouro" in k or "Prata" in k or "Internacional" in k],
    "ÍNDICES / CÂMBIO": [k for k in ativos if "Real" in k or "Ibovespa" in k or "S&P" in k or "Bitcoin" in k or "Nubank" in k],
}

for cat, nomes in categorias.items():
    for nome in nomes:
        if nome in ativos:
            opcoes_dropdown.append({"label": f"[{cat}] {nome}", "value": nome})

app.layout = html.Div(style={"fontFamily": "Segoe UI, Arial, sans-serif", "backgroundColor": "#f5f6fa", "minHeight": "100vh"}, children=[

    # Header
    html.Div(style={"backgroundColor": "#1a1a2e", "padding": "20px 40px", "color": "white"}, children=[
        html.H1("Dash do Claudinho e Ze_Lele", style={"margin": "0", "fontSize": "28px"}),
        html.P("Ações B3, Boi Gordo, Milho e Soja do Brasil, commodities internacionais e mais",
               style={"margin": "5px 0 0 0", "color": "#aaa", "fontSize": "14px"}),
        html.P("by Claudinho e Ze_Lele ★",
               style={"margin": "8px 0 0 0", "color": "#f1c40f", "fontSize": "12px", "fontStyle": "italic"}),
    ]),

    # Tabs
    dcc.Tabs(id="tabs", value="tab-selecao", style={"marginTop": "0"}, children=[

        # Aba 1 - Seleção
        dcc.Tab(label="Selecionar Ativo", value="tab-selecao",
            style={"padding": "12px 24px", "fontWeight": "bold"},
            selected_style={"padding": "12px 24px", "fontWeight": "bold", "borderTop": "3px solid #1a73e8"},
            children=[
                html.Div(style={"padding": "40px", "maxWidth": "700px", "margin": "0 auto"}, children=[

                    html.H3("Escolha o ativo:", style={"marginBottom": "15px", "color": "#333"}),

                    dcc.Dropdown(
                        id="dropdown-acao",
                        options=opcoes_dropdown,
                        value="Petrobras PN (PETR4)",
                        placeholder="Selecione ou pesquise um ativo...",
                        style={"fontSize": "16px", "marginBottom": "25px"},
                        searchable=True,
                    ),

                    html.H3("Período:", style={"marginBottom": "15px", "color": "#333"}),

                    dcc.Dropdown(
                        id="dropdown-periodo",
                        options=[
                            {"label": "1 Ano", "value": "1"},
                            {"label": "5 Anos", "value": "5"},
                            {"label": "10 Anos", "value": "10"},
                            {"label": "Desde 2000", "value": "2000"},
                            {"label": "Máximo disponível", "value": "max"},
                        ],
                        value="2000",
                        style={"fontSize": "16px", "marginBottom": "30px"},
                    ),

                    html.H3("Médias Móveis:", style={"marginBottom": "15px", "color": "#333"}),

                    html.Div(style={"marginBottom": "20px"}, children=[
                        dcc.Checklist(
                            id="check-medias",
                            options=[
                                {"label": " MM 21 (curto prazo)", "value": "21"},
                                {"label": " MM 50 (médio prazo)", "value": "50"},
                                {"label": " MM 200 (longo prazo)", "value": "200"},
                            ],
                            value=["21", "50", "200"],
                            inline=True,
                            style={"fontSize": "15px"},
                            inputStyle={"marginRight": "5px"},
                            labelStyle={"marginRight": "25px"},
                        ),
                    ]),

                    html.H3("Painéis adicionais:", style={"marginBottom": "15px", "color": "#333"}),

                    html.Div(style={"marginBottom": "30px"}, children=[
                        dcc.Checklist(
                            id="check-paineis",
                            options=[
                                {"label": " Sigma (Z-Score)", "value": "sigma"},
                                {"label": " Variação Anual (244d)", "value": "var244"},
                            ],
                            value=["sigma", "var244"],
                            inline=True,
                            style={"fontSize": "15px"},
                            inputStyle={"marginRight": "5px"},
                            labelStyle={"marginRight": "25px"},
                        ),
                    ]),

                    html.Button("Gerar Gráfico", id="btn-gerar", n_clicks=0,
                        style={
                            "backgroundColor": "#1a73e8", "color": "white", "border": "none",
                            "padding": "14px 40px", "fontSize": "16px", "borderRadius": "8px",
                            "cursor": "pointer", "fontWeight": "bold",
                        }
                    ),

                    html.Div(id="status-msg", style={"marginTop": "20px", "color": "#666", "fontSize": "14px"}),
                ]),
            ]
        ),

        # Aba 2 - Gráfico
        dcc.Tab(label="Gráfico", value="tab-grafico",
            style={"padding": "12px 24px", "fontWeight": "bold"},
            selected_style={"padding": "12px 24px", "fontWeight": "bold", "borderTop": "3px solid #1a73e8"},
            children=[
                html.Div(style={"padding": "20px"}, children=[
                    dcc.Loading(
                        id="loading",
                        type="circle",
                        children=[
                            html.Div(id="info-acao", style={"padding": "10px 20px", "fontSize": "14px", "color": "#555"}),
                            dcc.Graph(id="grafico-principal", style={"height": "85vh"}),
                        ]
                    ),
                ]),
            ]
        ),
    ]),
])


@callback(
    Output("grafico-principal", "figure"),
    Output("tabs", "value"),
    Output("status-msg", "children"),
    Output("info-acao", "children"),
    Input("btn-gerar", "n_clicks"),
    State("dropdown-acao", "value"),
    State("dropdown-periodo", "value"),
    State("check-medias", "value"),
    State("check-paineis", "value"),
    prevent_initial_call=True,
)
def gerar_grafico(n_clicks, nome_ativo, periodo, medias, paineis):
    paineis = paineis or []
    mostrar_sigma = "sigma" in paineis
    mostrar_var244 = "var244" in paineis

    if not nome_ativo or nome_ativo not in ativos:
        fig = go.Figure()
        fig.add_annotation(text="Selecione um ativo.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=20))
        return fig, "tab-grafico", "Nenhum ativo selecionado.", ""

    ativo_info = ativos[nome_ativo]
    unidade = ativo_info["unidade"]

    # Definir data inicial
    if periodo == "max":
        start = "1990-01-01"
    elif periodo == "2000":
        start = "2000-01-01"
    else:
        start = (datetime.now() - timedelta(days=int(periodo) * 365)).strftime("%Y-%m-%d")

    # Buscar dados
    serie = buscar_dados(ativo_info, start)

    # === TIPO ESPECIAL: ABRAS com média 12m + eventos ===
    if ativo_info.get("tipo") == "abras_mm12" and not serie.empty:
        mm12 = serie.rolling(window=12).mean().dropna()
        cores_b = ["#2ecc71" if v >= 0 else "#e74c3c" for v in mm12.values]
        ultimo_mes = mm12.index[-1].strftime("%m/%Y")
        ultimo_valor_mm12 = mm12.iloc[-1]
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=mm12.index, y=mm12.values, marker_color=cores_b,
            hovertemplate="Mês: %{x|%m/%Y}<br>Média 12m: %{y:+.2f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

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
            fig.add_vrect(x0=pd.Timestamp(inicio), x1=pd.Timestamp(fim),
                          fillcolor="gold", opacity=0.45, line_width=0)
            fig.add_annotation(
                x=pd.Timestamp(inicio) + (pd.Timestamp(fim) - pd.Timestamp(inicio)) / 2,
                y=1, yref="paper", text=rotulo, showarrow=False,
                font=dict(size=9, color="#8B4513"), yshift=-8,
            )
        for inicio, fim, rotulo in eleicoes:
            fig.add_vrect(x0=pd.Timestamp(inicio), x1=pd.Timestamp(fim),
                          fillcolor="#f1c40f", opacity=0.25, line_width=0)
            fig.add_annotation(
                x=pd.Timestamp(inicio) + (pd.Timestamp(fim) - pd.Timestamp(inicio)) / 2,
                y=0, yref="paper", text=rotulo, showarrow=False,
                font=dict(size=7, color="#7d6608"), yshift=8, textangle=-90,
            )

        fig.update_layout(
            title=dict(
                text=f"{nome_ativo}<br>"
                     f"<span style='font-size:13px; color:gray;'>"
                     f"Média dos últimos 12 meses corridos — YoY Real | "
                     f"Última: {ultimo_valor_mm12:+.2f}% ({ultimo_mes}) | "
                     f"Áreas amarelas: Copas do Mundo (forte) e Eleições (claro) | "
                     f"Atualizado em: {data_atual} | Fonte: ABRAS</span>",
                font=dict(size=18),
            ),
            template="plotly_white",
            hovermode="x unified",
            showlegend=False,
            xaxis_title="Mês/Ano",
            yaxis_title="Média 12m YoY (%)",
            height=700,
        )
        info = f"Consumo nos Lares - ABRAS | Média 12m YoY: {ultimo_valor_mm12:+.2f}% ({ultimo_mes})"
        return fig, "tab-grafico", "Gráfico gerado com sucesso!", info

    # === TIPO GENÉRICO: VARIAÇÃO ANUAL (12m vs 12m anteriores) ===
    if ativo_info.get("tipo") == "var_anual" and not serie.empty:
        soma_12m = serie.rolling(window=12).sum()
        var = (soma_12m - soma_12m.shift(12)).dropna()
        cores_b = ["#2ecc71" if v >= 0 else "#e74c3c" for v in var.values]
        var_atual = var.iloc[-1]
        mes_var = var.index[-1].strftime("%m/%Y")
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=var.index, y=var.values, marker_color=cores_b,
            hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:+,.0f} " + unidade + "<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

        cor_ultimo = "#2ecc71" if var_atual >= 0 else "#e74c3c"
        sinal = "+" if var_atual >= 0 else ""
        fig.add_annotation(
            x=0.99, y=0.98, xref="paper", yref="paper",
            text=f"<b>ÚLTIMO MÊS ({mes_var})</b><br>"
                 f"<span style='font-size:22px; color:{cor_ultimo};'><b>{sinal}{var_atual:,.0f}</b></span><br>"
                 f"<span style='font-size:11px; color:#555;'>variação anual ({unidade})</span>",
            showarrow=False, align="center",
            xanchor="right", yanchor="top",
            bordercolor=cor_ultimo, borderwidth=2, borderpad=10,
            bgcolor="rgba(255, 255, 255, 0.95)",
            font=dict(size=12, color="#333"),
        )

        fig.update_layout(
            title=dict(
                text=f"{nome_ativo} — Variação Anual<br>"
                     f"<span style='font-size:13px; color:gray;'>"
                     f"Diferença entre últimos 12 meses e 12 meses anteriores | "
                     f"Variação atual: {var_atual:+,.0f} {unidade} | "
                     f"Atualizado em: {data_atual} | Fonte: IPEA</span>",
                font=dict(size=18),
            ),
            template="plotly_white",
            hovermode="x unified",
            showlegend=False,
            xaxis_title="Mês/Ano",
            yaxis_title=f"Variação Anual ({unidade})",
            yaxis=dict(tickformat=",.0f"),
            height=700,
        )
        info = f"{nome_ativo} | Variação Anual: {var_atual:+,.0f} {unidade} ({mes_var})"
        return fig, "tab-grafico", "Gráfico gerado com sucesso!", info

    # === TIPO ESPECIAL: CAGED — Variação Anual de Empregos ===
    if ativo_info.get("tipo") == "caged" and not serie.empty:
        soma_12m = serie.rolling(window=12).sum()
        var = (soma_12m - soma_12m.shift(12)).dropna()
        cores_b = ["#2ecc71" if v >= 0 else "#e74c3c" for v in var.values]
        var_atual = var.iloc[-1]
        mes_var = var.index[-1].strftime("%m/%Y")
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=var.index, y=var.values, marker_color=cores_b,
            hovertemplate="Mês: %{x|%m/%Y}<br>Variação: %{y:+,.0f} empregos<extra></extra>",
        ))
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)

        cor_ultimo = "#2ecc71" if var_atual >= 0 else "#e74c3c"
        sinal = "+" if var_atual >= 0 else ""
        fig.add_annotation(
            x=0.99, y=0.98, xref="paper", yref="paper",
            text=f"<b>ÚLTIMO MÊS ({mes_var})</b><br>"
                 f"<span style='font-size:22px; color:{cor_ultimo};'><b>{sinal}{var_atual:,.0f}</b></span><br>"
                 f"<span style='font-size:11px; color:#555;'>variação anual (empregos)</span>",
            showarrow=False, align="center",
            xanchor="right", yanchor="top",
            bordercolor=cor_ultimo, borderwidth=2, borderpad=10,
            bgcolor="rgba(255, 255, 255, 0.95)",
            font=dict(size=12, color="#333"),
        )

        fig.update_layout(
            title=dict(
                text=f"CAGED — Variação Anual de Empregos Formais no Brasil<br>"
                     f"<span style='font-size:13px; color:gray;'>"
                     f"Diferença entre o saldo dos últimos 12 meses e o saldo dos 12 meses anteriores | "
                     f"Variação atual: {var_atual:+,.0f} empregos | "
                     f"Atualizado em: {data_atual} | Fontes: CAGED (antigo + novo) via IPEA</span>",
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
        info = f"CAGED | Variação Anual: {var_atual:+,.0f} empregos ({mes_var})"
        return fig, "tab-grafico", "Gráfico gerado com sucesso!", info

    if serie.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Nenhum dado encontrado para '{nome_ativo}'.",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=18)
        )
        return fig, "tab-grafico", f"Erro: dados não encontrados.", ""

    ultimo_valor = serie.iloc[-1]
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # === CALCULOS DE SIGMA E VARIAÇÃO (janela 245/244) ===
    JANELA = 245
    media_anual = serie.rolling(window=JANELA).mean()
    desv_p = serie.rolling(window=JANELA).std()
    sigma = (serie - media_anual) / desv_p
    variacao_244 = (serie / serie.shift(JANELA - 1) - 1) * 100

    # Determinar quantos painéis e seus títulos
    paineis_extras = []
    if mostrar_sigma:
        paineis_extras.append(("sigma", "Sigma - Z-Score (janela 245 pregões)"))
    if mostrar_var244:
        paineis_extras.append(("var244", "Variação (janela 244 pregões) %"))

    n_rows = 1 + len(paineis_extras)
    if n_rows == 1:
        row_heights = [1.0]
        altura_total = 700
    elif n_rows == 2:
        row_heights = [0.65, 0.35]
        altura_total = 850
    else:
        row_heights = [0.5, 0.25, 0.25]
        altura_total = 1000

    titulos = ["Preço"] + [t for _, t in paineis_extras]

    fig = make_subplots(
        rows=n_rows, cols=1,
        row_heights=row_heights,
        vertical_spacing=0.07,
        subplot_titles=titulos,
    )

    # === PAINEL 1: PREÇO ===
    fig.add_trace(go.Scatter(
        x=serie.index, y=serie.values, mode="lines", name=nome_ativo,
        line=dict(color="#006400", width=1.5),
        fill="tozeroy", fillcolor="rgba(0, 100, 0, 0.1)",
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Preço: " + unidade.split("/")[0] + " %{y:.2f}<extra></extra>"
    ), row=1, col=1)

    # Médias móveis
    if len(serie) > 200:
        cores_mm = {"21": "#e67e22", "50": "#3498db", "200": "#e74c3c"}
        estilos_mm = {"21": "dot", "50": "dash", "200": "solid"}
        for mm in (medias or []):
            janela = int(mm)
            mm_serie = serie.rolling(window=janela).mean()
            fig.add_trace(go.Scatter(
                x=mm_serie.index, y=mm_serie.values, mode="lines", name=f"MM {mm}",
                line=dict(color=cores_mm[mm], width=1.2, dash=estilos_mm[mm]),
                hovertemplate=f"MM{mm}: %{{y:.2f}}<extra></extra>"
            ), row=1, col=1)

    # Mapa de qual painel/linha cada gráfico extra ocupa
    paineis_row = {nome: idx + 2 for idx, (nome, _) in enumerate(paineis_extras)}

    sigma_clean = sigma.dropna()
    var_clean = variacao_244.dropna()

    # === PAINEL: SIGMA ===
    if "sigma" in paineis_row:
        r = paineis_row["sigma"]
        fig.add_trace(go.Scatter(
            x=sigma_clean.index, y=sigma_clean.values,
            mode="lines", name="Sigma",
            line=dict(color="#8e44ad", width=1.5),
            fill="tozeroy", fillcolor="rgba(142, 68, 173, 0.15)",
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Sigma: %{y:.2f}σ<extra></extra>",
            showlegend=False,
        ), row=r, col=1)

        niveis_sigma = [
            (5, "#7b0000", "dash"), (4, "#c0392b", "dash"), (3, "#e74c3c", "dash"),
            (2, "#e67e22", "dot"), (1, "#f39c12", "dot"),
            (-1, "#f39c12", "dot"), (-2, "#e67e22", "dot"),
            (-3, "#e74c3c", "dash"), (-4, "#c0392b", "dash"), (-5, "#7b0000", "dash"),
        ]
        for nivel, cor, dash in niveis_sigma:
            fig.add_hline(y=nivel, line_dash=dash, line_color=cor, opacity=0.4,
                          annotation_text=f"{nivel:+d}σ", annotation_position="right",
                          row=r, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5, row=r, col=1)
        fig.update_yaxes(title_text="Sigma (σ)", row=r, col=1)

    # === PAINEL: VARIAÇÃO 244d ===
    if "var244" in paineis_row:
        r = paineis_row["var244"]
        fig.add_trace(go.Scatter(
            x=var_clean.index, y=var_clean.values,
            mode="lines", name="Variação 244d",
            line=dict(color="#2c3e50", width=1.5),
            fill="tozeroy", fillcolor="rgba(52, 152, 219, 0.15)",
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Variação: %{y:.2f}%<extra></extra>",
            showlegend=False,
        ), row=r, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5, row=r, col=1)
        fig.update_yaxes(title_text="Variação (%)", row=r, col=1)

    fonte_txt = "IPEA/DERAL" if ativo_info["fonte"] == "ipea" else "Yahoo Finance"

    sigma_atual = sigma_clean.iloc[-1] if not sigma_clean.empty else 0
    var_atual = var_clean.iloc[-1] if not var_clean.empty else 0

    fig.update_layout(
        title=dict(
            text=f"{nome_ativo}<br>"
                 f"<span style='font-size:13px; color:gray;'>"
                 f"Último: {unidade.split('/')[0]} {ultimo_valor:.2f} | "
                 f"Sigma atual: {sigma_atual:+.2f}σ | "
                 f"Variação 244d: {var_atual:+.2f}% | "
                 f"Atualizado em: {data_atual} | Fonte: {fonte_txt}</span>",
            font=dict(size=18),
        ),
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.7)"),
        height=altura_total,
    )
    fig.update_yaxes(title_text=f"Preço ({unidade})", row=1, col=1)
    fig.update_xaxes(title_text="Data", row=n_rows, col=1)

    info = f"Exibindo: {nome_ativo} | Unidade: {unidade} | Fonte: {fonte_txt} | Último valor: {unidade.split('/')[0]} {ultimo_valor:.2f}"

    return fig, "tab-grafico", "Gráfico gerado com sucesso!", info


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    is_local = "PORT" not in os.environ
    if is_local:
        Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        print(f"\n Dashboard rodando em: http://127.0.0.1:{port}")
        print(" Pressione Ctrl+C para encerrar\n")
    app.run(debug=False, host="0.0.0.0", port=port)
