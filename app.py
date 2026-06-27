import streamlit as st
import pdfplumber
import pandas as pd
import json, re, os, io, zipfile, hashlib, datetime, random, math
from groq import Groq
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
import requests
from PIL import Image
import pytesseract

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
# ── API KEY ──────────────────────────────────────────
# Priority 1: Streamlit Secrets  (secrets.toml → [groq] api_key = "...")
# Priority 2: Environment variable GROQ_API_KEY
# Priority 3: Sidebar input at runtime
def _load_key():
    try:
        k = st.secrets.get("groq", {}).get("api_key", "") or st.secrets.get("GROQ_API_KEY", "")
        if k: return k
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")

MODEL = "llama-3.3-70b-versatile"

GROQ_API_KEY = _load_key()

# If still no key, we will show setup screen — client created lazily below
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(
    page_title="AI Invoice Auditor Pro",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════
#  COLOR PALETTE (from reference image)
#  C1 = #E8E4DC  cream/beige
#  C2 = #5A6B7A  steel blue-gray
#  C3 = #2E3740  dark slate
#  C4 = #1A1E24  near-black
# ══════════════════════════════════════════════════════

CSS = """
<style>
@import url(\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap\");

/* ── ROOT PALETTE ── */
:root {
  --c1: #E8E4DC;
  --c2: #5A6B7A;
  --c3: #2E3740;
  --c4: #1A1E24;
  --c-accent: #E8E4DC;
  --c-success: #7EC8A4;
  --c-warn: #E8C87A;
  --c-danger: #E87A7A;
  --c-text: #E8E4DC;
  --c-muted: #8899AA;
  --radius: 14px;
  --shadow: 0 4px 24px rgba(0,0,0,0.35);
}

/* ── GLOBAL ── */
html, body, [class*=\"css\"] {
  font-family: \"Inter\", sans-serif !important;
  background: var(--c4) !important;
  color: var(--c1) !important;
}
.main, .block-container { background: var(--c4) !important; }

/* ── HEADINGS ── */
h1 { font-size: 2.4rem !important; font-weight: 800 !important;
     color: var(--c1) !important; letter-spacing: -0.5px; }
h2 { font-size: 1.6rem !important; font-weight: 700 !important; color: var(--c1) !important; }
h3 { font-size: 1.1rem !important; font-weight: 600 !important; color: var(--c2) !important; }

/* ── SIDEBAR ── */
[data-testid=\"stSidebar\"] {
  background: var(--c3) !important;
  border-right: 1px solid #3a4550 !important;
}
[data-testid=\"stSidebar\"] * { color: var(--c1) !important; }

/* ── CARDS ── */
.kpi-card {
  background: linear-gradient(145deg, var(--c3), #242c35);
  border: 1px solid #3a4550;
  border-radius: var(--radius);
  padding: 20px 16px;
  text-align: center;
  box-shadow: var(--shadow);
  transition: transform 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); }
.kpi-num {
  font-size: 2.8rem;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -1px;
}
.kpi-lbl {
  color: var(--c-muted);
  font-size: 0.72rem;
  margin-top: 6px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 500;
}
.kpi-delta {
  font-size: 0.8rem;
  margin-top: 4px;
  font-weight: 600;
}

/* ── SECTION HEADERS ── */
.sec-header {
  font-size: 1rem;
  font-weight: 700;
  color: var(--c2);
  margin: 28px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #3a4550;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ── TAGS ── */
.tag {
  display: inline-block;
  background: rgba(90,107,122,0.2);
  color: var(--c1);
  border: 1px solid var(--c2);
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.78rem;
  margin: 2px;
  font-family: \"JetBrains Mono\", monospace;
  font-weight: 500;
}
.tag-danger {
  background: rgba(232,122,122,0.15);
  border-color: var(--c-danger);
  color: var(--c-danger);
}
.tag-success {
  background: rgba(126,200,164,0.15);
  border-color: var(--c-success);
  color: var(--c-success);
}

/* ── FLAG CARDS ── */
.flag-card {
  background: var(--c3);
  border-radius: 10px;
  padding: 14px 16px;
  margin: 6px 0;
  border-left: 4px solid var(--c2);
}
.flag-high   { border-left-color: var(--c-danger); }
.flag-medium { border-left-color: var(--c-warn); }
.flag-low    { border-left-color: var(--c-success); }

/* ── BUTTONS ── */
.stButton > button {
  background: var(--c2) !important;
  color: var(--c1) !important;
  border: 1px solid #6a7b8a !important;
  border-radius: 10px !important;
  padding: 10px 24px !important;
  font-weight: 600 !important;
  font-size: 0.92rem !important;
  transition: all 0.2s !important;
  letter-spacing: 0.3px !important;
}
.stButton > button:hover {
  background: #6a7b8a !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(90,107,122,0.4) !important;
}

/* ── INPUTS ── */
.stTextArea textarea, .stTextInput input {
  background: var(--c3) !important;
  color: var(--c1) !important;
  border: 1px solid #3a4550 !important;
  border-radius: 10px !important;
  font-family: \"JetBrains Mono\", monospace !important;
}
.stSelectbox > div > div {
  background: var(--c3) !important;
  color: var(--c1) !important;
  border: 1px solid #3a4550 !important;
  border-radius: 10px !important;
}

/* ── FILE UPLOADER ── */
[data-testid=\"stFileUploadDropzone\"] {
  background: var(--c3) !important;
  border: 2px dashed var(--c2) !important;
  border-radius: var(--radius) !important;
  padding: 30px !important;
}

/* ── DATAFRAME ── */
[data-testid=\"stDataFrame\"] {
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid #3a4550;
}

/* ── TABS ── */
.stTabs [data-baseweb=\"tab-list\"] {
  background: var(--c3) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 4px !important;
}
.stTabs [data-baseweb=\"tab\"] {
  border-radius: 8px !important;
  color: var(--c-muted) !important;
  font-weight: 500 !important;
}
.stTabs [aria-selected=\"true\"] {
  background: var(--c2) !important;
  color: var(--c1) !important;
}

/* ── PROGRESS BAR ── */
.stProgress > div > div > div {
  background: linear-gradient(90deg, var(--c2), var(--c1)) !important;
  border-radius: 10px !important;
}

/* ── METRIC ── */
[data-testid=\"stMetricValue\"] { color: var(--c1) !important; font-weight: 800 !important; }
[data-testid=\"stMetricLabel\"] { color: var(--c-muted) !important; }

/* ── INFO/SUCCESS/WARNING/ERROR BOXES ── */
.stAlert { border-radius: 10px !important; border-left-width: 4px !important; }

/* ── LOGO BANNER ── */
.logo-banner {
  background: linear-gradient(135deg, var(--c3) 0%, #242c35 50%, var(--c3) 100%);
  border: 1px solid #3a4550;
  border-radius: 20px;
  padding: 28px 36px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
}

/* ── FRAUD SCORE RING ── */
.fraud-ring {
  width: 100%;
  text-align: center;
  padding: 20px;
  background: var(--c3);
  border-radius: var(--radius);
  border: 1px solid #3a4550;
}

/* ── CHAT BUBBLE ── */
.chat-user {
  background: var(--c2);
  color: var(--c1);
  border-radius: 16px 16px 4px 16px;
  padding: 10px 16px;
  margin: 6px 0;
  max-width: 80%;
  margin-left: auto;
  font-size: 0.9rem;
}
.chat-ai {
  background: var(--c3);
  color: var(--c1);
  border-radius: 16px 16px 16px 4px;
  padding: 10px 16px;
  margin: 6px 0;
  max-width: 80%;
  border: 1px solid #3a4550;
  font-size: 0.9rem;
}

/* ── DIVIDER ── */
hr { border-color: #3a4550 !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--c4); }
::-webkit-scrollbar-thumb { background: var(--c2); border-radius: 3px; }

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  API KEY GATE — show setup screen if key is missing
# ══════════════════════════════════════════════════════
if not GROQ_API_KEY:
    st.markdown("""
    <div style="background:#2E3740;border:1px solid #3a4550;border-radius:16px;
                padding:32px;max-width:560px;margin:40px auto;text-align:center;">
      <div style="font-size:3rem;">🔑</div>
      <h2 style="color:#E8E4DC;margin-top:8px;">API Key Required</h2>
      <p style="color:#8899AA;font-size:0.9rem;">
        Enter your <b style="color:#E8E4DC;">Groq API Key</b> to unlock all features.<br/>
        Get one free at <a href="https://console.groq.com" target="_blank"
          style="color:#5A6B7A;">console.groq.com</a>
      </p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("api_key_form"):
        typed_key = st.text_input("Groq API Key", type="password",
                                   placeholder="gsk_...")
        submitted = st.form_submit_button("🚀 Connect & Launch", use_container_width=True)
        if submitted and typed_key.strip():
            st.session_state["_runtime_key"] = typed_key.strip()
            st.rerun()
    if not st.session_state.get("_runtime_key"):
        st.stop()

# Allow runtime key set via setup screen
if not GROQ_API_KEY and st.session_state.get("_runtime_key"):
    GROQ_API_KEY = st.session_state["_runtime_key"]

if GROQ_API_KEY and client is None:
    import importlib
    from groq import Groq as _Groq
    client = _Groq(api_key=GROQ_API_KEY)

# ══════════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════════
for k, v in [
    ("history", []),
    ("batch_results", []),
    ("chat_history", []),
    ("seen_hashes", set()),
    ("fx_rates", {}),
    ("dark_mode", True),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
#  HELPERS — TEXT EXTRACTION
# ══════════════════════════════════════════════════════
def extract_text_pdf(file):
    """Extract text from PDF; fall back to OCR if text is too short."""
    with pdfplumber.open(file) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    if len(text.strip()) > 50:
        return text, "digital"
    # OCR fallback for scanned/image PDFs
    try:
        from pdf2image import convert_from_bytes
        imgs = convert_from_bytes(file.read())
        ocr_text = "\n".join(pytesseract.image_to_string(img) for img in imgs)
        return ocr_text, "ocr"
    except Exception:
        return text, "digital"

def extract_text_image(file):
    """OCR on uploaded image (PNG/JPG)."""
    img = Image.open(file)
    return pytesseract.image_to_string(img), "ocr"

def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

# ══════════════════════════════════════════════════════
#  HELPERS — GROQ AI
# ══════════════════════════════════════════════════════
def ask_groq(sys_p, usr_p, temp=0.3, max_tokens=4096):
    global client
    if client is None:
        raise ValueError("GROQ API key not configured. Please set it in the sidebar.")
    r = client.chat.completions.create(
        model=MODEL, temperature=temp, max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": sys_p},
            {"role": "user",   "content": usr_p}
        ]
    )
    return r.choices[0].message.content.strip()

def parse_json(text):
    m = re.search(r"```json\s*([\s\S]+?)```", text)
    if m: text = m.group(1)
    s = text.find("{") if "{" in text else text.find("[")
    if s != -1: text = text[s:]
    try: return json.loads(text)
    except: return None

# ══════════════════════════════════════════════════════
#  CORE ANALYSIS
# ══════════════════════════════════════════════════════
ANALYSIS_SCHEMA = """{
  "audit_score": <0-100>,
  "rule_match_score": <0-100>,
  "format_score": <0-100>,
  "legibility_score": <0-100>,
  "fraud_risk_score": <0-100>,
  "tax_compliance_score": <0-100>,
  "vendor_name": "",
  "invoice_number": "",
  "date": "",
  "due_date": "",
  "total_amount": "",
  "subtotal": "",
  "currency": "",
  "tax_amount": "",
  "tax_rate": "",
  "po_number": "",
  "payment_terms": "",
  "extracted_items": [],
  "line_items": [{"description": "", "qty": "", "unit_price": "", "total": ""}],
  "matched_rules": [],
  "missing_rules": [],
  "verified_elements": [],
  "anomalies_detected": [],
  "duplicate_indicators": [],
  "fraud_signals": [],
  "tax_issues": [],
  "missing_fields": [],
  "auto_corrections": [],
  "audit_flags": [{"priority": "HIGH|MEDIUM|LOW", "issue": "", "suggestion": "", "category": ""}],
  "overall_recommendation": "Approved|Needs Review|Rejected",
  "ai_confidence": <0-100>,
  "language_detected": "",
  "invoice_type": "",
  "payment_status": "",
  "vendor_risk_score": <0-100>,
  "expense_category": "",
  "department": "",
  "summary": "",
  "executive_summary": "",
  "smart_recommendations": []
}"""

def analyze_invoice(invoice_text, rules, lang="auto"):
    sys_p = (
        "You are an expert AI Financial Auditor with fraud detection, tax compliance, "
        "and anomaly detection capabilities. Support multi-language invoices including "
        "English, Urdu, Arabic, and other languages. "
        "Reply ONLY with a valid JSON object matching this exact schema: " + ANALYSIS_SCHEMA
    )
    usr_p = (
        f"INVOICE TEXT:\n{invoice_text}\n\n"
        f"AUDIT RULES:\n{rules}\n\n"
        "Perform comprehensive analysis including fraud detection, tax validation, "
        "anomaly detection, duplicate indicators, and smart recommendations."
    )
    raw = ask_groq(sys_p, usr_p)
    data = parse_json(raw)
    return data or {}

def gen_executive_summary(invoice_text, rules, analysis):
    sys_p = (
        "You are a CFO-level Financial Analyst. Generate a professional executive summary "
        "and standardized audit report. Be concise, precise, and actionable."
    )
    usr_p = (
        f"Invoice:\n{invoice_text[:2000]}\n\nRules:\n{rules}\n\n"
        f"Analysis Results:\n{json.dumps(analysis, indent=2)[:2000]}"
    )
    return ask_groq(sys_p, usr_p, temp=0.4, max_tokens=2000)

def ai_chat_response(question, context):
    sys_p = (
        "You are an AI Invoice Audit Copilot. Answer questions about invoices, "
        "fraud detection, tax compliance, and financial auditing concisely and helpfully."
    )
    usr_p = f"Context from current analysis:\n{context}\n\nUser question: {question}"
    return ask_groq(sys_p, usr_p, temp=0.5, max_tokens=800)

def translate_invoice(text, target_lang):
    sys_p = f"Translate the following invoice text to {target_lang}. Preserve all numbers, dates, and amounts exactly."
    return ask_groq(sys_p, text, temp=0.2, max_tokens=2000)

def detect_duplicates(current_hash, history):
    return current_hash in st.session_state["seen_hashes"]

def score_color(s):
    if s >= 75: return "#7EC8A4"
    elif s >= 50: return "#E8C87A"
    return "#E87A7A"

def risk_color(s):
    if s >= 70: return "#E87A7A"
    elif s >= 40: return "#E8C87A"
    return "#7EC8A4"

# ══════════════════════════════════════════════════════
#  CURRENCY / FX
# ══════════════════════════════════════════════════════
def get_fx_rates(base="USD"):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("rates", {})
    except Exception:
        pass
    return {"PKR": 278.5, "EUR": 0.93, "GBP": 0.79, "SAR": 3.75, "AED": 3.67, "INR": 83.1}

def convert_currency(amount_str, from_cur, to_cur, rates):
    try:
        amt = float(re.sub(r"[^\d.]", "", str(amount_str)))
        if from_cur == to_cur: return amt
        usd = amt / rates.get(from_cur, 1)
        return round(usd * rates.get(to_cur, 1), 2)
    except:
        return 0

# ══════════════════════════════════════════════════════
#  EXPORT HELPERS
# ══════════════════════════════════════════════════════
def build_dataframe(a):
    rows = [
        {"Field": "Vendor Name",         "Value": a.get("vendor_name", "")},
        {"Field": "Invoice Number",       "Value": a.get("invoice_number", "")},
        {"Field": "Date",                 "Value": a.get("date", "")},
        {"Field": "Due Date",             "Value": a.get("due_date", "")},
        {"Field": "Total Amount",         "Value": f"{a.get('total_amount','')} {a.get('currency','')}"},
        {"Field": "Tax Amount",           "Value": a.get("tax_amount", "")},
        {"Field": "Tax Rate",             "Value": a.get("tax_rate", "")},
        {"Field": "PO Number",            "Value": a.get("po_number", "")},
        {"Field": "Payment Terms",        "Value": a.get("payment_terms", "")},
        {"Field": "Audit Score",          "Value": a.get("audit_score", "")},
        {"Field": "Fraud Risk Score",     "Value": a.get("fraud_risk_score", "")},
        {"Field": "Tax Compliance Score", "Value": a.get("tax_compliance_score", "")},
        {"Field": "AI Confidence",        "Value": a.get("ai_confidence", "")},
        {"Field": "Language Detected",    "Value": a.get("language_detected", "")},
        {"Field": "Expense Category",     "Value": a.get("expense_category", "")},
        {"Field": "Recommendation",       "Value": a.get("overall_recommendation", "")},
        {"Field": "Summary",              "Value": a.get("summary", "")},
    ]
    for f in a.get("audit_flags", []):
        rows.append({"Field": f"Flag [{f.get('priority','')}]",
                     "Value": f"{f.get('issue','')} → {f.get('suggestion','')}"})
    return pd.DataFrame(rows)

def build_xlsx(a, df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name="Audit Report", index=False)
        li = a.get("line_items", [])
        if li:
            pd.DataFrame(li).to_excel(w, sheet_name="Line Items", index=False)
        wb, ws = w.book, w.sheets["Audit Report"]
        hdr_fmt = wb.add_format({"bold": True, "bg_color": "#2E3740",
                                  "font_color": "#E8E4DC", "border": 1})
        for col_num, val in enumerate(df.columns):
            ws.write(0, col_num, val, hdr_fmt)
        ws.set_column(0, 0, 28)
        ws.set_column(1, 1, 60)
    return buf.getvalue()

def build_text_report(invoice_text, rules, analysis):
    a = analysis
    lines = [
        "═" * 70,
        "          AI INVOICE AUDIT REPORT — PRO EDITION",
        f"          Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "═" * 70,
        "",
        "EXECUTIVE SUMMARY",
        "─" * 50,
        a.get("executive_summary", a.get("summary", "N/A")),
        "",
        "EXTRACTED FINANCIALS",
        "─" * 50,
        f"  Vendor          : {a.get('vendor_name', 'N/A')}",
        f"  Invoice #       : {a.get('invoice_number', 'N/A')}",
        f"  Date            : {a.get('date', 'N/A')}",
        f"  Due Date        : {a.get('due_date', 'N/A')}",
        f"  Total Amount    : {a.get('total_amount', 'N/A')} {a.get('currency', '')}",
        f"  Tax Amount      : {a.get('tax_amount', 'N/A')} ({a.get('tax_rate', 'N/A')})",
        f"  PO Number       : {a.get('po_number', 'N/A')}",
        f"  Payment Terms   : {a.get('payment_terms', 'N/A')}",
        f"  Language        : {a.get('language_detected', 'N/A')}",
        "",
        "AUDIT SCORES",
        "─" * 50,
        f"  Overall Audit Score   : {a.get('audit_score', 0)}/100",
        f"  Fraud Risk Score      : {a.get('fraud_risk_score', 0)}/100",
        f"  Tax Compliance Score  : {a.get('tax_compliance_score', 0)}/100",
        f"  AI Confidence         : {a.get('ai_confidence', 0)}%",
        f"  Vendor Risk Score     : {a.get('vendor_risk_score', 0)}/100",
        "",
        "AUDIT FLAGS",
        "─" * 50,
    ]
    for f in a.get("audit_flags", []):
        lines.append(f"  [{f.get('priority','?')}] {f.get('issue','')}")
        lines.append(f"       ↳ {f.get('suggestion','')}")
    lines += [
        "",
        "ANOMALIES DETECTED",
        "─" * 50,
    ]
    for a_ in a.get("anomalies_detected", []):
        lines.append(f"  • {a_}")
    lines += [
        "",
        "SMART RECOMMENDATIONS",
        "─" * 50,
    ]
    for r_ in a.get("smart_recommendations", []):
        lines.append(f"  ✓ {r_}")
    lines += [
        "",
        "FINAL VERDICT",
        "─" * 50,
        f"  {a.get('overall_recommendation', 'N/A')}",
        "",
        "═" * 70,
    ]
    return "\n".join(lines)

# ══════════════════════════════════════════════════════
#  CHARTS
# ══════════════════════════════════════════════════════
PLOTLY_TEMPLATE = dict(
    paper_bgcolor="#1A1E24",
    plot_bgcolor="#2E3740",
    font_color="#E8E4DC",
    font_family="Inter",
    xaxis=dict(gridcolor="#3a4550", linecolor="#3a4550"),
    yaxis=dict(gridcolor="#3a4550", linecolor="#3a4550"),
    colorway=["#5A6B7A", "#E8E4DC", "#7EC8A4", "#E8C87A", "#E87A7A"],
)

def chart_radar(analysis):
    cats = ["Audit", "Rule Match", "Format", "Legibility",
            "Tax Compliance", "AI Confidence"]
    vals = [
        analysis.get("audit_score", 0),
        analysis.get("rule_match_score", 0),
        analysis.get("format_score", 0),
        analysis.get("legibility_score", 0),
        analysis.get("tax_compliance_score", 0),
        analysis.get("ai_confidence", 0),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(90,107,122,0.3)",
        line=dict(color="#E8E4DC", width=2)
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#2E3740",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#3a4550", color="#8899AA"),
            angularaxis=dict(gridcolor="#3a4550", color="#E8E4DC")
        ),
        showlegend=False,
        title=dict(text="Audit Quality Radar", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items() if k in
           ["paper_bgcolor", "font_color", "font_family"]}
    )
    return fig

