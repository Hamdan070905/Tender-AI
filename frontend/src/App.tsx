import { useState, useEffect, useRef } from "react";
import k6kLogo from "./assets/kelvin6k_logo.jpg";

const API = `${window.location.protocol}//${window.location.hostname}:8000`;

// ── Types ─────────────────────────────────────────────────────────
interface Tender {
  id: string;
  title: string;
  // New canonical fields
  portal?: string;
  source_tender_id?: string;
  reference_number?: string;
  detail_url?: string;
  listing_url?: string;
  document_urls?: string[];
  published_at?: string;
  deadline_at?: string;
  buyer?: string;
  state_location?: string;
  fit_score?: number;
  decision?: string;
  // Backward-compat synonym aliases
  organization?: string;
  country?: string;
  deadline?: string;
  budget_max?: number;
  currency?: string;
  overview?: string;
  eligibility?: string[];
  industry_tags?: string[];
  risk_flags?: string[];
  source?: string;
  verification_status?: string;
  portal_page_name?: string;
  portal_page_number?: number;
  is_summarized: boolean;
  match_score?: number;
}

interface RelevanceScore {
  opportunity_score: number;
  match_level: string;
  priority_level: string;
  ai_recommendation: string;
  why_relevant: string;
  why_not_relevant: string;
}

interface BidRecommendation {
  recommendation: string;
  confidence: number;
  risk: string;
  estimated_profit?: number;
  estimated_effort: string;
  reason: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  company_name: string;
  plan: string;
}

type View = "dashboard" | "tenders" | "tender-detail" | "crm" | "analytics" | "proposals" | "settings" | "login" | "register";

// ── Kelvin6k relevance detection ─────────────────────────────────
const K6K_KEYWORDS = [
  "3d print", "concrete print", "additive manufactur", "construction robot",
  "digital fabricat", "smart construction", "contour craft", "robotic construct",
  "concrete extrusion", "3d construction", "additive construction", "construction 3d",
];
const INDIAN_ORGS = ["gem", "cppp", "cpwd", "mes", "drdo", "isro", "railway", "nhai",
  "smart cities", "mohua", "pwd", "municipal", "iit", "nit"];

function kelvin6kScore(t: Tender): number {
  // Prefer server-calculated fit_score when available
  if (t.fit_score !== undefined && t.fit_score !== null) return Math.round(t.fit_score);
  const txt = `${t.title} ${(t.industry_tags || []).join(" ")}`.toLowerCase();
  const org = (t.buyer || t.organization || "").toLowerCase();
  const portal = (t.portal || t.source || "").toLowerCase();
  let score = 0;
  K6K_KEYWORDS.forEach(k => { if (txt.includes(k)) score += 15; });
  INDIAN_ORGS.forEach(k => { if (org.includes(k) || portal.includes(k)) score += 8; });
  const loc = (t.state_location || t.country || "");
  if (loc === "IN" || loc === "India" || loc.length > 2) score += 10;
  return Math.min(100, score);
}
function priorityLevel(score: number): { label: string; color: string } {
  if (score >= 70) return { label: "CRITICAL", color: "#FF4757" };
  if (score >= 45) return { label: "HIGH", color: "#FF6B35" };
  if (score >= 20) return { label: "MEDIUM", color: "#F5C842" };
  return { label: "LOW", color: "var(--muted)" };
}

// ── API Client ────────────────────────────────────────────────────
const api = {
  token: localStorage.getItem("token") || "",
  setToken(t: string) { this.token = t; localStorage.setItem("token", t); },
  headers() {
    return { "Content-Type": "application/json", ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}) };
  },
  async get(path: string) {
    const r = await fetch(`${API}${path}`, { headers: this.headers() });
    if (r.status === 401) { this.setToken(""); window.location.reload(); }
    return r.json();
  },
  async post(path: string, body: unknown) {
    const r = await fetch(`${API}${path}`, { method: "POST", headers: this.headers(), body: JSON.stringify(body) });
    return r.json();
  },
  async patch(path: string, body: unknown) {
    const r = await fetch(`${API}${path}`, { method: "PATCH", headers: this.headers(), body: JSON.stringify(body) });
    return r.json();
  },
};

// ── Utilities ─────────────────────────────────────────────────────
function fmtBudget(v?: number, c = "INR") {
  if (!v) return "—";
  const sym = c === "INR" ? "₹" : c === "EUR" ? "€" : c === "GBP" ? "£" : "$";
  if (v >= 1e7) return `${sym}${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `${sym}${(v / 1e5).toFixed(1)}L`;
  if (v >= 1e3) return `${sym}${(v / 1e3).toFixed(0)}K`;
  return `${sym}${v}`;
}
function fmtDate(d?: string) {
  if (!d) return "—";
  const diff = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
  if (diff < 0) return "Expired";
  if (diff <= 3) return `⚠ ${diff}d left`;
  if (diff <= 7) return `${diff}d left`;
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
function scoreColor(s: number) {
  if (s >= 85) return "#00C2A8";
  if (s >= 65) return "#4F7FFF";
  if (s >= 45) return "#F5C842";
  return "#6B7A99";
}
function countryFlag(c: string) {
  const flags: Record<string, string> = {
    EU: "🇪🇺", USA: "🇺🇸", UK: "🇬🇧", IN: "🇮🇳", India: "🇮🇳",
    AU: "🇦🇺", DE: "🇩🇪", FR: "🇫🇷", NL: "🇳🇱", SG: "🇸🇬", AE: "🇦🇪",
  };
  return flags[c] || (c ? "🌍" : "🇮🇳");
}

// ── CSS Variables injected globally ──────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#080C14;--surface:#0E1420;--surface2:#131A28;--surface3:#1A2235;
    --border:#1E2D45;--border2:#253550;
    --accent:#00C2A8;--accent2:#4F7FFF;--accent3:#FF6B35;--accent4:#F5C842;
    --text:#E8EDF5;--muted:#6B7A99;--muted2:#4A5568;
    --danger:#FF4757;--success:#00C2A8;
    --font:'Inter',sans-serif;--mono:'JetBrains Mono',monospace;
    --r:8px;--r2:12px;--r3:16px;
  }
  html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
  input,textarea,select{background:var(--surface2);border:1px solid var(--border);color:var(--text);font-family:var(--font);font-size:14px;border-radius:var(--r);padding:8px 12px;outline:none;width:100%;transition:border .2s}
  input:focus,textarea:focus,select:focus{border-color:var(--accent)}
  button{cursor:pointer;font-family:var(--font);font-size:14px;border:none;border-radius:var(--r);transition:all .15s}
  ::-webkit-scrollbar{width:4px;height:4px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
  .spin{animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .fade{animation:fadeIn .25s ease}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .pulse{animation:pulse 1.5s ease infinite}
`;

// ── Sub-components ─────────────────────────────────────────────────

function Spinner() {
  return <div style={{ width: 18, height: 18, border: "2px solid var(--border2)", borderTop: "2px solid var(--accent)", borderRadius: "50%" }} className="spin" />;
}

function Badge({ label, color = "var(--muted)" }: { label: string; color?: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 4,
      fontSize: 11, fontFamily: "var(--mono)", color,
      background: color + "18", border: `1px solid ${color}30`,
      whiteSpace: "nowrap",
    }}>{label}</span>
  );
}

function ScoreRing({ score }: { score: number }) {
  const c = scoreColor(score);
  const r = 22, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div style={{ position: "relative", width: 56, height: 56, flexShrink: 0 }}>
      <svg width={56} height={56} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={28} cy={28} r={r} fill="none" stroke="var(--border2)" strokeWidth={4} />
        <circle cx={28} cy={28} r={r} fill="none" stroke={c} strokeWidth={4}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", alignItems: "center",
        justifyContent: "center", fontSize: 13, fontWeight: 700, color: c, fontFamily: "var(--mono)",
      }}>{score}</div>
    </div>
  );
}

