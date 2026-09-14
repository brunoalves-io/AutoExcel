from __future__ import annotations

import pandas as pd
import streamlit as st

from core import (
    build_excel_bytes,
    build_multi_excel_bytes,
    normalize_lots,
    normalize_quadra,
    quadra_sort_key,
    validate_lots,
)
from dxf_reader import read_dxf_bytes

VERSION = "V4.10"
STATE_PREFIX = "v410"

st.set_page_config(page_title="AutoExcel by AB Alves", page_icon="📐", layout="wide")
st.title("📐 AutoExcel by AB Alves")
st.markdown(
    """
    <style>
    div.stDownloadButton > button,
    div[data-testid="stDownloadButton"] button {
        background-color: #16a34a !important;
        border-color: #16a34a !important;
        color: #ffffff !important;
    }
    div.stDownloadButton > button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        background-color: #15803d !important;
        border-color: #15803d !important;
        color: #ffffff !important;
    }
    div.stDownloadButton > button:focus,
    div[data-testid="stDownloadButton"] button:focus {
        box-shadow: 0 0 0 0.2rem rgba(22, 163, 74, 0.25) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Somente DXF. Lote e área são vinculados pela própria polilinha; quadras partidas são recompostas pela numeração contínua e rótulos ligeiramente fora da polilinha são recuperados pela geometria do DXF."
)

with st.sidebar:
    st.header("Configuração")
    st.success("🔒 Processamento 100% local")
    st.info(
        "O app aceita apenas **DXF** e detecta automaticamente rótulos como **QUADRA 01**, **QUADRA 02** etc."
    )
    integer_digits = st.selectbox(
        "Dígitos antes da vírgula na área",
        [3, 4],
        index=0,
        help="Usado como apoio quando o texto da área estiver sem separador decimal. Ex.: 63810 → 638,10.",
    )
    c1, c2 = st.columns(2)
    area_min = c1.number_input("Área mín.", min_value=1.0, value=100.0, step=10.0)
    area_max = c2.number_input("Área máx.", min_value=10.0, value=5000.0, step=100.0)
    group_equal = st.checkbox("Agrupar áreas iguais consecutivas", value=True)
    st.caption("Todas as quadras são exportadas em uma única planilha, uma abaixo da outra.")

uploaded = st.file_uploader("Envie o arquivo DXF do AutoCAD", type=["dxf"], accept_multiple_files=False)

if f"lots_{STATE_PREFIX}" not in st.session_state:
    st.session_state[f"lots_{STATE_PREFIX}"] = pd.DataFrame(
        columns=["quadra", "lote", "area_m2", "confidence", "status", "note"]
    )
if f"details_{STATE_PREFIX}" not in st.session_state:
    st.session_state[f"details_{STATE_PREFIX}"] = pd.DataFrame()
if f"obs_{STATE_PREFIX}" not in st.session_state:
    st.session_state[f"obs_{STATE_PREFIX}"] = ""
if f"stats_{STATE_PREFIX}" not in st.session_state:
    st.session_state[f"stats_{STATE_PREFIX}"] = {}


def save_result(result):
    rows = result.get("lotes", [])
    normalized_rows = []
    for r in rows:
        normalized_rows.append(
            {
                "quadra": normalize_quadra(r.get("quadra") or "SEM_QUADRA"),
                "lote": r.get("lote"),
                "area_m2": r.get("area_m2"),
                "confidence": r.get("confidence"),
                "status": r.get("status", ""),
                "note": r.get("note", ""),
            }
        )
    st.session_state[f"lots_{STATE_PREFIX}"] = pd.DataFrame(normalized_rows)
    st.session_state[f"details_{STATE_PREFIX}"] = pd.DataFrame(rows)
    st.session_state[f"obs_{STATE_PREFIX}"] = result.get("observacoes", "")
    st.session_state[f"stats_{STATE_PREFIX}"] = result.get("stats", {})
    return normalized_rows


def build_groups_from_editor(df: pd.DataFrame):
    grouped = {}
    for _, row in df.iterrows():
        q = normalize_quadra(row.get("quadra"))
        if pd.isna(row.get("lote")) or pd.isna(row.get("area_m2")):
            continue
        grouped.setdefault(q, []).append(row.to_dict())
    out = {q: normalize_lots(rows) for q, rows in grouped.items()}
    return dict(sorted(out.items(), key=lambda kv: quadra_sort_key(kv[0])))


def streamlit_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    safe = df.copy()
    for col in safe.columns:
        if safe[col].dtype == "object":
            def to_text(value):
                if value is None:
                    return ""
                try:
                    missing = pd.isna(value)
                    if isinstance(missing, bool) and missing:
                        return ""
                except (TypeError, ValueError):
                    pass
                if isinstance(value, str):
                    return value
                return str(value)
            safe[col] = safe[col].map(to_text).astype("string")
    return safe


if uploaded:
    data = uploaded.getvalue()

    st.info(
        "🎯 **Leitura DXF topológica:** número e área são lidos diretamente e vinculados pela mesma polilinha do lote. Sem OCR e sem associação por mera proximidade."
    )
    left, right = st.columns([1.45, 1])
    with left:
        st.subheader(f"📄 {uploaded.name}")
        st.write(
            "O app detecta cada lote pela LWPOLYLINE do lote que contém seu número e sua área, agrupa os lotes contíguos em quadras e então associa cada grupo ao rótulo QUADRA. "
            "Como regra do projeto, cada quadra deve ter numeração contínua começando em **L.01**, independentemente de quantos lotes ela possua."
        )
        st.caption(
            "Ex.: uma quadra com 4 lotes deve conter L.01, L.02, L.03 e L.04. O app não espera L.05."
        )
    with right:
        st.subheader("Leitura direta")
        if st.button("📐 Ler DXF · todas as quadras", type="primary", use_container_width=True):
            try:
                with st.spinner("Lendo quadras, lotes e áreas diretamente do DXF…"):
                    result = read_dxf_bytes(
                        data,
                        integer_digits=int(integer_digits),
                        area_min=float(area_min),
                        area_max=float(area_max),
                    )
                rows = save_result(result)
                qs = sorted({r["quadra"] for r in rows}, key=quadra_sort_key)
                st.success(f"Leitura concluída: {len(rows)} lote(s) em {len(qs)} quadra(s).")
            except Exception as exc:
                st.error(str(exc))

    if st.session_state[f"obs_{STATE_PREFIX}"]:
        st.info(st.session_state[f"obs_{STATE_PREFIX}"])

    current_df = st.session_state[f"lots_{STATE_PREFIX}"]
    if not current_df.empty:
        st.subheader("Resumo por quadra")
        summary_source = current_df.dropna(subset=["quadra", "lote", "area_m2"]).copy()
        if not summary_source.empty:
            summary_source["quadra"] = summary_source["quadra"].map(normalize_quadra)
            summary = (
                summary_source.groupby("quadra", as_index=False)
                .agg(
                    lotes=("lote", "count"),
                    area_total_m2=("area_m2", "sum"),
                    primeiro_lote=("lote", "min"),
                    ultimo_lote=("lote", "max"),
                )
            )
            summary = summary.sort_values("quadra", key=lambda s: s.map(quadra_sort_key))
            summary["area_total_m2"] = summary["area_total_m2"].round(2)
            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "quadra": "Quadra",
                    "lotes": "Lotes",
                    "area_total_m2": st.column_config.NumberColumn("Área total (m²)", format="%.2f"),
                    "primeiro_lote": st.column_config.NumberColumn("Primeiro", format="%d"),
                    "ultimo_lote": st.column_config.NumberColumn("Último", format="%d"),
                },
            )

    st.subheader("Revisar resultado")
    st.caption(
        "A coluna **Quadra** permanece editável. Se a associação geométrica colocar um lote na quadra errada, você pode corrigir antes de exportar."
    )
    edited = st.data_editor(
        st.session_state[f"lots_{STATE_PREFIX}"],
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "quadra": st.column_config.TextColumn("Quadra", help="Ex.: 01, 02, 03"),
            "lote": st.column_config.NumberColumn("Lote", min_value=1, step=1, format="%d"),
            "area_m2": st.column_config.NumberColumn("Área (m²)", min_value=0.01, step=0.01, format="%.2f"),
            "confidence": st.column_config.NumberColumn(
                "Confiança", min_value=0.0, max_value=1.0, format="%.2f", disabled=True
            ),
            "status": st.column_config.TextColumn("Status", disabled=True),
            "note": st.column_config.TextColumn("Observação", disabled=True),
        },
        key="editor_local_v410",
    )
    st.session_state[f"lots_{STATE_PREFIX}"] = edited

    incomplete_mask = (
        edited["quadra"].isna()
        | (edited["quadra"].astype(str).str.strip() == "")
        | edited["lote"].isna()
        | edited["area_m2"].isna()
    ) if not edited.empty else pd.Series(dtype=bool)
    incomplete = edited[incomplete_mask] if not edited.empty else edited

    validation_errors = []
    validation_warnings = []
    try:
        grouped_lots = build_groups_from_editor(edited)
        if "SEM_QUADRA" in grouped_lots:
            validation_errors.append(
                "Há lote(s) sem quadra definida. Corrija a coluna Quadra antes de gerar o Excel."
            )
        for q, lots in grouped_lots.items():
            result = validate_lots(lots)
            validation_errors.extend([f"Quadra {q}: {m}" for m in result["errors"]])
            validation_warnings.extend([f"Quadra {q}: {m}" for m in result["warnings"]])
    except Exception as exc:
        grouped_lots = {}
        validation_errors.append(str(exc))

    for msg in validation_errors:
        st.error(msg)
    for msg in validation_warnings:
        st.warning(msg)
    if not incomplete.empty:
        st.warning(f"Há {len(incomplete)} linha(s) incompleta(s).")

    if grouped_lots:
        total_lots = sum(len(v) for v in grouped_lots.values())
        total_area = sum(x.area_m2 for lots in grouped_lots.values() for x in lots)
        a, b, c = st.columns(3)
        a.metric("Quadras", len(grouped_lots))
        b.metric("Lotes completos", total_lots)
        c.metric(
            "Área total",
            f"{total_area:,.2f} m²".replace(",", "X").replace(".", ",").replace("X", "."),
        )

    with st.expander("🔬 Diagnóstico"):
        if st.session_state[f"stats_{STATE_PREFIX}"]:
            st.json(st.session_state[f"stats_{STATE_PREFIX}"])
        if not st.session_state[f"details_{STATE_PREFIX}"].empty:
            diagnostic_df = streamlit_safe_dataframe(st.session_state[f"details_{STATE_PREFIX}"])
            try:
                st.dataframe(diagnostic_df, use_container_width=True, hide_index=True)
            except Exception:
                st.caption("Diagnóstico exibido em modo de compatibilidade.")
                st.json(diagnostic_df.astype(str).to_dict(orient="records"))

    st.divider()
    st.subheader("Gerar Excel")
    if len(grouped_lots) > 1:
        st.write(
            "Será criado **um único arquivo Excel com uma única planilha**, contendo todas as quadras **uma abaixo da outra**."
        )
    elif len(grouped_lots) == 1:
        st.write("Será criada a tabela da quadra no mesmo modelo visual definido anteriormente.")

    can_generate = bool(grouped_lots) and not validation_errors and incomplete.empty
    if can_generate:
        try:
            if len(grouped_lots) == 1:
                q, lots = next(iter(grouped_lots.items()))
                excel = build_excel_bytes(
                    lots=lots,
                    quadra=q,
                    group_equal_consecutive=group_equal,
                )
                filename = f"Quadra_{q.replace(' ', '_')}_Areas_Lotes.xlsx"
            else:
                excel = build_multi_excel_bytes(
                    quadras=grouped_lots,
                    group_equal_consecutive=group_equal,
                )
                filename = "Areas_Lotes_Todas_Quadras.xlsx"
            st.download_button(
                "⬇️ Baixar Excel",
                data=excel,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Erro ao gerar Excel: {exc}")
    else:
        st.button("⬇️ Baixar Excel", disabled=True, use_container_width=True)
else:
    st.info("Envie um arquivo **DXF** do AutoCAD para iniciar.")

with st.expander(f"Como a {VERSION} valida as quadras?"):
    st.markdown(
        """
1. Aceita **somente DXF**. Não há mais modo PRINT nem OCR.
2. Lê diretamente `TEXT`, `MTEXT` e atributos do DXF.
3. Detecta os rótulos **QUADRA 01**, **QUADRA 02**, **QUADRA 03** etc.
4. Localiza as **LWPOLYLINE** dos lotes e verifica qual número e qual área estão dentro de cada polígono. Se uma LWPOLYLINE estiver sem a flag CLOSED, ela só é aceita como lote quando o fechamento implícito é confirmado pela área geométrica do polígono e pela área escrita no próprio lote.
5. Agrupa automaticamente polígonos que compartilham divisas em componentes físicos.
6. Se o ponto técnico de um número/área ficar poucos milímetros fora da polilinha, recupera o rótulo usando a borda do lote, sem OCR.
7. Associa um componente principal a cada rótulo **QUADRA XX** e, quando uma mesma quadra estiver fisicamente partida, incorpora os componentes extras cuja numeração completa a sequência sem duplicidades.
8. Em cada quadra, a numeração é obrigatoriamente **contínua a partir de L.01**. A quantidade é simplesmente o último número encontrado após a recomposição.
9. Assim, uma quadra com L.01 a L.04 tem exatamente 4 lotes; lotes de uma quadra vizinha não entram no grupo só por estarem próximos.
10. Se houver L.01, L.02 e L.04 dentro do mesmo componente físico, o app aponta **L.03 como ausente**.
11. Todas as quadras são exportadas na mesma planilha, uma abaixo da outra.
"""
    )