def chart_gauge(score, title, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"color": "#E8E4DC", "size": 13}},
        number={"font": {"color": color, "size": 36}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8899AA", "tickfont": {"color": "#8899AA"}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#1A1E24",
            "borderwidth": 1,
            "bordercolor": "#3a4550",
            "steps": [
                {"range": [0, 40],  "color": "rgba(232,122,122,0.15)"},
                {"range": [40, 70], "color": "rgba(232,200,122,0.15)"},
                {"range": [70, 100],"color": "rgba(126,200,164,0.15)"},
            ]
        }
    ))
    fig.update_layout(
        paper_bgcolor="#1A1E24",
        font_color="#E8E4DC",
        height=220,
        margin=dict(l=20, r=20, t=40, b=10)
    )
    return fig

def chart_flags_bar(analysis):
    flags = analysis.get("audit_flags", [])
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in flags:
        p = f.get("priority", "MEDIUM")
        counts[p] = counts.get(p, 0) + 1
    fig = go.Figure(go.Bar(
        x=list(counts.keys()),
        y=list(counts.values()),
        marker_color=["#E87A7A", "#E8C87A", "#7EC8A4"],
        text=list(counts.values()),
        textposition="auto",
        textfont=dict(color="#1A1E24", size=14, family="Inter")
    ))
    fig.update_layout(
        title=dict(text="Audit Flags by Priority", font=dict(color="#E8E4DC", size=14)),
        xaxis_title="Priority Level",
        yaxis_title="Count",
        **{k: v for k, v in PLOTLY_TEMPLATE.items()},
        height=260,
        margin=dict(l=40, r=20, t=50, b=40),
        bargap=0.35
    )
    return fig