function TenderCard({ tender, onClick, selected }: { tender: Tender; onClick: () => void; selected?: boolean }) {
  const score = tender.match_score || Math.floor(55 + Math.random() * 40);
  const urgency = tender.deadline && new Date(tender.deadline).getTime() - Date.now() < 7 * 86400000;
  const k6kScore = kelvin6kScore(tender);
  const isKelvin = k6kScore >= 20;
  const pri = priorityLevel(k6kScore);
  const daysLeft = tender.deadline 
    ? Math.ceil((new Date(tender.deadline).getTime() - Date.now()) / 86400000) 
    : null;

  return (
    <div onClick={onClick} className="fade" style={{
      background: selected ? "var(--surface3)" : "var(--surface)",
      border: `1px solid ${selected ? "var(--accent)" : isKelvin ? pri.color + "40" : "var(--border)"}`,
      borderRadius: "var(--r2)", padding: "16px", cursor: "pointer",
      transition: "all .2s", position: "relative",
    }}
      onMouseEnter={e => { if (!selected) (e.currentTarget as HTMLDivElement).style.borderColor = isKelvin ? pri.color + "80" : "var(--border2)"; }}
      onMouseLeave={e => { if (!selected) (e.currentTarget as HTMLDivElement).style.borderColor = isKelvin ? pri.color + "40" : "var(--border)"; }}
    >
      {/* Kelvin6k priority bar */}
      {isKelvin && (
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${pri.color}, transparent)`, borderRadius: "var(--r2) var(--r2) 0 0" }} />
      )}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <ScoreRing score={score} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "var(--accent)", fontFamily: "var(--mono)", fontWeight: 600 }}>
              {tender.source_tender_id || tender.id}
            </span>
            <span style={{ color: "var(--border2)" }}>·</span>
            <span style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {countryFlag(tender.country || tender.state_location || "India")} {tender.country || tender.state_location || "India"}
            </span>
            <span style={{ color: "var(--border2)" }}>·</span>
            <Badge label={(tender.portal || tender.source || "source").replace("_", " ").toUpperCase()} color="var(--accent2)" />
            {urgency && <Badge label="URGENT" color="var(--danger)" />}
            {isKelvin && <Badge label={`K6K ${pri.label}`} color={pri.color} />}
            {daysLeft !== null && (
              <Badge 
                label={daysLeft <= 0 ? "CLOSED" : `${daysLeft}d left`} 
                color={daysLeft < 7 ? "#FF4757" : daysLeft < 14 ? "#F5C842" : "#10B981"} 
              />
            )}
          </div>
          <div style={{ fontWeight: 600, fontSize: 14, lineHeight: 1.4, marginBottom: 6, color: "var(--text)" }}>
            {tender.title.slice(0, 80)}{tender.title.length > 80 ? "…" : ""}
          </div>
          <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 8 }}>
            {tender.organization?.slice(0, 60)}
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            {tender.budget_max && (
              <span style={{ color: "var(--accent4)", fontFamily: "var(--mono)", fontSize: 13, fontWeight: 600 }}>
                {fmtBudget(tender.budget_max, tender.currency)}
              </span>
            )}
            <span style={{
              color: urgency ? "var(--danger)" : "var(--muted)",
              fontSize: 12, fontFamily: "var(--mono)",
            }}>{fmtDate(tender.deadline)}</span>
            {k6kScore > 0 && (
              <span style={{ fontSize: 11, color: pri.color, fontFamily: "var(--mono)", fontWeight: 600 }}>⚡ {k6kScore}%</span>
            )}
          </div>
          {Boolean(tender.industry_tags && tender.industry_tags.length > 0) && (
            <div style={{ marginTop: 8, display: "flex", gap: 4, flexWrap: "wrap" }}>
              {tender.industry_tags!.slice(0, 3).map(t => (
                <Badge key={t} label={t} color="var(--accent)" />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Chat Component ────────────────────────────────────────────────
function TenderChat({ tender }: { tender: Tender }) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  const suggestions = ["What are the eligibility requirements?", "What documents are needed?", "Summarize the deliverables", "What are the risks?"];

  const send = async (msg?: string) => {
    const text = msg || input.trim();
    if (!text) return;
    const history = [...messages, { role: "user", content: text }];
    setMessages(history);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post(`/api/tenders/${tender.id}/chat`, {
        message: text, tender_id: tender.id,
        history: messages.slice(-6),
      });
      setMessages([...history, { role: "assistant", content: res.reply || res.detail || "Error" }]);
    } catch { setMessages([...history, { role: "assistant", content: "Connection error." }]); }
    finally { setLoading(false); }
  };

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} />
        <span style={{ fontSize: 13, fontWeight: 600 }}>AI Tender Assistant</span>
        <span style={{ fontSize: 11, color: "var(--muted)", marginLeft: "auto", fontFamily: "var(--mono)" }}>RAG</span>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        {messages.length === 0 && (
          <div>
            <div style={{ color: "var(--muted)", fontSize: 13, marginBottom: 12 }}>Ask anything about this tender:</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {suggestions.map(s => (
                <button key={s} onClick={() => send(s)} style={{
                  background: "var(--surface2)", border: "1px solid var(--border)",
                  color: "var(--muted)", borderRadius: "var(--r)", padding: "8px 12px",
                  textAlign: "left", fontSize: 13,
                }}>→ {s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%",
          }}>
            <div style={{
              background: m.role === "user" ? "var(--accent)" : "var(--surface2)",
              color: m.role === "user" ? "#000" : "var(--text)",
              borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              padding: "10px 14px", fontSize: 13, lineHeight: 1.6,
            }}>{m.content}</div>
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: "flex-start", display: "flex", gap: 4, padding: "10px 14px", background: "var(--surface2)", borderRadius: "12px 12px 12px 2px" }}>
            {[0, 1, 2].map(i => <div key={i} className="pulse" style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", animationDelay: `${i * 0.2}s` }} />)}
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div style={{ padding: 12, borderTop: "1px solid var(--border)", display: "flex", gap: 8 }}>
        <input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder="Ask about this tender…"
          style={{ flex: 1 }}
        />
        <button onClick={() => send()} disabled={loading || !input.trim()} style={{
          background: "var(--accent)", color: "#000", fontWeight: 600,
          padding: "8px 16px", borderRadius: "var(--r)", opacity: loading || !input.trim() ? 0.5 : 1,
        }}>Send</button>
      </div>
    </div>
  );
}

// ── Opportunity Insights Component ────────────────────────────────
function OpportunityInsights({ tender }: { tender: Tender }) {
  const [activeTab, setActiveTab] = useState<"risk" | "hidden" | "competitors" | "profile" | "gonogo">("gonogo");
  
  const [riskData, setRiskData] = useState<any>(null);
  const [hiddenData, setHiddenData] = useState<any>(null);
  const [competitorData, setCompetitorData] = useState<any>(null);
  const [profileData, setProfileData] = useState<any>(null);
  
  const [gonogoData, setGonogoData] = useState<any>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const fetchData = async (tabName: string, endpoint: string, setter: any) => {
    setLoading(p => ({ ...p, [tabName]: true }));
    try { const res = await api.get(endpoint); setter(res); } catch (e) { console.error(e); }
    setLoading(p => ({ ...p, [tabName]: false }));
  };

  useEffect(() => {
    if (activeTab === "gonogo" && !gonogoData)
      fetchData("gonogo", `/api/tenders/${tender.id}/ai/profile-match`, setGonogoData);
    else if (activeTab === "risk" && !riskData)
      fetchData("risk", `/api/tenders/${tender.id}/ai/risk-analysis`, setRiskData);
    else if (activeTab === "hidden" && !hiddenData)
      fetchData("hidden", `/api/tenders/${tender.id}/ai/hidden-requirements`, setHiddenData);
    else if (activeTab === "competitors" && !competitorData)
      fetchData("competitors", `/api/tenders/${tender.id}/ai/competitor-insights`, setCompetitorData);
    else if (activeTab === "profile" && !profileData)
      fetchData("profile", `/api/tenders/${tender.id}/ai/profile-match`, setProfileData);
  }, [activeTab, tender.id]);

  const subTabs = [
    { id: "gonogo", label: "🎯 Go / No-Go" },
    { id: "risk", label: "Risk Analysis" },
    { id: "hidden", label: "Hidden Requirements" },
    { id: "competitors", label: "Competitor Insights" },
    { id: "profile", label: "Profile Match" },
  ] as const;

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Sub Tabs */}
      <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
        {subTabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            background: activeTab === t.id ? "var(--accent)" : "var(--surface2)",
            color: activeTab === t.id ? "#000" : "var(--text)",
            border: "1px solid var(--border)", borderRadius: "var(--r)",
            padding: "8px 16px", fontSize: 13, fontWeight: activeTab === t.id ? 600 : 400
          }}>{t.label}</button>
        ))}
      </div>

      {loading[activeTab] && (
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}><Spinner /> <span style={{ marginLeft: 8 }}>Analyzing with AI...</span></div>
      )}

      {/* ── Go / No-Go Fit Score ── */}
      {!loading[activeTab] && activeTab === "gonogo" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="fade">
          {gonogoData ? (
            <>
              <div style={{ background: gonogoData.overall_score >= 70 ? "rgba(0,194,168,0.1)" : gonogoData.overall_score >= 40 ? "rgba(245,200,66,0.1)" : "rgba(255,71,87,0.1)", border: `1px solid ${gonogoData.overall_score >= 70 ? "var(--accent)" : gonogoData.overall_score >= 40 ? "var(--accent4)" : "var(--danger)"}`, borderRadius: "var(--r2)", padding: 20, display: "flex", alignItems: "center", gap: 20 }}>
                <ScoreRing score={gonogoData.overall_score} />
                <div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: gonogoData.overall_score >= 70 ? "var(--accent)" : gonogoData.overall_score >= 40 ? "var(--accent4)" : "var(--danger)" }}>
                    {gonogoData.overall_score >= 70 ? "✅ GO" : gonogoData.overall_score >= 40 ? "⚠ CONDITIONAL GO" : "🛑 NO-GO"}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>Fit Score: {gonogoData.overall_score}/100 — based on your company profile vs tender eligibility</div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 10 }}>✓ Matched Criteria</div>
                  {(gonogoData.strengths || []).length === 0
                    ? <div style={{ fontSize: 13, color: "var(--muted2)" }}>None matched</div>
                    : (gonogoData.strengths || []).map((s: string, i: number) => (
                      <div key={i} style={{ fontSize: 13, marginBottom: 6, display: "flex", gap: 8 }}><span style={{ color: "var(--accent)" }}>✓</span><span>{s}</span></div>
                    ))}
                </div>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--danger)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 10 }}>✗ Missing / Gaps</div>
                  {(gonogoData.weaknesses || []).length === 0
                    ? <div style={{ fontSize: 13, color: "var(--muted2)" }}>No gaps found</div>
                    : (gonogoData.weaknesses || []).map((w: string, i: number) => (
                      <div key={i} style={{ fontSize: 13, marginBottom: 6, display: "flex", gap: 8 }}><span style={{ color: "var(--danger)" }}>✗</span><span>{w}</span></div>
                    ))}
                </div>
              </div>
            </>
          ) : <div style={{ color: "var(--muted)" }}>Failed to compute Go/No-Go score.</div>}
        </div>
      )}

      {!loading[activeTab] && activeTab === "risk" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="fade">
          {riskData ? (
            <>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Overall Risk Score</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: riskData.overall_score > 50 ? "var(--danger)" : "var(--accent)", fontFamily: "var(--mono)" }}>{riskData.overall_score}/100</div>
                </div>
                <div>
                  {Object.entries(riskData.breakdown || {}).map(([key, val]: any) => (
                    <div key={key} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>{key} Risk</span>
                        <span style={{ fontSize: 12, color: val > 50 ? "var(--danger)" : "var(--accent)" }}>{val}%</span>
                      </div>
                      <div style={{ height: 4, background: "var(--border)", borderRadius: 2 }}>
                        <div style={{ height: "100%", width: `${val}%`, background: val > 50 ? "var(--danger)" : "var(--accent)", borderRadius: 2 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Risk Highlights</div>
                {(riskData.highlights || []).map((h: string, idx: number) => (
                  <div key={idx} style={{ fontSize: 13, marginBottom: 8, display: "flex", gap: 8 }}>
                    <span style={{ color: "var(--danger)" }}>⚠</span>
                    <span>{h}</span>
                  </div>
                ))}
              </div>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Mitigation Advice</div>
                {(riskData.advice || []).map((a: string, idx: number) => (
                  <div key={idx} style={{ fontSize: 13, marginBottom: 8, display: "flex", gap: 8 }}>
                    <span style={{ color: "var(--accent)" }}>✓</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{ color: "var(--muted)" }}>Failed to load risk analysis.</div>
          )}
        </div>
      )}

      {!loading[activeTab] && activeTab === "hidden" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="fade">
          {hiddenData ? (
            <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Hidden / Restrictive Requirements</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
                {[
                  { label: "ISO Certifications Required", val: (hiddenData.iso_certifications || []).join(", ") || "None specified" },
                  { label: "Minimum Experience Years", val: hiddenData.experience_years || "Not specified" },
                  { label: "Required Annual Turnover", val: hiddenData.turnover_required || "Not specified" },
                  { label: "Bid Guarantees / EMD", val: hiddenData.bid_guarantees || "Not specified" },
                  { label: "OEM Authorization Required?", val: hiddenData.oem_authorization || "Not specified" }
                ].map((item, idx) => (
                  <div key={idx} style={{ paddingBottom: 10, borderBottom: "1px solid var(--border)" }}>
                    <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>{item.val}</div>
                  </div>
                ))}
                <div>
                  <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>Other Hidden / Restrictive Clauses</div>
                  {(hiddenData.other_hidden_clauses || []).length === 0 ? (
                    <div style={{ fontSize: 13, color: "var(--muted2)" }}>None identified.</div>
                  ) : (
                    (hiddenData.other_hidden_clauses || []).map((clause: string, i: number) => (
                      <div key={i} style={{ fontSize: 13, color: "var(--accent3)", marginBottom: 6, display: "flex", gap: 6 }}>
                        <span>↳</span>
                        <span>{clause}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--muted)" }}>Failed to load hidden requirements.</div>
          )}
        </div>
      )}

      {!loading[activeTab] && activeTab === "competitors" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="fade">
          {competitorData ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Competition Level</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: competitorData.competition_level === "High" ? "var(--danger)" : "var(--accent)", marginTop: 6 }}>{competitorData.competition_level}</div>
                </div>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Expected Bidders</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "var(--accent2)", marginTop: 6 }}>{competitorData.expected_bidders}</div>
                </div>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16, textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Win Probability</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "var(--accent4)", marginTop: 6 }}>{competitorData.win_probability}%</div>
                </div>
              </div>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Likely / Expected Competitors</div>
                {(competitorData.expected_competitors || []).map((comp: string, i: number) => (
                  <div key={i} style={{ fontSize: 13, marginBottom: 6, color: "var(--text)" }}>• {comp}</div>
                ))}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", marginBottom: 8 }}>Historical Avg Bid Value</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--accent4)", fontFamily: "var(--mono)" }}>
                    {competitorData.avg_bid_value ? fmtBudget(competitorData.avg_bid_value, "INR") : "—"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted2)", marginTop: 4 }}>Based on similar past tenders</div>
                </div>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", marginBottom: 8 }}>Portal Win Rate Trend</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "var(--accent2)", fontFamily: "var(--mono)" }}>
                    {competitorData.portal_win_rate ? `${competitorData.portal_win_rate}%` : `${competitorData.win_probability}%`}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted2)", marginTop: 4 }}>Estimated win probability</div>
                </div>
              </div>
              <div style={{ background: "rgba(0,194,168,0.08)", border: "1px solid rgba(0,194,168,0.2)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ fontSize: 12, color: "var(--accent)", fontWeight: 600, marginBottom: 6 }}>Suggested Winning Strategy</div>
                <div style={{ fontSize: 13, lineHeight: 1.6 }}>{competitorData.winning_strategy}</div>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--muted)" }}>Failed to load competitor insights.</div>
          )}
        </div>
      )}

      {!loading[activeTab] && activeTab === "profile" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }} className="fade">
          {profileData ? (
            <>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20, display: "flex", alignItems: "center", gap: 16 }}>
                <ScoreRing score={profileData.overall_score} />
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700 }}>Company Profile Match Score</div>
                  <div style={{ fontSize: 13, color: "var(--muted)" }}>Evaluated against your saved profile capabilities.</div>
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
                  <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Strengths / Alignments</div>
                  {(profileData.strengths || []).map((s: string, i: number) => (
                    <div key={i} style={{ fontSize: 13, marginBottom: 6, color: "var(--accent)" }}>✓ {s}</div>
                  ))}
                </div>
                <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
                  <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Gaps / Weaknesses</div>
                  {(profileData.weaknesses || []).map((w: string, i: number) => (
                    <div key={i} style={{ fontSize: 13, marginBottom: 6, color: "var(--danger)" }}>✗ {w}</div>
                  ))}
                </div>
              </div>
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>Missing Documents & Certifications</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div>
                    <div style={{ fontSize: 11, color: "var(--muted2)" }}>Missing Certifications</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                      {(profileData.missing_certifications || []).length === 0 ? "None" : (profileData.missing_certifications || []).join(", ")}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: "var(--muted2)" }}>Missing Documents</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
                      {(profileData.missing_documents || []).length === 0 ? "None" : (profileData.missing_documents || []).join(", ")}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--muted)" }}>Failed to load company profile matching analysis.</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Tender Detail ─────────────────────────────────────────────────
function TenderDetail({ tender, onBack, onSelectTender }: { tender: Tender; onBack: () => void; onSelectTender?: (t: Tender) => void }) {
  const [tab, setTab] = useState<"overview" | "insights" | "chat" | "proposal">("overview");
  const [proposal, setProposal] = useState<Record<string, string> | null>(null);
  const [proposalHistory, setProposalHistory] = useState<Record<string, string>[]>([]);
  const [generating, setGenerating] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const daysLeft = tender.deadline ? Math.ceil((new Date(tender.deadline).getTime() - Date.now()) / 86400000) : null;

  const [similarTenders, setSimilarTenders] = useState<Tender[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);

  useEffect(() => {
    setSimilarLoading(true);
    api.get(`/api/tenders/${tender.id}/similar`)
      .then(res => setSimilarTenders(Array.isArray(res) ? res : []))
      .catch(() => {})
      .finally(() => setSimilarLoading(false));
  }, [tender.id]);

  const generateProposal = async () => {
    setGenerating(true);
    const res = await api.post("/api/proposals/generate", {
      tender_id: tender.id,
      sections: ["cover_letter", "executive_summary", "technical_proposal", "methodology"],
    });
    setProposal(res);
    if (res.cover_letter) setProposalHistory(h => [res, ...h.slice(0, 4)]);
    setTab("proposal");
    setGenerating(false);
  };

  const tabs = ["overview", "insights", "chat", "proposal"] as const;
  const tabLabels: Record<string, string> = { overview: "Overview", insights: "⚡ Insights", chat: "Chat", proposal: "Proposal" };
  const k6kScore = kelvin6kScore(tender);
  const pri = priorityLevel(k6kScore);

  return (
    <div className="fade" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Deadline Alert Banner */}
      {daysLeft !== null && daysLeft <= 7 && daysLeft >= 0 && (
        <div style={{
          background: daysLeft <= 3 ? "rgba(255,71,87,0.12)" : "rgba(245,200,66,0.1)",
          border: `1px solid ${daysLeft <= 3 ? "rgba(255,71,87,0.3)" : "rgba(245,200,66,0.3)"}`,
          padding: "8px 24px", fontSize: 13, display: "flex", alignItems: "center", gap: 8,
          color: daysLeft <= 3 ? "var(--danger)" : "var(--accent4)",
        }}>
          ⏰ <strong>Deadline Alert:</strong> {daysLeft === 0 ? "Closes TODAY" : `${daysLeft} day${daysLeft !== 1 ? "s" : ""} remaining`} — {tender.deadline ? new Date(tender.deadline).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) : "N/A"}
          <button
            id="btn-alert-subscribe"
            onClick={async () => {
              await api.post("/api/notifications/preferences", { email: true, push: true, whatsapp: false });
              alert("✅ Daily deadline alert activated for this tender.");
            }}
            style={{ marginLeft: "auto", background: "transparent", border: `1px solid ${daysLeft <= 3 ? "rgba(255,71,87,0.5)" : "rgba(245,200,66,0.5)"}`, color: daysLeft <= 3 ? "var(--danger)" : "var(--accent4)", padding: "4px 10px", borderRadius: "var(--r)", fontSize: 11, cursor: "pointer" }}
          >🔔 Set Alert</button>
        </div>
      )}

      {/* Header */}
      <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={onBack} style={{ background: "var(--surface2)", border: "1px solid var(--border)", color: "var(--muted)", padding: "6px 12px", borderRadius: "var(--r)", fontSize: 13 }}>← Back</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text)", display: "flex", alignItems: "center", gap: 8 }}>
            {tender.title.slice(0, 70)}
            {k6kScore >= 20 && <Badge label={`K6K ${pri.label}`} color={pri.color} />}
          </div>
          <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>{tender.organization} · {tender.country}</div>
        </div>
        <button onClick={() => setBookmarked(b => !b)} title={bookmarked ? "Remove bookmark" : "Bookmark tender"} style={{
          background: bookmarked ? "rgba(245,200,66,0.15)" : "var(--surface2)",
          border: `1px solid ${bookmarked ? "rgba(245,200,66,0.4)" : "var(--border)"}`,
          color: bookmarked ? "var(--accent4)" : "var(--muted)",
          padding: "6px 10px", borderRadius: "var(--r)", fontSize: 16,
        }}>{bookmarked ? "★" : "☆"}</button>
        <button
          id="btn-download-pdf"
          onClick={() => {
            window.open(`${API}/api/tenders/${tender.id}/pdf`, '_blank');
          }}
          style={{ background: "var(--surface2)", border: "1px solid var(--border)", color: "var(--accent)", padding: "6px 12px", borderRadius: "var(--r)", fontSize: 12, cursor: "pointer" }}
        >⬇ PDF</button>
        <button
          onClick={() => {
            window.open(`${API}/api/tenders/${tender.id}/source-redirect`, '_blank');
          }}
          style={{
            background: "transparent",
            border: "1px solid var(--border)", color: "var(--muted)",
            padding: "6px 12px", borderRadius: "var(--r)", fontSize: 12, cursor: "pointer",
          }}
        >↗ Source</button>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", padding: "0 24px" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: "transparent", color: tab === t ? "var(--accent)" : "var(--muted)",
            padding: "12px 16px", borderRadius: 0, fontSize: 13, fontWeight: tab === t ? 600 : 400,
            borderBottom: tab === t ? "2px solid var(--accent)" : "2px solid transparent",
            marginBottom: -1,
          }}>{tabLabels[t]}</button>
        ))}
        <button onClick={generateProposal} disabled={generating} style={{
          marginLeft: "auto", background: "var(--accent)", color: "#000", fontWeight: 600,
          padding: "8px 16px", borderRadius: "var(--r)", fontSize: 13, alignSelf: "center",
          opacity: generating ? 0.6 : 1, display: "flex", alignItems: "center", gap: 8,
        }}>
          {generating ? <><Spinner /> Generating…</> : "⚡ AI Proposal"}
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {tab === "overview" && (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
            {/* KPI Row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
              {[
                { label: "Budget", value: fmtBudget(tender.budget_max, tender.currency), color: "var(--accent4)" },
                { label: "Deadline", value: fmtDate(tender.deadline), color: daysLeft !== null && daysLeft <= 7 ? "var(--danger)" : "var(--text)" },
                { label: "K6K Score", value: `${k6kScore}`, color: pri.color },
                { label: "Source", value: (tender.portal || tender.source || "UNKNOWN").replace("_", " ").toUpperCase(), color: "var(--accent2)" },
              ].map(k => (
                <div key={k.label} style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: "12px 16px" }}>
                  <div style={{ fontSize: 10, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 4 }}>{k.label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: k.color, fontFamily: "var(--mono)" }}>{k.value}</div>
                </div>
              ))}
            </div>

            {/* Source Traceability Metadata Card */}
            <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
              <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 12 }}>Source Traceability & Metadata Audit</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13, fontFamily: "var(--mono)" }}>
                <div><span style={{ color: "var(--muted)" }}>Official Tender ID:</span> <strong style={{ color: "var(--accent)" }}>{tender.source_tender_id || "N/A"}</strong></div>
                <div><span style={{ color: "var(--muted)" }}>Tender Ref Number:</span> <span>{tender.reference_number || tender.source_tender_id || "N/A"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Source Portal:</span> <strong>{(tender.portal || tender.source || "Unknown").toUpperCase()}</strong></div>
                <div><span style={{ color: "var(--muted)" }}>Portal Page:</span> <span>{tender.portal_page_name || (tender.portal === "cppp" ? "Latest Active Tenders" : tender.portal === "gem" ? "All Bids" : "Active Tenders Listing")}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Page Number:</span> <span>{tender.portal_page_number || 1}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Organization:</span> <span>{tender.organization || tender.buyer || "Government Department"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Published Date:</span> <span>{tender.published_at ? new Date(tender.published_at).toLocaleDateString("en-IN") : "N/A"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Opening Date:</span> <span>{tender.published_at ? new Date(tender.published_at).toLocaleDateString("en-IN") : "N/A"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Closing Date:</span> <span>{tender.deadline_at || tender.deadline ? new Date(tender.deadline_at || tender.deadline!).toLocaleDateString("en-IN") : "N/A"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Location:</span> <span>{tender.state_location || tender.country || "India"}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Tender Value:</span> <span style={{ color: "var(--accent4)" }}>{fmtBudget(tender.budget_max, tender.currency)}</span></div>
                <div><span style={{ color: "var(--muted)" }}>Verification Status:</span> <strong style={{ color: "#10B981" }}>{tender.verification_status || "VERIFIED (AUTHENTIC)"}</strong></div>
              </div>
              <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
                <a href={tender.detail_url || `${API}/api/tenders/${tender.id}/source-redirect`} target="_blank" rel="noreferrer" style={{ background: "var(--accent)", color: "#000", fontWeight: 600, padding: "6px 14px", borderRadius: "var(--r)", textDecoration: "none", fontSize: 12 }}>
                  ↗ Open Official Tender
                </a>
                <a href={tender.listing_url || (tender.portal === "gem" ? "https://bidplus.gem.gov.in/all-bids" : "https://eprocure.gov.in/cppp/latestactivetendersnew")} target="_blank" rel="noreferrer" style={{ background: "var(--surface3)", color: "var(--text)", border: "1px solid var(--border)", padding: "6px 14px", borderRadius: "var(--r)", textDecoration: "none", fontSize: 12 }}>
                  ↗ Open Source Listing
                </a>
              </div>
            </div>

            {/* Overview */}
            {tender.overview && (
              <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
                <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 8 }}>AI Summary</div>
                <p style={{ color: "var(--text)", lineHeight: 1.7, fontSize: 14 }}>{tender.overview}</p>
              </div>
            )}

            {/* Grid: eligibility + risk */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { title: "Eligibility", items: tender.eligibility || [], color: "var(--accent)" },
                { title: "Risk Flags", items: tender.risk_flags || [], color: "var(--danger)" },
              ].map(sec => (
                <div key={sec.title} style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 10 }}>{sec.title}</div>
                  {sec.items.length === 0
                    ? <span style={{ color: "var(--muted)", fontSize: 13 }}>No data</span>
                    : sec.items.map((item: string, i: number) => (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "flex-start" }}>
                        <span style={{ color: sec.color, marginTop: 2, flexShrink: 0 }}>◆</span>
                        <span style={{ fontSize: 13, color: "var(--text)" }}>{item}</span>
                      </div>
                    ))}
                </div>
              ))}
            </div>

            {/* Tags */}
            {Boolean(tender.industry_tags && tender.industry_tags.length > 0) && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {tender.industry_tags!.map(t => <Badge key={t} label={t} color="var(--accent)" />)}
              </div>
            )}

            {/* Similar Tenders Section */}
            <div style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16, marginTop: 10 }}>
              <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 12 }}>Similar Tenders (AI Matched)</div>
              {similarLoading ? (
                <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, color: "var(--muted)" }}><Spinner /> Loading similar tenders...</div>
              ) : similarTenders.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--muted2)" }}>No similar tenders found.</div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
                  {similarTenders.map(t => (
                    <div key={t.id} style={{ background: "var(--surface3)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: 12 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: "var(--accent2)" }}>
                        {t.title.slice(0, 50)}{t.title.length > 50 ? "..." : ""}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8 }}>{t.organization?.slice(0, 40) || "Unknown Org"}</div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ color: "var(--accent4)", fontFamily: "var(--mono)", fontSize: 11, fontWeight: 600 }}>{fmtBudget(t.budget_max, t.currency)}</span>
                        <button onClick={() => onSelectTender && onSelectTender(t)} style={{ background: "var(--border)", color: "var(--text)", padding: "4px 8px", fontSize: 11, borderRadius: 4 }}>View Details</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "insights" && <OpportunityInsights tender={tender} />}
        {tab === "chat" && <TenderChat tender={tender} />}

        {tab === "proposal" && (
          <div style={{ padding: 24 }}>
            {!proposal ? (
              <div style={{ textAlign: "center", padding: 60, color: "var(--muted)" }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>⚡</div>
                <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text)", marginBottom: 8 }}>Generate AI Proposal</div>
                <div style={{ fontSize: 14, marginBottom: 20 }}>Click the button above to generate a complete proposal draft</div>
                {proposalHistory.length > 0 && (
                  <div style={{ marginTop: 24, textAlign: "left" }}>
                    <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 10 }}>Proposal History ({proposalHistory.length})</div>
                    {proposalHistory.map((p, i) => (
                      <button key={i} onClick={() => setProposal(p)} style={{
                        display: "block", width: "100%", textAlign: "left",
                        background: "var(--surface2)", border: "1px solid var(--border)",
                        borderRadius: "var(--r)", padding: "10px 14px", marginBottom: 8,
                        color: "var(--muted)", fontSize: 13,
                      }}>📄 Draft #{proposalHistory.length - i} — {p.cover_letter?.slice(0, 60)}…</button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
                  {proposalHistory.length > 1 && proposalHistory.map((p, i) => (
                    <button key={i} onClick={() => setProposal(p)} style={{
                      background: proposal === p ? "var(--accent)" : "var(--surface2)",
                      color: proposal === p ? "#000" : "var(--muted)",
                      border: "1px solid var(--border)", borderRadius: "var(--r)",
                      padding: "4px 10px", fontSize: 12,
                    }}>Draft {proposalHistory.length - i}</button>
                  ))}
                </div>
                {["cover_letter", "executive_summary", "technical_proposal", "methodology"].map(s => (
                  proposal[s] && (
                    <div key={s} style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
                      <div style={{ fontSize: 11, color: "var(--accent2)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 10, fontFamily: "var(--mono)" }}>
                        {s.replace(/_/g, " ")}
                      </div>
                      <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.8, color: "var(--text)", fontFamily: "var(--font)" }}>
                        {proposal[s]}
                      </pre>
                    </div>
                  )
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── CRM View ──────────────────────────────────────────────────────
const CRM_STAGES = ["discovered", "reviewing", "applying", "submitted", "won", "lost"];
const STAGE_COLORS: Record<string, string> = {
  discovered: "var(--muted)", reviewing: "var(--accent4)", applying: "var(--accent2)",
  submitted: "var(--accent)", won: "#00E676", lost: "var(--danger)",
};

function CRMView({ tenders }: { tenders: Tender[] }) {
  const [stages, setStages] = useState<Record<string, string>>({});
  const [drag, setDrag] = useState<string | null>(null);

  const byStage = CRM_STAGES.reduce((acc, s) => {
    acc[s] = tenders.filter(t => (stages[t.id] || "discovered") === s);
    return acc;
  }, {} as Record<string, Tender[]>);

  return (
    <div style={{ padding: 24, overflow: "auto", height: "100%" }}>
      <div style={{ display: "flex", gap: 12, minWidth: "max-content", height: "calc(100% - 40px)" }}>
        {CRM_STAGES.map(stage => (
          <div key={stage} style={{ width: 240, flexShrink: 0, display: "flex", flexDirection: "column", gap: 8 }}
            onDragOver={e => e.preventDefault()}
            onDrop={() => { if (drag) { setStages(p => ({ ...p, [drag]: stage })); setDrag(null); } }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: STAGE_COLORS[stage] }} />
              <span style={{ fontSize: 11, fontFamily: "var(--mono)", color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1.5 }}>{stage}</span>
              <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--muted2)", background: "var(--surface2)", padding: "1px 6px", borderRadius: 4 }}>{byStage[stage].length}</span>
            </div>
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, padding: "2px 0" }}>
              {byStage[stage].map(t => (
                <div key={t.id} draggable onDragStart={() => setDrag(t.id)}
                  style={{
                    background: "var(--surface)", border: `1px solid ${STAGE_COLORS[stage]}30`,
                    borderLeft: `3px solid ${STAGE_COLORS[stage]}`,
                    borderRadius: "var(--r)", padding: "12px", cursor: "grab",
                  }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, color: "var(--text)" }}>
                    {t.title.slice(0, 50)}{t.title.length > 50 ? "…" : ""}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>{fmtBudget(t.budget_max, t.currency)} · {(t.portal || t.source || "UNKNOWN").toUpperCase()}</div>
                  {t.deadline && (
                    <div style={{ fontSize: 11, color: "var(--muted2)", marginTop: 4, fontFamily: "var(--mono)" }}>{fmtDate(t.deadline)}</div>
                  )}
                </div>
              ))}
              {byStage[stage].length === 0 && (
                <div style={{ border: "2px dashed var(--border)", borderRadius: "var(--r)", padding: 20, textAlign: "center", color: "var(--muted2)", fontSize: 12 }}>
                  Drop here
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Analytics View ────────────────────────────────────────────────
function AnalyticsView({ tenders }: { tenders: Tender[] }) {
  const byCountry = tenders.reduce((a, t) => {
    const loc = t.state_location || t.country || "India";
    a[loc] = (a[loc] || 0) + 1;
    return a;
  }, {} as Record<string, number>);

  const bySource = tenders.reduce((a, t) => {
    const src = (t.portal || t.source || "Unknown").toUpperCase();
    a[src] = (a[src] || 0) + 1;
    return a;
  }, {} as Record<string, number>);
  const totalBudget = tenders.reduce((a, t) => a + (t.budget_max || 0), 0);
  const avgScore = tenders.length ? Math.round(tenders.reduce((a, t) => a + (t.match_score || 72), 0) / tenders.length) : 0;
  const upcoming = tenders.filter(t => t.deadline && new Date(t.deadline).getTime() - Date.now() < 30 * 86400000).length;

  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      {/* KPI Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Total Tenders", value: tenders.length, color: "var(--accent2)", suffix: "" },
          { label: "Pipeline Value", value: fmtBudget(totalBudget), color: "var(--accent4)", suffix: "" },
          { label: "Avg Match Score", value: avgScore, color: "var(--accent)", suffix: "%" },
          { label: "Closing in 30d", value: upcoming, color: "var(--danger)", suffix: "" },
        ].map(k => (
          <div key={k.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: "20px 24px" }}>
            <div style={{ fontSize: 10, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 8 }}>{k.label}</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: k.color, fontFamily: "var(--mono)", lineHeight: 1 }}>
              {k.value}{k.suffix}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* By Country */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
          <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 16 }}>By Country</div>
          {Object.entries(byCountry).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([c, n]) => (
            <div key={c} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ width: 28, fontSize: 18 }}>{countryFlag(c)}</span>
              <span style={{ flex: 1, fontSize: 13, color: "var(--text)" }}>{c}</span>
              <div style={{ height: 6, background: "var(--border)", borderRadius: 3, flex: 2 }}>
                <div style={{ height: "100%", background: "var(--accent2)", borderRadius: 3, width: `${(n / Math.max(...Object.values(byCountry))) * 100}%` }} />
              </div>
              <span style={{ width: 24, textAlign: "right", fontSize: 13, color: "var(--muted)", fontFamily: "var(--mono)" }}>{n}</span>
            </div>
          ))}
        </div>

        {/* By Source */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 20 }}>
          <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 16 }}>By Source</div>
          {Object.entries(bySource).sort((a, b) => b[1] - a[1]).map(([s, n]) => (
            <div key={s} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ flex: 1, fontSize: 13, color: "var(--text)", fontFamily: "var(--mono)" }}>{s.replace("_", " ").toUpperCase()}</span>
              <div style={{ height: 6, background: "var(--border)", borderRadius: 3, flex: 2 }}>
                <div style={{ height: "100%", background: "var(--accent)", borderRadius: 3, width: `${(n / Math.max(...Object.values(bySource))) * 100}%` }} />
              </div>
              <span style={{ width: 24, textAlign: "right", fontSize: 13, color: "var(--muted)", fontFamily: "var(--mono)" }}>{n}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Settings View ─────────────────────────────────────────────────
function SettingsView() {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [models, setModels] = useState<Record<string, string[]>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get("/api/llm/current").then(setConfig);
    api.get("/api/llm/models").then(setModels);
  }, []);

  const save = async () => {
    setSaving(true);
    await api.post("/api/llm/switch", config);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const allModels = Object.values(models).flat();

  return (
    <div style={{ padding: 24, maxWidth: 640, overflowY: "auto", height: "100%" }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Settings</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {[
          { key: "fast_model", label: "Fast Model", hint: "Summarize, classify, chat" },
          { key: "quality_model", label: "Quality Model", hint: "Proposals, compliance" },
          { key: "vision_model", label: "Vision Model", hint: "Scanned PDF analysis" },
        ].map(f => (
          <div key={f.key} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{f.label}</div>
            <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>{f.hint}</div>
            <select
              value={config[f.key] || ""}
              onChange={e => setConfig(p => ({ ...p, [f.key]: e.target.value }))}
              style={{ fontFamily: "var(--mono)", fontSize: 12 }}
            >
              {allModels.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        ))}

        {/* Reranker */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Reranker</div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>Result reranking model</div>
          <select value={config.reranker || "bge"} onChange={e => setConfig(p => ({ ...p, reranker: e.target.value }))} style={{ fontFamily: "var(--mono)", fontSize: 12 }}>
            {["bge", "jina", "none"].map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        {/* Embedding */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r2)", padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Embedding Provider</div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>gemini = highest quality · local = free, offline</div>
          <select value={config.embedding || "local"} onChange={e => setConfig(p => ({ ...p, embedding: e.target.value }))} style={{ fontFamily: "var(--mono)", fontSize: 12 }}>
            {["gemini", "local"].map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        <button onClick={save} disabled={saving} style={{
          background: "var(--accent)", color: "#000", fontWeight: 700,
          padding: "12px 24px", borderRadius: "var(--r)", fontSize: 14,
          opacity: saving ? 0.6 : 1,
        }}>{saving ? "Saving…" : saved ? "✓ Saved" : "Save Changes"}</button>
      </div>
    </div>
  );
}

// ── Auth Views ────────────────────────────────────────────────────
function AuthView({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "", company_name: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setLoading(true);
    setError("");
    const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    const res = await api.post(path, form);
    if (res.access_token) {
      api.setToken(res.access_token);
      const user = await api.get("/api/users/me");
      onLogin(res.access_token, user);
    } else {
      setError(res.detail || "Failed");
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg)",
      backgroundImage: "radial-gradient(ellipse at 50% 0%, rgba(0,194,168,0.08) 0%, transparent 60%)",
    }}>
      <div style={{ width: "100%", maxWidth: 400, padding: 24 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 32, fontWeight: 800, letterSpacing: -1, marginBottom: 8 }}>
            Tender<span style={{ color: "var(--accent)" }}>AI</span>
          </div>
          <div style={{ color: "var(--muted)", fontSize: 14 }}>Procurement Intelligence Platform</div>
        </div>

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r3)", padding: 28 }}>
          <div style={{ display: "flex", marginBottom: 24, background: "var(--surface2)", borderRadius: "var(--r)", padding: 3 }}>
            {(["login", "register"] as const).map(m => (
              <button key={m} onClick={() => setMode(m)} style={{
                flex: 1, padding: "8px", borderRadius: "calc(var(--r) - 2px)",
                background: mode === m ? "var(--surface3)" : "transparent",
                color: mode === m ? "var(--text)" : "var(--muted)",
                fontWeight: mode === m ? 600 : 400, fontSize: 13, textTransform: "capitalize",
              }}>{m}</button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {mode === "register" && (
              <>
                <input placeholder="Full name" value={form.full_name} onChange={e => setForm(p => ({ ...p, full_name: e.target.value }))} />
                <input placeholder="Company name" value={form.company_name} onChange={e => setForm(p => ({ ...p, company_name: e.target.value }))} />
              </>
            )}
            <input placeholder="Email" type="email" value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
            <input placeholder="Password" type="password" value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} onKeyDown={e => e.key === "Enter" && submit()} />
            {error && <div style={{ color: "var(--danger)", fontSize: 13 }}>{error}</div>}
            <button onClick={submit} disabled={loading} style={{
              background: "var(--accent)", color: "#000", fontWeight: 700,
              padding: "12px", borderRadius: "var(--r)", fontSize: 14, marginTop: 4,
              opacity: loading ? 0.6 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}>
              {loading ? <><Spinner />{mode === "login" ? "Signing in…" : "Creating…"}</> : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </div>
        </div>

        <div style={{ textAlign: "center", marginTop: 20, fontSize: 12, color: "var(--muted2)" }}>
          TenderAI v2 · Concrete 3D Printing Intelligence
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState<User | null>({
    id: "dev_user_001",
    email: "dev@tenderai.local",
    full_name: "Dev Architect",
    company_name: "3D Concrete Tech",
    plan: "pro",
  });
  const [view, setView] = useState<View>("tenders");
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "error">("checking");
  // Filters
  const [filterState, setFilterState] = useState("");
  const [filterOrg, setFilterOrg] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterDeadline, setFilterDeadline] = useState("");
  const [showK6kOnly, setShowK6kOnly] = useState(false);

  // Check API + auth on mount
  useEffect(() => {
    fetch(`${API}/health`).then(r => r.ok ? setApiStatus("ok") : setApiStatus("error")).catch(() => setApiStatus("error"));
    if (api.token) {
      api.get("/api/users/me").then(u => { if (u.id) setUser(u); }).catch(() => { });
    }
  }, []);

  const fetchTenders = () => {
    if (!user) return;
    setLoading(true);
    api.get(`/api/tenders?size=50`).then(data => {
      setTenders(data.tenders || []);
      setLoading(false);
    }).catch(err => {
      console.error("Failed to fetch tenders:", err);
      setLoading(false);
    });
  };

  // Load tenders when authenticated
  useEffect(() => { fetchTenders(); }, [user]);

  const handleLogin = (_token: string, u: User) => setUser(u);
  const handleLogout = () => { api.setToken(""); setUser(null); };

  const triggerCrawl = async () => {
    setLoading(true);
    await api.post("/api/tenders/crawl/trigger", {});
    fetchTenders();
  };

  // Derived filter options
  const INDIAN_STATES = ["Andhra Pradesh","Delhi","Gujarat","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Punjab","Rajasthan","Tamil Nadu","Telangana","Uttar Pradesh","West Bengal"];
  const CATEGORIES = ["Construction 3D Printing","Additive Manufacturing","Infrastructure","Civil Works","Smart Cities","Defence","Railways","Equipment Supply","Robotics"];
  const CATEGORY_KEYWORDS: Record<string, string[]> = {
    "Construction 3D Printing": ["3d print", "3d-print", "concrete print", "extrusion", "additive construction", "contour craft"],
    "Additive Manufacturing": ["additive", "3d print", "3d-print", "prototyping", "layering"],
    "Infrastructure": ["infrastructure", "highway", "road", "bridge", "flyover", "dam", "building"],
    "Civil Works": ["civil", "construction", "masonry", "earthwork", "excavation", "renovation", "structure"],
    "Smart Cities": ["smart city", "smart cities", "iot", "urban development", "surveillance"],
    "Defence": ["defence", "defense", "military", "drdo", "ordnance", "army", "navy", "air force"],
    "Railways": ["railway", "rail", "metro", "irctc", "locomotive"],
    "Equipment Supply": ["supply", "procurement", "purchase", "equipment", "machinery", "hardware", "material"],
    "Robotics": ["robotic", "robot", "automation", "automated", "uav", "drone"],
  };
  const uniqueOrgs = [...new Set(tenders.map(t => t.organization).filter(Boolean))].slice(0, 30);

  const filteredTenders = tenders.filter(t => {
    if (search && !t.title.toLowerCase().includes(search.toLowerCase()) &&
        !t.organization?.toLowerCase().includes(search.toLowerCase()) &&
        !t.country?.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterState && !`${t.organization} ${t.overview || ""}`.toLowerCase().includes(filterState.toLowerCase())) return false;
    if (filterOrg && t.organization !== filterOrg) return false;
    if (filterCategory) {
      const txt = `${t.title} ${t.overview || ""} ${(t.industry_tags || []).join(" ")}`.toLowerCase();
      const keywords = CATEGORY_KEYWORDS[filterCategory] || [filterCategory];
      const hasMatch = keywords.some(k => txt.includes(k.toLowerCase()));
      if (!hasMatch) return false;
    }
    if (filterDeadline === "7d" && (!t.deadline || new Date(t.deadline).getTime() - Date.now() > 7 * 86400000)) return false;
    if (filterDeadline === "30d" && (!t.deadline || new Date(t.deadline).getTime() - Date.now() > 30 * 86400000)) return false;
    if (showK6kOnly && kelvin6kScore(t) < 20) return false;
    return true;
  });

  // Stats
  const k6kTenders = tenders.filter(t => kelvin6kScore(t) >= 20);
  const urgentCount = tenders.filter(t => t.deadline && new Date(t.deadline).getTime() - Date.now() < 7 * 86400000 && new Date(t.deadline).getTime() > Date.now()).length;

  if (!user) return <><style>{GLOBAL_CSS}</style><AuthView onLogin={handleLogin} /></>;

  const NAV = [
    { id: "tenders", label: "Tenders", icon: "◈" },
    { id: "crm", label: "CRM", icon: "⋮⋮" },
    { id: "analytics", label: "Analytics", icon: "◷" },
    { id: "settings", label: "Settings", icon: "⚙" },
  ] as const;

  return (
    <>
      <style>{GLOBAL_CSS}</style>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>

        {/* Top Nav */}
        <header style={{
          display: "flex", alignItems: "center", padding: "0 20px",
          borderBottom: "1px solid var(--border)", height: 52, flexShrink: 0,
          background: "var(--surface)", gap: 20,
        }}>
          <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.5, flexShrink: 0, display: "flex", alignItems: "center", gap: 8 }}>
            <img src={k6kLogo} alt="Kelvin6K TenderAI" style={{ height: 28, width: "auto", objectFit: "contain", borderRadius: "4px" }} />
            Tender<span style={{ color: "var(--accent)" }}>AI</span>
          </div>

          {/* Nav */}
          <nav style={{ display: "flex", gap: 2 }}>
            {NAV.map(n => (
              <button key={n.id} onClick={() => { setView(n.id as View); setSelectedTender(null); }} style={{
                background: view === n.id ? "var(--surface2)" : "transparent",
                color: view === n.id ? "var(--text)" : "var(--muted)",
                padding: "6px 14px", borderRadius: "var(--r)", fontSize: 13,
                fontWeight: view === n.id ? 600 : 400,
                border: view === n.id ? "1px solid var(--border)" : "1px solid transparent",
                display: "flex", alignItems: "center", gap: 6,
              }}>
                <span style={{ fontSize: 14 }}>{n.icon}</span> {n.label}
              </button>
            ))}
          </nav>

          {/* Search — only for tenders view */}
          {view === "tenders" && !selectedTender && (
            <div style={{ flex: 1, maxWidth: 360, position: "relative" }}>
              <input
                value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search tenders…"
                style={{ paddingLeft: 32, fontSize: 13 }}
              />
              <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--muted)", pointerEvents: "none" }}>⌕</span>
            </div>
          )}

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
            {/* API Status */}
            <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: apiStatus === "ok" ? "var(--accent)" : "var(--danger)", fontFamily: "var(--mono)" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: apiStatus === "ok" ? "var(--accent)" : "var(--danger)" }} className={apiStatus === "checking" ? "pulse" : ""} />
              API {apiStatus}
            </div>

            {/* Crawl */}
            <button onClick={triggerCrawl} style={{
              background: "transparent", border: "1px solid var(--border)",
              color: "var(--muted)", padding: "5px 10px", borderRadius: "var(--r)", fontSize: 12,
            }}>⟳ Crawl</button>

            {/* User */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#000" }}>
                {user.full_name?.[0]?.toUpperCase() || "U"}
              </div>
              <button onClick={handleLogout} style={{ background: "transparent", border: "none", color: "var(--muted)", fontSize: 12 }}>Logout</button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main style={{ flex: 1, overflow: "hidden", display: "flex" }}>

          {/* Tenders View */}
          {view === "tenders" && (
            selectedTender
              ? <div style={{ flex: 1, overflow: "hidden" }}><TenderDetail tender={selectedTender} onBack={() => setSelectedTender(null)} /></div>
              : (
                <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
                  {/* Stats bar */}
                  <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
                    {[
                      { label: "Total", value: tenders.length, color: "var(--text)" },
                      { label: "K6K Relevant", value: k6kTenders.length, color: "#FF6B35" },
                      { label: "Urgent", value: urgentCount, color: "var(--danger)" },
                    ].map(s => (
                      <div key={s.label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--r)", padding: "6px 12px", display: "flex", gap: 6, alignItems: "center" }}>
                        <span style={{ fontSize: 16, fontWeight: 700, color: s.color, fontFamily: "var(--mono)" }}>{s.value}</span>
                        <span style={{ fontSize: 11, color: "var(--muted)" }}>{s.label}</span>
                      </div>
                    ))}
                    {tenders.length === 0 && !loading && (
                      <div style={{ fontSize: 12, color: "var(--accent3)", background: "rgba(255,107,53,0.1)", border: "1px solid rgba(255,107,53,0.2)", padding: "4px 12px", borderRadius: "var(--r)" }}>
                        No tenders yet — click ⟳ Crawl
                      </div>
                    )}
                    <span style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--mono)", marginLeft: "auto" }}>{filteredTenders.length} shown</span>
                  </div>

                  {/* Filters */}
                  <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
                    <select value={filterState} onChange={e => setFilterState(e.target.value)} style={{ width: "auto", fontSize: 12, padding: "5px 10px" }}>
                      <option value="">All States</option>
                      {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <select value={filterOrg} onChange={e => setFilterOrg(e.target.value)} style={{ width: "auto", fontSize: 12, padding: "5px 10px", maxWidth: 180 }}>
                      <option value="">All Organizations</option>
                      {uniqueOrgs.map(o => <option key={o} value={o}>{o?.slice(0, 40)}</option>)}
                    </select>
                    <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)} style={{ width: "auto", fontSize: 12, padding: "5px 10px" }}>
                      <option value="">All Categories</option>
                      {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <select value={filterDeadline} onChange={e => setFilterDeadline(e.target.value)} style={{ width: "auto", fontSize: 12, padding: "5px 10px" }}>
                      <option value="">Any Deadline</option>
                      <option value="7d">Closing in 7 days</option>
                      <option value="30d">Closing in 30 days</option>
                    </select>
                    <button onClick={() => setShowK6kOnly(v => !v)} style={{
                      background: showK6kOnly ? "rgba(255,107,53,0.15)" : "var(--surface)",
                      border: `1px solid ${showK6kOnly ? "rgba(255,107,53,0.4)" : "var(--border)"}`,
                      color: showK6kOnly ? "#FF6B35" : "var(--muted)",
                      padding: "5px 10px", borderRadius: "var(--r)", fontSize: 12, fontWeight: showK6kOnly ? 600 : 400,
                    }}>⚡ K6K Only</button>
                    {(filterState || filterOrg || filterCategory || filterDeadline || showK6kOnly) && (
                      <button onClick={() => { setFilterState(""); setFilterOrg(""); setFilterCategory(""); setFilterDeadline(""); setShowK6kOnly(false); }}
                        style={{ background: "transparent", border: "none", color: "var(--muted)", fontSize: 12, padding: "5px 8px" }}>✕ Clear</button>
                    )}
                  </div>

                  {loading
                    ? <div style={{ display: "flex", justifyContent: "center", padding: 60 }}><Spinner /></div>
                    : (
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
                        {filteredTenders.map(t => (
                          <TenderCard key={t.id} tender={t} onClick={() => setSelectedTender(t)} />
                        ))}
                      </div>
                    )}

                  {!loading && filteredTenders.length === 0 && tenders.length > 0 && (
                    <div style={{ textAlign: "center", padding: 60, color: "var(--muted)" }}>
                      No tenders match "{search}"
                    </div>
                  )}
                </div>
              )
          )}

          {view === "crm" && <div style={{ flex: 1, overflow: "hidden" }}><CRMView tenders={tenders} /></div>}
          {view === "analytics" && <div style={{ flex: 1, overflow: "hidden" }}><AnalyticsView tenders={tenders} /></div>}
          {view === "settings" && <div style={{ flex: 1, overflow: "hidden" }}><SettingsView /></div>}
        </main>
      </div>
    </>
  );
}
