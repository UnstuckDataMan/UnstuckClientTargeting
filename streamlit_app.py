
import json
import io
from pathlib import Path
import urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Industry & Niche Picker", page_icon="🧭", layout="wide")

# --- Load data ---
DATA_PATH = Path(__file__).parent / "data.json"
try:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"Failed to read data.json: {e}")
    st.stop()

# Normalise + sort
def normalise(rows):
    out = []
    for r in rows:
        ind = str(r.get("industry","")).strip()
        niches = sorted({str(n).strip() for n in r.get("niches", []) if str(n).strip()})
        if ind and niches:
            out.append({"industry": ind, "niches": niches})
    out.sort(key=lambda x: x["industry"].lower())
    return out

DATA = normalise(raw)

# Build lookups
industries = [r["industry"] for r in DATA]
niches_map = {r["industry"]: r["niches"] for r in DATA}

# --- Query param state (shareable link) ---
qp = st.experimental_get_query_params()
pre_sel_inds = qp.get("industries", [])
pre_sel_niches = {}
for k, v in qp.items():
    if k.startswith("n_"):
        industry = urllib.parse.unquote(k[2:])
        pre_sel_niches[industry] = v  # list of niches

st.title("Industry & Niche Picker")
st.caption("Select industries, then choose specific niches. Export or share your selections via URL.")

# --- Search bars ---
c1, c2, _ = st.columns([2,2,1])
with c1:
    industry_query = st.text_input("Search industries", "")
with c2:
    niche_query = st.text_input("Filter niches", "")

# Filter industries by query
def match(q, s): return q.lower() in s.lower()
visible_industries = [i for i in industries if match(industry_query, i)]

# --- Selections state ---
default_inds = [i for i in visible_industries if i in pre_sel_inds] if pre_sel_inds else []
selected_industries = st.multiselect("1) Choose industries", options=visible_industries, default=default_inds)

# Build per-industry niche selections
selections = {}
total_niche_count = 0
for ind in selected_industries:
    all_niches = [n for n in niches_map[ind] if match(niche_query, n)]
    with st.expander(f"2) Select niches for: {ind}", expanded=True):
        # Buttons for select all / clear
        b1, b2 = st.columns(2)
        key_prefix = f"k_{ind}"
        def_all = pre_sel_niches.get(ind, []) if pre_sel_niches else []
        default_set = set(def_all) if def_all else set()
        chosen = set()
        with b1:
            if st.button("Select all", key=f"{key_prefix}_all"):
                chosen = set(all_niches)
        with b2:
            if st.button("Clear", key=f"{key_prefix}_clear"):
                chosen = set()

        cols = st.columns(2)
        for idx, niche in enumerate(all_niches):
            col = cols[idx % 2]
            with col:
                default_val = (niche in default_set) if pre_sel_niches else False
                if chosen:
                    default_val = (niche in chosen)
                picked = st.checkbox(niche, value=default_val, key=f"{key_prefix}_n_{niche}")
                if picked:
                    selections.setdefault(ind, []).append(niche)
                    total_niche_count += 1

# --- Exports ---
st.subheader("Selections summary")
st.caption(f"{len(selections)} industries • {total_niche_count} niches")
if selections:
    rows = []
    for ind, ns in selections.items():
        if not ns:
            rows.append({"industry": ind, "niche": ""})
        else:
            for n in ns:
                rows.append({"industry": ind, "niche": n})
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    json_bytes = io.BytesIO()
    json_bytes.write(json.dumps(selections, indent=2).encode("utf-8"))
    json_bytes.seek(0)
    st.download_button("Download JSON", data=json_bytes, file_name="selections.json", mime="application/json")

    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)
    st.download_button("Download CSV", data=csv_bytes, file_name="selections.csv", mime="text/csv")

    qp_out = {"industries": selected_industries}
    for ind, ns in selections.items():
        qp_out[f"n_{ind}"] = ns
    st.markdown("**Share this view** (encodes current selections):")
    st.code("?" + urllib.parse.urlencode(qp_out, doseq=True))

    if st.button("Update URL with selections"):
        st.experimental_set_query_params(**qp_out)
        st.success("URL updated — copy from your browser address bar.")
else:
    st.info("No selections yet. Pick at least one industry to begin.")

st.write("---")
st.caption("Tip: save this repository to GitHub and deploy on Streamlit Community Cloud. The app reads `data.json`.")