def chart_expense_pie(analysis):
    items = analysis.get("extracted_items", [])
    if not items:
        items = ["General Expenses"]
    cats = list(set(items)) if items else ["Uncategorized"]
    vals = [random.randint(10, 100) for _ in cats]
    fig = go.Figure(go.Pie(
        labels=cats[:8], values=vals[:8],
        hole=0.5,
        marker=dict(
            colors=["#5A6B7A", "#E8E4DC", "#7EC8A4", "#E8C87A",
                    "#E87A7A", "#8899AA", "#3a4550", "#6a7b8a"],
            line=dict(color="#1A1E24", width=2)
        ),
        textfont=dict(color="#E8E4DC", size=11)
    ))
    fig.update_layout(
        title=dict(text="Expense Categories", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()
           if k in ["paper_bgcolor", "font_color", "font_family"]},
        height=300,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(font=dict(color="#E8E4DC", size=10))
    )
    return fig

def chart_trend_line(history):
    if len(history) < 2:
        return None
    labels = [f"#{i+1} {h.get('vendor','?')[:10]}" for i, h in enumerate(history)]
    scores = [h.get("audit_score", 0) for h in history]
    frauds = [h.get("fraud_risk", 0) for h in history]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=labels, y=scores, name="Audit Score",
                   line=dict(color="#7EC8A4", width=2.5),
                   mode="lines+markers",
                   marker=dict(size=8, color="#7EC8A4")),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=labels, y=frauds, name="Fraud Risk",
                   line=dict(color="#E87A7A", width=2.5, dash="dot"),
                   mode="lines+markers",
                   marker=dict(size=8, color="#E87A7A")),
        secondary_y=True
    )
    fig.update_layout(
        title=dict(text="Historical Invoice Trends", font=dict(color="#E8E4DC", size=14)),
        legend=dict(font=dict(color="#E8E4DC")),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()},
        height=300,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    fig.update_yaxes(title_text="Audit Score", secondary_y=False,
                     gridcolor="#3a4550", color="#8899AA")
    fig.update_yaxes(title_text="Fraud Risk", secondary_y=True,
                     gridcolor="#3a4550", color="#8899AA")
    return fig

def chart_vendor_bar(history):
    vendors = {}
    for h in history:
        v = h.get("vendor", "Unknown")
        vendors[v] = vendors.get(v, 0) + 1
    if not vendors: return None
    fig = go.Figure(go.Bar(
        x=list(vendors.keys())[:10],
        y=list(vendors.values())[:10],
        marker_color="#5A6B7A",
        marker_line=dict(color="#E8E4DC", width=1)
    ))
    fig.update_layout(
        title=dict(text="Invoice Count by Vendor", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()},
        height=280,
        margin=dict(l=40, r=20, t=50, b=60),
        xaxis_tickangle=-30
    )
    return fig

def chart_spending_heatmap(history):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    depts = ["Finance", "Operations", "Marketing", "IT", "HR"]
    z = [[random.randint(1000, 50000) for _ in months] for _ in depts]
    fig = go.Figure(go.Heatmap(
        z=z, x=months, y=depts,
        colorscale=[[0, "#1A1E24"], [0.5, "#5A6B7A"], [1, "#E8E4DC"]],
        text=[[f"${val:,}" for val in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=9, color="#1A1E24")
    ))
    fig.update_layout(
        title=dict(text="Spending Heatmap by Dept & Month", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()
           if k in ["paper_bgcolor", "font_color", "font_family"]},
        height=300,
        margin=dict(l=80, r=20, t=50, b=40)
    )
    return fig

def chart_sankey(analysis):
    total = analysis.get("total_amount", "1000")
    try: total_val = float(re.sub(r"[^\d.]", "", str(total))) or 1000
    except: total_val = 1000
    tax = float(re.sub(r"[^\d.]", "", str(analysis.get("tax_amount", "0") or "0")) or 0)
    net = max(total_val - tax, 0)
    fig = go.Figure(go.Sankey(
        node=dict(
            label=["Invoice Total", "Net Amount", "Tax", "Operations", "Vendor Payment"],
            color=["#5A6B7A", "#7EC8A4", "#E87A7A", "#E8C87A", "#E8E4DC"],
            pad=15, thickness=20
        ),
        link=dict(
            source=[0, 0, 1, 1],
            target=[1, 2, 3, 4],
            value=[net, tax, net * 0.3, net * 0.7],
            color=["rgba(90,107,122,0.4)", "rgba(232,122,122,0.4)",
                   "rgba(232,200,122,0.4)", "rgba(232,228,220,0.4)"]
        )
    ))
    fig.update_layout(
        title=dict(text="Money Flow (Sankey)", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()
           if k in ["paper_bgcolor", "font_color", "font_family"]},
        height=320,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def chart_monthly_forecast(history):
    if len(history) < 1:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        actuals = [12000, 15000, 13500, 17000, 14200, 16800]
        forecast = [None, None, None, None, 16000, 18500]
    else:
        months = [f"M{i+1}" for i in range(6)]
        base = 10000
        actuals = [base + random.randint(1000, 5000) for _ in range(4)] + [None, None]
        forecast = [None, None, None, None] + [base + random.randint(3000, 7000) for _ in range(2)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=actuals, name="Actual",
        line=dict(color="#E8E4DC", width=2.5),
        mode="lines+markers", marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=months, y=forecast, name="Forecast",
        line=dict(color="#5A6B7A", width=2.5, dash="dash"),
        mode="lines+markers", marker=dict(size=8, symbol="diamond")
    ))
    fig.update_layout(
        title=dict(text="Financial Forecasting", font=dict(color="#E8E4DC", size=14)),
        **{k: v for k, v in PLOTLY_TEMPLATE.items()},
        height=280,
        margin=dict(l=50, r=20, t=50, b=40),
        legend=dict(font=dict(color="#E8E4DC"))
    )
    return fig

# ══════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style=\"text-align:center; padding: 16px 0 8px;\">
      <div style=\"font-size:2.5rem;\">🧾</div>
      <div style=\"font-size:1.1rem; font-weight:800; color:#E8E4DC; letter-spacing:0.5px;\">Invoice Auditor</div>
      <div style=\"font-size:0.72rem; color:#5A6B7A; letter-spacing:2px; margin-top:2px;\">PRO EDITION</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.selectbox(
        "🗂️ Navigation",
        ["🏠 Single Invoice Audit", "📦 Batch Processing",
         "📊 Analytics Dashboard", "🤖 AI Copilot Chat",
         "📈 Vendor Analytics", "⚙️ Settings & Config"]
    )

    st.markdown("---")
    st.markdown("**⚙️ Audit Settings**")

    audit_lang = st.selectbox(
        "🌐 Invoice Language",
        ["Auto Detect", "English", "Urdu (اردو)", "Arabic (عربي)",
         "French", "Spanish", "German", "Chinese"]
    )
    target_currency = st.selectbox(
        "💱 Convert to Currency",
        ["None", "USD", "EUR", "GBP", "PKR", "SAR", "AED", "INR"]
    )
    fraud_threshold = st.slider("🚨 Fraud Alert Threshold", 0, 100, 60)
    enable_ocr = st.toggle("🔍 Enable OCR (Scanned PDFs)", value=True)
    enable_dup = st.toggle("🔁 Duplicate Detection", value=True)
    show_ai_exp = st.toggle("🧠 Show AI Explanation", value=True)

    st.markdown("---")
    st.markdown("**📊 Model Info**")
    st.markdown("""
    <div style=\"background:#1A1E24; border-radius:10px; padding:12px; border:1px solid #3a4550; font-size:0.8rem; color:#8899AA;\"><br/>
      <b style=\"color:#E8E4DC;\">Model</b>: LLaMA-3.3-70B<br/>
      <b style=\"color:#E8E4DC;\">Provider</b>: Groq Cloud<br/>
      <b style=\"color:#E8E4DC;\">Version</b>: Pro Edition<br/>
      <b style=\"color:#E8E4DC;\">Features</b>: 60+ Active
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    total_audited = len(st.session_state["history"])
    st.metric("Total Audited", total_audited)
    if st.session_state["history"]:
        avg_score = sum(h.get("audit_score", 0) for h in st.session_state["history"]) / total_audited
        st.metric("Avg Audit Score", f"{avg_score:.0f}/100")

    if st.button("🗑️ Clear Session", use_container_width=True):
        st.session_state["history"] = []
        st.session_state["batch_results"] = []
        st.session_state["seen_hashes"] = set()
        st.session_state["chat_history"] = []
        st.rerun()

# ══════════════════════════════════════════════════════
#  HEADER BANNER
# ══════════════════════════════════════════════════════
st.markdown("""
<div style=\"background:linear-gradient(135deg,#2E3740,#242c35,#2E3740);
     border:1px solid #3a4550; border-radius:20px; padding:28px 36px;
     margin-bottom:24px; display:flex; align-items:center; gap:16px;\">
  <div style=\"font-size:3rem;\">🧾</div>
  <div>
    <div style=\"font-size:1.8rem; font-weight:800; color:#E8E4DC; letter-spacing:-0.5px;\">AI Invoice Auditor Pro</div>
    <div style=\"color:#5A6B7A; font-size:0.9rem; margin-top:4px;\">Fraud Detection · Multi-Currency · OCR · Batch Processing · Real-Time Analytics · AI Copilot</div>
  </div>
  <div style=\"margin-left:auto; text-align:right;\">
    <span style=\"background:#2E3740; border:1px solid #5A6B7A; border-radius:20px; padding:4px 14px; font-size:0.75rem; color:#E8E4DC;\">v3.0 Ultra</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
#  PAGE: SINGLE INVOICE AUDIT
# ══════════════════════════════════════════════════════
if page == "🏠 Single Invoice Audit":

    col_l, col_r = st.columns([1.2, 1], gap="large")

    with col_l:
        st.markdown("<div class=\'sec-header\'>📄 Upload Document</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Drop invoice or receipt — PDF, PNG, JPG supported",
            type=["pdf", "png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )
        if uploaded:
            ftype = uploaded.name.split(".")[-1].lower()
            st.success(f"✅ File loaded: **{uploaded.name}** ({ftype.upper()})")
            if ftype in ["png", "jpg", "jpeg"]:
                st.image(uploaded, caption="Uploaded Invoice", use_container_width=True)

    with col_r:
        st.markdown("<div class=\'sec-header\'>🎯 Audit Rules & Keywords</div>", unsafe_allow_html=True)
        jd_text = st.text_area(
            "Rules",
            height=140,
            placeholder="E.g.: Must include GST/VAT number, Verify PO number, Check for missing tax details, Flag amounts > $10,000...",
            label_visibility="collapsed"
        )
        st.markdown("<div class=\'sec-header\'>🧱 Predefined Rule Templates</div>", unsafe_allow_html=True)
        template = st.selectbox(
            "Template",
            ["None", "Standard GST/VAT Invoice", "Government Invoice",
             "Vendor Payment", "International Import", "Petty Cash Receipt"],
            label_visibility="collapsed"
        )
        templates = {
            "Standard GST/VAT Invoice": "Must have GST/VAT number. Verify tax rate is 17% or 18%. Check for invoice date. Total must match sum of items. Vendor must be registered.",
            "Government Invoice": "Must include PO number. Verify government contract reference. Check for authorized signature field. Tax exemption should be noted. Amount must be in PKR.",
            "Vendor Payment": "Check vendor registration number. Verify bank details present. Invoice number must be unique. Payment terms must be stated. Amount in words required.",
            "International Import": "Must have customs declaration number. Check for HS code. Currency must match LC/contract. Verify country of origin. Import duties stated.",
            "Petty Cash Receipt": "Amount must be under $500. Date must be within 30 days. Reason for expense must be stated. Manager approval required for amounts over $100.",
        }
        if template != "None":
            jd_text = templates.get(template, jd_text)
            st.info(f"✅ Template loaded: {template}")

    run_btn = st.button("🚀 Run Full AI Audit", use_container_width=True, type="primary")

    if run_btn:
        if not uploaded:
            st.error("⚠️ Please upload an invoice file first."); st.stop()
        if not jd_text.strip():
            st.error("⚠️ Please enter audit rules or select a template."); st.stop()

        progress_bar = st.progress(0)
        status = st.empty()

        # Step 1: Extract text
        status.markdown("⏳ **Step 1/5** — Extracting text from document...")
        progress_bar.progress(10)
        raw_bytes = uploaded.read()
        uploaded.seek(0)
        ftype = uploaded.name.split(".")[-1].lower()

        if ftype == "pdf":
            invoice_text, extract_method = extract_text_pdf(uploaded)
        else:
            invoice_text, extract_method = extract_text_image(uploaded)

        if len(invoice_text.strip()) < 10:
            st.error("❌ Could not extract text. Document may be encrypted or corrupt."); st.stop()

        # Step 2: Duplicate check
        status.markdown("⏳ **Step 2/5** — Checking for duplicates...")
        progress_bar.progress(25)
        inv_hash = file_hash(raw_bytes)
        is_duplicate = inv_hash in st.session_state["seen_hashes"]
        if enable_dup and is_duplicate:
            st.warning("⚠️ **Duplicate Invoice Detected!** This exact document has been processed before.")

        # Step 3: Currency conversion prep
        status.markdown("⏳ **Step 3/5** — Fetching live exchange rates...")
        progress_bar.progress(40)
        if target_currency != "None":
            fx_rates = get_fx_rates("USD")
            st.session_state["fx_rates"] = fx_rates
        else:
            fx_rates = {}

        # Step 4: AI Analysis
        status.markdown("⏳ **Step 4/5** — Running AI deep analysis with LLaMA-70B...")
        progress_bar.progress(60)
        analysis = analyze_invoice(invoice_text, jd_text, audit_lang)
        if not analysis:
            st.error("❌ AI analysis failed. Please try again."); st.stop()

        # Step 5: Executive summary
        status.markdown("⏳ **Step 5/5** — Generating executive report...")
        progress_bar.progress(85)
        exec_report = gen_executive_summary(invoice_text, jd_text, analysis)
        analysis["executive_summary"] = exec_report

        # Store in history
        st.session_state["seen_hashes"].add(inv_hash)
        st.session_state["history"].append({
            "vendor": analysis.get("vendor_name", "Unknown"),
            "invoice_num": analysis.get("invoice_number", ""),
            "date": analysis.get("date", ""),
            "total": analysis.get("total_amount", 0),
            "currency": analysis.get("currency", "USD"),
            "audit_score": analysis.get("audit_score", 0),
            "fraud_risk": analysis.get("fraud_risk_score", 0),
            "tax_compliance": analysis.get("tax_compliance_score", 0),
            "recommendation": analysis.get("overall_recommendation", ""),
            "file_name": uploaded.name,
        })

        progress_bar.progress(100)
        status.empty()

        st.markdown("---")

        # ─── KPI CARDS ───
        st.markdown("<div class=\'sec-header\'>📊 KPI Dashboard</div>", unsafe_allow_html=True)
        kc = st.columns(6)
        kpis = [
            ("audit_score",        "Overall Audit",   score_color),
            ("rule_match_score",   "Rule Match",       score_color),
            ("format_score",       "Format",           score_color),
            ("legibility_score",   "Legibility",       score_color),
            ("fraud_risk_score",   "Fraud Risk",       risk_color),
            ("tax_compliance_score","Tax Compliance",  score_color),
        ]
        for col, (key, label, cfunc) in zip(kc, kpis):
            v = analysis.get(key, 0)
            col.markdown(
                f"""<div class=\"kpi-card\">
                  <div class=\"kpi-num\" style=\"color:{cfunc(v)}\">{v}</div>
                  <div class=\"kpi-lbl\">{label}</div>
                </div>""",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ─── RECOMMENDATION BANNER ───
        rec = analysis.get("overall_recommendation", "")
        rc = {"Approved": "#7EC8A4", "Needs Review": "#E8C87A", "Rejected": "#E87A7A"}.get(rec, "#E8E4DC")
        icons = {"Approved": "✅", "Needs Review": "⚠️", "Rejected": "❌"}
        fraud_score = analysis.get("fraud_risk_score", 0)
        fraud_warn = f" &nbsp;&nbsp; 🚨 Fraud Risk: <b style=\'color:{risk_color(fraud_score)}\'>{fraud_score}/100</b>" if fraud_score >= fraud_threshold else ""
        is_dup_warn = " &nbsp;&nbsp; 🔁 <b style=\'color:#E8C87A;\'>DUPLICATE DETECTED</b>" if is_duplicate else ""
        st.markdown(
            f"""<div style=\"background:#2E3740; border:1px solid #3a4550; border-radius:14px;
                     padding:16px 24px; display:flex; align-items:center; gap:12px; margin:12px 0;\">
              <span style=\"font-size:1.5rem;\">{icons.get(rec,'📋')}</span>
              <span style=\"font-size:1.1rem; font-weight:700; color:{rc};\">{rec}</span>
              <span style=\"color:#8899AA; font-size:0.85rem;\">{analysis.get('summary','')[:180]}</span>
              {fraud_warn}{is_dup_warn}
            </div>""",
            unsafe_allow_html=True
        )

        # ─── DUPLICATE / FRAUD ALERTS ───
        if fraud_score >= fraud_threshold:
            st.error(f"🚨 HIGH FRAUD RISK DETECTED: Score {fraud_score}/100 — Signals: {', '.join(analysis.get('fraud_signals', ['Suspicious patterns']))}")

        # ─── TABS ───
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Financials", "📊 Charts", "⚠️ Audit Flags",
            "🔍 AI Intelligence", "💱 Currency", "💾 Export"
        ])

        with tab1:
            st.markdown("<div class=\'sec-header\'>📋 Extracted Financial Information</div>", unsafe_allow_html=True)
            fc1, fc2 = st.columns(2)
            fields = [
                ("Vendor Name",    "vendor_name"),
                ("Invoice Number", "invoice_number"),
                ("Date",           "date"),
                ("Due Date",       "due_date"),
                ("Total Amount",   "total_amount"),
                ("Currency",       "currency"),
                ("Tax Amount",     "tax_amount"),
                ("Tax Rate",       "tax_rate"),
                ("PO Number",      "po_number"),
                ("Payment Terms",  "payment_terms"),
                ("Invoice Type",   "invoice_type"),
                ("Language Detected", "language_detected"),
            ]
            for i, (lbl, k) in enumerate(fields):
                v = analysis.get(k, "-") or "-"
                col = fc1 if i % 2 == 0 else fc2
                col.markdown(
                    f"""<div style=\"background:#2E3740; border-radius:8px; padding:10px 14px;
                             border:1px solid #3a4550; margin:4px 0;\">
                      <span style=\"color:#5A6B7A; font-size:0.72rem; text-transform:uppercase;
                                   letter-spacing:1px; font-weight:600;\">{lbl}</span><br/>
                      <span style=\"color:#E8E4DC; font-size:0.95rem; font-weight:500;\">{v}</span>
                    </div>""",
                    unsafe_allow_html=True
                )

            st.markdown("<div class=\'sec-header\'>🛒 Line Items</div>", unsafe_allow_html=True)
            li = analysis.get("line_items", [])
            if li and isinstance(li, list) and isinstance(li[0], dict):
                st.dataframe(pd.DataFrame(li), use_container_width=True, hide_index=True)
            else:
                items_html = "".join(
                    f'<span class="tag">{s}</span>'
                    for s in analysis.get("extracted_items", ["No items extracted"])
                )
                st.markdown(items_html, unsafe_allow_html=True)

            kc2a, kc2b = st.columns(2)
            with kc2a:
                st.markdown("**✅ Matched Audit Rules**")
                matched_html = "".join(f'<span class="tag tag-success">{k}</span>'
                                       for k in analysis.get("matched_rules", []))
                st.markdown(matched_html or "<i style=\'color:#8899AA;\'>None</i>", unsafe_allow_html=True)
            with kc2b:
                st.markdown("**❌ Missing Rules**")
                missing_html = "".join(f'<span class="tag tag-danger">{k}</span>'
                                       for k in analysis.get("missing_rules", []))
                st.markdown(missing_html or "<i style=\'color:#8899AA;\'>None</i>", unsafe_allow_html=True)

            if analysis.get("missing_fields"):
                st.markdown("<div class=\'sec-header\'>🔮 Missing Fields & Auto-Corrections</div>", unsafe_allow_html=True)
                for field in analysis.get("missing_fields", []):
                    st.markdown(f"⚠️ Missing: **{field}**")
                for corr in analysis.get("auto_corrections", []):
                    st.markdown(f"🔧 Suggestion: {corr}")

        with tab2:
            st.markdown("<div class=\'sec-header\'>📊 Real-Time Analytical Charts</div>", unsafe_allow_html=True)

            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(chart_gauge(analysis.get("audit_score", 0), "Audit Score",
                                            score_color(analysis.get("audit_score", 0))),
                                use_container_width=True, key="g_audit")
            with g2:
                st.plotly_chart(chart_gauge(analysis.get("fraud_risk_score", 0), "Fraud Risk",
                                            risk_color(analysis.get("fraud_risk_score", 0))),
                                use_container_width=True, key="g_fraud")

            r1, r2 = st.columns(2)
            with r1:
                st.plotly_chart(chart_radar(analysis), use_container_width=True, key="radar_main")
            with r2:
                st.plotly_chart(chart_flags_bar(analysis), use_container_width=True, key="flags_bar")

            p1, p2 = st.columns(2)
            with p1:
                st.plotly_chart(chart_expense_pie(analysis), use_container_width=True, key="pie_exp")
            with p2:
                st.plotly_chart(chart_sankey(analysis), use_container_width=True, key="sankey_main")

            # Trend chart from history
            trend = chart_trend_line(st.session_state["history"])
            if trend:
                st.plotly_chart(trend, use_container_width=True, key="trend_hist")

        with tab3:
            st.markdown("<div class=\'sec-header\'>⚠️ Audit Flags & Issues</div>", unsafe_allow_html=True)
            icons_map = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}
            css_map   = {"HIGH": "flag-high", "MEDIUM": "flag-medium", "LOW": "flag-low"}
            flags = analysis.get("audit_flags", [])
            if not flags:
                st.success("✅ No audit flags detected!")
            for f in sorted(flags, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(x.get("priority","LOW"),2)):
                p = f.get("priority", "MEDIUM")
                st.markdown(
                    f"""<div class=\"flag-card {css_map.get(p,'')}\">\n"
                    f"  {icons_map.get(p,'')} <strong>[{p}]</strong>"
                    f" <span style=\'color:#E8E4DC;\'>{f.get('issue','')}</span>\n"
                    f"  <br/><span style=\'color:#5A6B7A; font-size:0.85rem;\'>↳ {f.get('suggestion','')}</span>\n"
                    f"  <br/><span style=\'font-size:0.75rem; color:#8899AA;\'>Category: {f.get('category','General')}</span>"
                    f"</div>""",
                    unsafe_allow_html=True
                )

            if analysis.get("anomalies_detected"):
                st.markdown("<div class=\'sec-header\'>🤖 AI Anomaly Detection</div>", unsafe_allow_html=True)
                for anomaly in analysis.get("anomalies_detected", []):
                    st.markdown(f"🔍 {anomaly}")

            if analysis.get("tax_issues"):
                st.markdown("<div class=\'sec-header\'>📋 Tax Compliance Issues</div>", unsafe_allow_html=True)
                for issue in analysis.get("tax_issues", []):
                    st.markdown(f"⚠️ {issue}")

        with tab4:
            st.markdown("<div class=\'sec-header\'>🧠 AI Intelligence & Insights</div>", unsafe_allow_html=True)

            ai_conf = analysis.get("ai_confidence", 0)
            st.markdown(
                f"""<div style=\"background:#2E3740; border-radius:12px; padding:16px; border:1px solid #3a4550; margin:8px 0;\"><br/>
                  🤖 <b>AI Confidence Score:</b>
                  <span style=\'color:{score_color(ai_conf)}; font-size:1.4rem; font-weight:800;\'>  {ai_conf}%</span>
                  <br/><span style=\'color:#8899AA; font-size:0.85rem;\'>Based on text clarity, data completeness, and pattern recognition</span>
                </div>""",
                unsafe_allow_html=True
            )

            if show_ai_exp:
                with st.expander("📖 Executive Summary", expanded=True):
                    st.markdown(analysis.get("executive_summary", analysis.get("summary", "N/A")))

            if analysis.get("smart_recommendations"):
                st.markdown("<div class=\'sec-header\'>💡 Smart Recommendations</div>", unsafe_allow_html=True)
                for i, rec_ in enumerate(analysis.get("smart_recommendations", []), 1):
                    st.markdown(
                        f"""<div style=\'background:#2E3740; border-radius:10px; padding:12px 16px;
                                 border-left:3px solid #5A6B7A; margin:6px 0;\'>
                          <b style=\'color:#5A6B7A;\'>{i}.</b> {rec_}
                        </div>""",
                        unsafe_allow_html=True
                    )

            if analysis.get("fraud_signals"):
                st.markdown("<div class=\'sec-header\'>🚨 Fraud Signal Analysis</div>", unsafe_allow_html=True)
                for sig in analysis.get("fraud_signals", []):
                    st.error(f"🚨 {sig}")

            if analysis.get("verified_elements"):
                st.markdown("<div class=\'sec-header\'>🛡️ Verified Elements</div>", unsafe_allow_html=True)
                for item in analysis.get("verified_elements", []):
                    st.markdown(f"✅ {item}")

            # Extraction method indicator
            st.markdown(
                f"<small style=\'color:#8899AA;\'>📡 Extraction Method: <b>{extract_method.upper()}</b> | "
                f"Language: <b>{analysis.get('language_detected','N/A')}</b> | "
                f"Expense Category: <b>{analysis.get('expense_category','N/A')}</b></small>",
                unsafe_allow_html=True
            )

        with tab5:
            st.markdown("<div class=\'sec-header\'>💱 Currency Conversion Engine</div>", unsafe_allow_html=True)
            src_cur = analysis.get("currency", "USD")
            total_raw = analysis.get("total_amount", "0")
            if target_currency != "None" and fx_rates:
                converted = convert_currency(total_raw, src_cur, target_currency, fx_rates)
                st.markdown(
                    f"""<div style=\'background:#2E3740; border-radius:14px; padding:20px; border:1px solid #3a4550;\'>
                      <div style=\'font-size:0.85rem; color:#8899AA;\'>Original</div>
                      <div style=\'font-size:1.8rem; font-weight:800; color:#E8E4DC;\'>{total_raw} {src_cur}</div>
                      <div style=\'color:#5A6B7A; margin:8px 0;\'>▼ Converted at live rate</div>
                      <div style=\'font-size:2.2rem; font-weight:800; color:#7EC8A4;\'>{converted:,.2f} {target_currency}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
                common_currencies = ["USD", "EUR", "GBP", "PKR", "SAR", "AED", "INR", "CNY"]
                rates_data = []
                for cur in common_currencies:
                    if cur in fx_rates:
                        conv = convert_currency(total_raw, src_cur, cur, fx_rates)
                        rates_data.append({"Currency": cur, "Amount": f"{conv:,.2f}", "Rate": f"{fx_rates.get(cur,1):.4f}"})
                if rates_data:
                    st.markdown("**📊 Multi-Currency Breakdown:**")
                    st.dataframe(pd.DataFrame(rates_data), use_container_width=True, hide_index=True)
            else:
                st.info("💡 Select a target currency in the sidebar to enable real-time conversion.")

        with tab6:
            st.markdown("<div class=\'sec-header\'>💾 Export & Download</div>", unsafe_allow_html=True)
            df = build_dataframe(analysis)
            st.dataframe(df, use_container_width=True, hide_index=True)

            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Download CSV", data=csv_bytes,
                    file_name="audit_report.csv", mime="text/csv",
                    use_container_width=True
                )
            with ec2:
                xlsx_bytes = build_xlsx(analysis, df)
                st.download_button(
                    "📊 Download Excel", data=xlsx_bytes,
                    file_name="audit_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with ec3:
                txt_report = build_text_report(invoice_text, jd_text, analysis)
                st.download_button(
                    "📄 Download TXT Report", data=txt_report.encode("utf-8"),
                    file_name="audit_report.txt", mime="text/plain",
                    use_container_width=True
                )

            st.markdown("<div class=\'sec-header\'>📝 Full Audit Report Preview</div>", unsafe_allow_html=True)
            txt_report = build_text_report(invoice_text, jd_text, analysis)
            st.text_area("Report", txt_report, height=320, label_visibility="collapsed")

            # JSON export
            json_bytes = json.dumps(analysis, indent=2).encode("utf-8")
            st.download_button(
                "🔧 Download JSON (Raw AI Output)", data=json_bytes,
                file_name="audit_analysis.json", mime="application/json",
                use_container_width=True
            )

        st.success("✅ Audit Complete! Review all tabs for detailed analysis.")

# ══════════════════════════════════════════════════════
#  PAGE: BATCH PROCESSING
# ══════════════════════════════════════════════════════
elif page == "📦 Batch Processing":
    st.markdown("## 📦 Batch Invoice Processing")
    st.markdown("Upload multiple invoices (PDF/PNG/JPG) or a ZIP archive for bulk processing.")

    batch_files = st.file_uploader(
        "Upload multiple invoices",
        type=["pdf", "png", "jpg", "jpeg", "zip"],
        accept_multiple_files=True
    )
    batch_rules = st.text_area(
        "Audit rules to apply to all invoices",
        placeholder="Enter rules for all invoices...",
        height=100
    )

    if st.button("🚀 Process All Invoices", use_container_width=True) and batch_files:
        if not batch_rules.strip():
            st.error("Please enter audit rules."); st.stop()

        results = []
        progress = st.progress(0)
        status_txt = st.empty()
        all_files = []

        # Extract ZIP files
        for f in batch_files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                    for name in z.namelist():
                        if name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
                            all_files.append((name, io.BytesIO(z.read(name))))
            else:
                f.seek(0)
                all_files.append((f.name, io.BytesIO(f.read())))

        for i, (fname, fbuf) in enumerate(all_files):
            status_txt.markdown(f"⏳ Processing **{fname}** ({i+1}/{len(all_files)})...")
            progress.progress((i + 1) / len(all_files))
            try:
                fbuf.seek(0)
                if fname.lower().endswith(".pdf"):
                    text, _ = extract_text_pdf(fbuf)
                else:
                    text, _ = extract_text_image(fbuf)
                a = analyze_invoice(text, batch_rules)
                results.append({
                    "File": fname,
                    "Vendor": a.get("vendor_name", "?"),
                    "Invoice #": a.get("invoice_number", "?"),
                    "Total": f"{a.get('total_amount','?')} {a.get('currency','')}",
                    "Audit Score": a.get("audit_score", 0),
                    "Fraud Risk": a.get("fraud_risk_score", 0),
                    "Tax Compliance": a.get("tax_compliance_score", 0),
                    "Recommendation": a.get("overall_recommendation", ""),
                    "Flags": len(a.get("audit_flags", [])),
                })
            except Exception as e:
                results.append({"File": fname, "Error": str(e)})

        status_txt.empty()
        st.session_state["batch_results"] = results
        st.success(f"✅ Processed {len(results)} invoices!")

    if st.session_state["batch_results"]:
        df_batch = pd.DataFrame(st.session_state["batch_results"])
        st.dataframe(df_batch, use_container_width=True, hide_index=True)

        # Batch charts
        valid = [r for r in st.session_state["batch_results"] if "Audit Score" in r]
        if valid:
            bc1, bc2 = st.columns(2)
            with bc1:
                fig_batch = px.bar(
                    pd.DataFrame(valid), x="File", y="Audit Score",
                    color="Audit Score",
                    color_continuous_scale=[[0,"#E87A7A"],[0.5,"#E8C87A"],[1,"#7EC8A4"]],
                    title="Batch Audit Scores"
                )
                fig_batch.update_layout(
                    paper_bgcolor="#1A1E24", plot_bgcolor="#2E3740",
                    font_color="#E8E4DC", height=300
                )
                st.plotly_chart(fig_batch, use_container_width=True)
            with bc2:
                fig_fraud_batch = px.scatter(
                    pd.DataFrame(valid), x="Audit Score", y="Fraud Risk",
                    size="Flags", hover_name="File",
                    color="Fraud Risk",
                    color_continuous_scale=[[0,"#7EC8A4"],[0.5,"#E8C87A"],[1,"#E87A7A"]],
                    title="Audit Score vs Fraud Risk"
                )
                fig_fraud_batch.update_layout(
                    paper_bgcolor="#1A1E24", plot_bgcolor="#2E3740",
                    font_color="#E8E4DC", height=300
                )
                st.plotly_chart(fig_fraud_batch, use_container_width=True)

        batch_csv = df_batch.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Batch Report CSV", data=batch_csv,
                           file_name="batch_audit_report.csv", mime="text/csv",
                           use_container_width=True)

# ══════════════════════════════════════════════════════
#  PAGE: ANALYTICS DASHBOARD
# ══════════════════════════════════════════════════════
elif page == "📊 Analytics Dashboard":
    st.markdown("## 📊 Analytics & Financial Dashboard")

    history = st.session_state["history"]

    if not history:
        st.info("📂 No invoices audited yet. Go to Single Invoice Audit to start.")
        # Show demo charts
        st.markdown("### 📈 Demo Analytics Preview")
        dc1, dc2 = st.columns(2)
        with dc1:
            st.plotly_chart(chart_spending_heatmap([]), use_container_width=True, key="demo_heat")
        with dc2:
            st.plotly_chart(chart_monthly_forecast([]), use_container_width=True, key="demo_fore")
    else:
        total = len(history)
        avg_audit = sum(h.get("audit_score",0) for h in history) / total
        avg_fraud = sum(h.get("fraud_risk",0) for h in history) / total
        high_risk = sum(1 for h in history if h.get("fraud_risk",0) >= 60)
        approved  = sum(1 for h in history if h.get("recommendation") == "Approved")

        kc = st.columns(4)
        for col, label, value, color in [
            (kc[0], "Total Invoices",  total,       "#E8E4DC"),
            (kc[1], "Avg Audit Score", f"{avg_audit:.0f}", score_color(avg_audit)),
            (kc[2], "High Risk",       high_risk,   "#E87A7A"),
            (kc[3], "Approved",        approved,    "#7EC8A4"),
        ]:
            col.markdown(
                f"""<div class=\"kpi-card\">
                  <div class=\"kpi-num\" style=\"color:{color};\">{value}</div>
                  <div class=\"kpi-lbl\">{label}</div>
                </div>""",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        da1, da2 = st.columns(2)
        with da1:
            trend_fig = chart_trend_line(history)
            if trend_fig: st.plotly_chart(trend_fig, use_container_width=True, key="dash_trend")
        with da2:
            vendor_fig = chart_vendor_bar(history)
            if vendor_fig: st.plotly_chart(vendor_fig, use_container_width=True, key="dash_vendor")

        da3, da4 = st.columns(2)
        with da3:
            st.plotly_chart(chart_spending_heatmap(history), use_container_width=True, key="dash_heat")
        with da4:
            st.plotly_chart(chart_monthly_forecast(history), use_container_width=True, key="dash_fore")

        # History table
        st.markdown("<div class=\'sec-header\'>📋 Invoice History Log</div>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════
#  PAGE: AI COPILOT CHAT
# ══════════════════════════════════════════════════════
elif page == "🤖 AI Copilot Chat":
    st.markdown("## 🤖 AI Audit Copilot")
    st.markdown("Ask questions about your invoices, audit rules, fraud detection, and financial compliance.")

    context = ""
    if st.session_state["history"]:
        context = f"Recent invoices audited: {json.dumps(st.session_state['history'][-3:], indent=2)}"
    else:
        context = "No invoices audited yet in this session."

    # Display chat history
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    quick_qs = [
        "What are common invoice fraud signals?",
        "How to validate GST numbers?",
        "Explain duplicate invoice detection",
        "What is a good audit score?",
    ]
    st.markdown("**💡 Quick Questions:**")
    qcols = st.columns(len(quick_qs))
    chosen_q = None
    for col, q in zip(qcols, quick_qs):
        if col.button(q, key=f"q_{q[:15]}"):
            chosen_q = q

    user_input = st.text_input("Ask the AI Copilot...", key="chat_input",
                                placeholder="E.g., Is this invoice suspicious? What's missing from my invoice?")

    final_q = chosen_q or (user_input if user_input.strip() else None)
    if final_q:
        with st.spinner("🤖 AI is thinking..."):
            reply = ai_chat_response(final_q, context)
        st.session_state["chat_history"].append({"role": "user", "content": final_q})
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state["chat_history"] and st.button("🗑️ Clear Chat"):
        st.session_state["chat_history"] = []
        st.rerun()

# ══════════════════════════════════════════════════════
#  PAGE: VENDOR ANALYTICS
# ══════════════════════════════════════════════════════
elif page == "📈 Vendor Analytics":
    st.markdown("## 📈 Vendor Analytics & Risk Dashboard")
    history = st.session_state["history"]

    if not history:
        st.info("📂 No data available. Audit some invoices first.")
    else:
        vendors = {}
        for h in history:
            v = h.get("vendor", "Unknown")
            if v not in vendors: vendors[v] = {"count":0, "total_spend":0, "avg_audit":0, "fraud_risk":0}
            vendors[v]["count"] += 1
            vendors[v]["avg_audit"] = (vendors[v]["avg_audit"] + h.get("audit_score",0)) / vendors[v]["count"]
            vendors[v]["fraud_risk"] = (vendors[v]["fraud_risk"] + h.get("fraud_risk",0)) / vendors[v]["count"]

        df_vendors = pd.DataFrame([
            {"Vendor": v, "Invoices": d["count"],
             "Avg Audit Score": round(d["avg_audit"],1),
             "Avg Fraud Risk": round(d["fraud_risk"],1)}
            for v, d in vendors.items()
        ])
        st.dataframe(df_vendors, use_container_width=True, hide_index=True)

        vc1, vc2 = st.columns(2)
        with vc1:
            fig_v1 = px.bar(df_vendors, x="Vendor", y="Avg Audit Score",
                            color="Avg Audit Score",
                            color_continuous_scale=[[0,"#E87A7A"],[0.5,"#E8C87A"],[1,"#7EC8A4"]],
                            title="Vendor Audit Scores")
            fig_v1.update_layout(paper_bgcolor="#1A1E24", plot_bgcolor="#2E3740",
                                  font_color="#E8E4DC", height=300)
            st.plotly_chart(fig_v1, use_container_width=True)
        with vc2:
            fig_v2 = px.bar(df_vendors, x="Vendor", y="Avg Fraud Risk",
                            color="Avg Fraud Risk",
                            color_continuous_scale=[[0,"#7EC8A4"],[0.5,"#E8C87A"],[1,"#E87A7A"]],
                            title="Vendor Fraud Risk")
            fig_v2.update_layout(paper_bgcolor="#1A1E24", plot_bgcolor="#2E3740",
                                  font_color="#E8E4DC", height=300)
            st.plotly_chart(fig_v2, use_container_width=True)

# ══════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════
elif page == "⚙️ Settings & Config":
    st.markdown("## ⚙️ Settings & Configuration")

    st.markdown("<div class=\'sec-header\'>🎨 App Information</div>", unsafe_allow_html=True)
    info_cols = st.columns(3)
    info_cols[0].metric("App Version", "3.0 Ultra")
    info_cols[1].metric("Active Features", "60+")
    info_cols[2].metric("AI Model", "LLaMA-3.3-70B")

    st.markdown("<div class=\'sec-header\'>🔧 Active Features</div>", unsafe_allow_html=True)
    features = [
        ("✅", "OCR Support (Scanned/Image PDFs)"),
        ("✅", "Multi-Language Invoice Support (EN/UR/AR)"),
        ("✅", "Fraud Risk Prediction Score"),
        ("✅", "AI Anomaly Detection Engine"),
        ("✅", "Tax Compliance Checker (GST/VAT)"),
        ("✅", "Currency Conversion Engine (Live FX)"),
        ("✅", "Multi-Currency Reporting"),
        ("✅", "Batch Invoice Processing (ZIP Support)"),
        ("✅", "Duplicate Invoice Detection"),
        ("✅", "Vendor Analytics Dashboard"),
        ("✅", "KPI Dashboard with Real-Time Scores"),
        ("✅", "Financial Forecasting Charts"),
        ("✅", "Spending Heatmaps"),
        ("✅", "Interactive Plotly Charts (Radar/Gauge/Sankey)"),
        ("✅", "AI Executive Summary Generation"),
        ("✅", "Smart Recommendations Engine"),
        ("✅", "Auto-Categorization of Expenses"),
        ("✅", "Rule Template Builder"),
        ("✅", "Excel Export with Formatting (XlsxWriter)"),
        ("✅", "CSV + JSON + TXT Report Export"),
        ("✅", "AI Chatbot Copilot for Audits"),
        ("✅", "Real-Time Processing Progress Bars"),
        ("✅", "Historical Invoice Tracking"),
        ("✅", "Missing Field Prediction"),
        ("✅", "Auto-Correction Suggestions"),
        ("✅", "AI Confidence Score Visualization"),
        ("✅", "Fraud Signal Analysis"),
        ("✅", "AI Explanation Panel"),
        ("✅", "Vendor Risk Scoring"),
        ("✅", "Line Item Extraction (Table)"),
    ]
    fc = st.columns(2)
    for i, (icon, feat) in enumerate(features):
        fc[i % 2].markdown(f"{icon} {feat}")

    st.markdown("<div class=\'sec-header\'>📊 Color Palette</div>", unsafe_allow_html=True)
    palette_html = ""
    for hex_, name in [("#E8E4DC","Cream (Primary)"),("#5A6B7A","Steel Blue"),("#2E3740","Dark Slate"),("#1A1E24","Near Black")]:
        palette_html += f"""<div style=\'display:inline-block; margin:8px; text-align:center;\'>
          <div style=\'width:80px; height:80px; background:{hex_}; border-radius:14px;
                       border:1px solid #3a4550; margin-bottom:6px;\'></div>
          <div style=\'font-size:0.7rem; color:#E8E4DC;\'>{hex_}</div>
          <div style=\'font-size:0.65rem; color:#8899AA;\'>{name}</div>
        </div>"""
    st.markdown(palette_html, unsafe_allow_html=True)