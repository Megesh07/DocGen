import { useEffect, useState } from 'react';
import type { AnalysisReport } from '../store/sessionStore';
import { useSessionStore } from '../store/sessionStore';
import type { ScanFunction } from '../apiClient';

interface Props {
  report: AnalysisReport;
  onGenerate: () => void;
  functions: ScanFunction[];
}

// ── Animated horizontal bar ───────────────────────────────────────────────────
function HBar({ pct, color, height = 8 }: { pct: number; color: string; height?: number }) {
  const [w, setW] = useState(0);
  useEffect(() => { setTimeout(() => setW(pct), 100); }, [pct]);
  return (
    <div style={{ height, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
      <div style={{
        height: '100%', borderRadius: 99, background: color,
        width: `${w}%`, transition: 'width 0.9s ease',
      }} />
    </div>
  );
}

// ── Coverage color helper ─────────────────────────────────────────────────────
function covColor(pct: number) {
  return pct >= 70 ? '#059669' : pct >= 40 ? '#d97706' : '#dc2626';
}

// ── Large animated coverage ring ─────────────────────────────────────────────
const RING_GRAD: Record<string, [string, string]> = {
  '#059669': ['#34d399', '#059669'],
  '#d97706': ['#fbbf24', '#b45309'],
  '#dc2626': ['#f87171', '#dc2626'],
};
function CoverageRing({ pct, documented, total }: { pct: number; documented: number; total: number }) {
  const size = 148;
  const cx = size / 2;
  const r = 58;
  const circ = 2 * Math.PI * r;
  const [filled, setFilled] = useState(0);
  useEffect(() => { setTimeout(() => setFilled(pct), 150); }, [pct]);
  const color = covColor(pct);
  const [g0, g1] = RING_GRAD[color] ?? ['#34d399', '#059669'];
  const offset = circ * (1 - filled / 100);
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      {/* Glow halo */}
      <div style={{
        position: 'absolute', inset: 12, borderRadius: '50%',
        boxShadow: `0 0 0 4px ${color}18, 0 0 28px ${color}30`,
        animation: 'ringHalo 2.8s ease-in-out infinite',
      }} />
      <svg width={size} height={size} style={{ position: 'relative', transform: 'rotate(-90deg)' }}>
        <defs>
          <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={g0} />
            <stop offset="100%" stopColor={g1} />
          </linearGradient>
        </defs>
        {/* Track */}
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--border)" strokeWidth={11} />
        {/* Filled arc — animates via dashoffset */}
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="url(#ringGrad)" strokeWidth={11}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1.3s cubic-bezier(0.34,1.2,0.64,1)' }}
        />
      </svg>
      {/* Center label */}
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2, textAlign: 'center' }}>
        <span style={{ fontSize: 28, fontWeight: 900, color, lineHeight: '28px', letterSpacing: -1 }}>{pct}%</span>
        <span style={{ fontSize: 8.5, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: 1.4, textTransform: 'uppercase' }}>Coverage</span>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>{documented}/{total}</span>
      </div>
    </div>
  );
}

// ── Mini ring for file drill-down ────────────────────────────────────────
function MiniRing({ pct }: { pct: number }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const [filled, setFilled] = useState(0);
  useEffect(() => { setTimeout(() => setFilled(pct), 80); }, [pct]);
  const color = covColor(pct);
  return (
    <div style={{ position: 'relative', width: 72, height: 72, flexShrink: 0 }}>
      <svg width={72} height={72} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={36} cy={36} r={r} fill="none" stroke="var(--border)" strokeWidth={7} />
        <circle cx={36} cy={36} r={r} fill="none" stroke={color} strokeWidth={7}
          strokeDasharray={`${(filled / 100) * circ} ${circ}`} strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.9s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
        <span style={{ fontSize: 14, fontWeight: 800, color, lineHeight: '14px' }}>{pct}%</span>
      </div>
    </div>
  );
}
export function AnalyzePhase({ report, onGenerate, functions }: Props) {
  const store = useSessionStore();
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  // Bar animation state — must live at component level (Rules of Hooks)
  const docPct   = report.totalFunctions > 0 ? (report.documented   / report.totalFunctions) * 100 : 0;
  const undocPct = report.totalFunctions > 0 ? (report.undocumented / report.totalFunctions) * 100 : 0;
  const [barDoc,   setBarDoc]   = useState(0);
  const [barUndoc, setBarUndoc] = useState(0);
  useEffect(() => { const t = setTimeout(() => { setBarDoc(docPct); setBarUndoc(undocPct); }, 250); return () => clearTimeout(t); }, [docPct, undocPct]);

  // Build a lookup: file path → functions list for drill-down
  const fnsByFile = new Map<string, ScanFunction[]>();
  functions.forEach(f => {
    const arr = fnsByFile.get(f.file) ?? [];
    arr.push(f);
    fnsByFile.set(f.file, arr);
  });

  const styles = [
    { id: 'google',  label: 'Google',  hint: 'Args: / Returns:' },
    { id: 'numpy',   label: 'NumPy',   hint: 'Parameters ------' },
    { id: 'rest',    label: 'reST',    hint: ':param x: ...' },
    { id: 'epytext', label: 'Epytext', hint: '@param x ...' },
    { id: 'sphinx',  label: 'Sphinx',  hint: ':param x: / :type:' },
  ] as const;

  const stylePreviews: Record<string, string> = {
    google:  `def process_data(items, config):\n    """Process a list of items using config.\n\n    Args:\n        items (list): Items to process.\n        config (dict): Processing configuration.\n\n    Returns:\n        list: Processed results.\n    """`,
    numpy:   `def process_data(items, config):\n    """Process a list of items using config.\n\n    Parameters\n    ----------\n    items : list\n        Items to process.\n    config : dict\n        Processing configuration.\n\n    Returns\n    -------\n    list\n        Processed results.\n    """`,
    rest:    `def process_data(items, config):\n    """Process a list of items using config.\n\n    :param items: Items to process.\n    :type items: list\n    :param config: Processing configuration.\n    :type config: dict\n    :returns: Processed results.\n    :rtype: list\n    """`,
    epytext: `def process_data(items, config):\n    """Process a list of items using config.\n\n    @param items: Items to process.\n    @type  items: list\n    @param config: Processing configuration.\n    @type  config: dict\n    @return: Processed results.\n    @rtype:  list\n    """`,
    sphinx:  `def process_data(items, config):\n    """Process a list of items using config.\n\n    :param list items: Items to process.\n    :param dict config: Processing configuration.\n    :returns: Processed results.\n    :rtype: list\n    """`,
  };

  const ready = report.undocumented > 0;
  const activePreview = stylePreviews[store.docstringStyle] ?? stylePreviews['google'];

  // Inject keyframes for ring glow animation
  useEffect(() => {
    if (document.getElementById('adg-ring-styles')) return;
    const el = document.createElement('style');
    el.id = 'adg-ring-styles';
    el.textContent = `
      @keyframes ringHalo {
        0%, 100% { opacity: 0.45; transform: scale(1); }
        50%       { opacity: 1;    transform: scale(1.04); }
      }
    `;
    document.head.appendChild(el);
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Left sidebar: settings only ───────────────────────────────────── */}
      <div style={{
        width: 256, flexShrink: 0,
        background: 'var(--bg-surface)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8 }}>
            Docstring Style
          </div>
        </div>

        {/* Style selector — fixed height */}
        <div style={{ padding: '12px 16px 0', flexShrink: 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {styles.map(s => {
              const active = store.docstringStyle === s.id;
              return (
                <button key={s.id} onClick={() => store.setDocstringStyle(s.id)} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 12px', borderRadius: 9, cursor: 'pointer', textAlign: 'left',
                  border: active ? '1.5px solid #d97706' : '1.5px solid var(--border)',
                  background: active ? '#fffbeb' : 'var(--bg-card)',
                  transition: 'all 0.15s',
                }}>
                  <div style={{
                    width: 13, height: 13, borderRadius: '50%', flexShrink: 0,
                    border: `2px solid ${active ? '#d97706' : 'var(--border)'}`,
                    background: active ? '#d97706' : 'transparent',
                    transition: 'all 0.15s',
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? '#b45309' : 'var(--text-primary)' }}>
                      {s.label}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                      {s.hint}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Preview + queue info + generate — single flex column fills remaining space */}
        <div style={{ flex: 1, padding: '10px 16px 16px', display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0 }}>

          {/* Preview card — fixed height, does not stretch */}
          <div style={{ flexShrink: 0, borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', maxHeight: 200 }}>
            <div style={{
              padding: '5px 10px', background: '#1a1814', flexShrink: 0,
              display: 'flex', alignItems: 'center', gap: 5,
            }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ff5f56', flexShrink: 0 }} />
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#ffbd2e', flexShrink: 0 }} />
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#27c93f', flexShrink: 0 }} />
              <span style={{ fontSize: 9.5, color: '#555', marginLeft: 3, fontFamily: 'JetBrains Mono, monospace' }}>
                preview.py
              </span>
            </div>
            <pre style={{
              margin: 0, padding: '10px 12px',
              fontSize: 9, lineHeight: 1.6,
              fontFamily: 'JetBrains Mono, monospace',
              background: '#1e1c18', color: '#c9b98a',
              overflow: 'auto', whiteSpace: 'pre',
            }}>{activePreview}</pre>
          </div>

          {/* Generate button */}
          <button onClick={onGenerate} disabled={!ready} style={{
            width: '100%', padding: '11px 16px', borderRadius: 10,
            background: ready ? 'linear-gradient(135deg, #b45309, #d97706)' : 'var(--border)',
            color: ready ? '#fff' : 'var(--text-muted)',
            border: 'none', fontWeight: 700, fontSize: 13,
            cursor: ready ? 'pointer' : 'not-allowed',
            boxShadow: ready ? '0 2px 12px rgba(180,83,9,0.30)' : 'none',
            transition: 'all 0.2s',
          }}>
            {ready ? 'Generate Docstrings' : 'Nothing to Generate'}
          </button>


        </div>
      </div>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '22px 28px', background: 'var(--bg-page)' }}>

        {/* Page title */}
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: -0.4 }}>
            Static Analysis Report
          </h2>
        </div>

        {/* ── Overview card ──────────────────────────────────────────────── */}
        {(() => {
          const ringColor = covColor(report.coveragePct);
          const tint = ringColor === '#059669' ? '#f0fdf4' : ringColor === '#d97706' ? '#fffbeb' : '#fff5f5';
          return (
            <div style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 16, marginBottom: 18, overflow: 'hidden',
              display: 'flex',
            }}>
              {/* Left panel — ring */}
              <div style={{
                padding: '24px 20px',
                background: tint,
                borderRight: '1px solid var(--border)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                minWidth: 164,
              }}>
                <CoverageRing pct={report.coveragePct} documented={report.documented} total={report.totalFunctions} />
              </div>

              {/* Right panel — breakdown */}
              <div style={{ flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>

                {/* Header row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Documentation breakdown</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {report.totalFunctions} functions total · {report.totalFiles} file{report.totalFiles !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Big count row */}
                <div style={{ display: 'flex', gap: 0, marginBottom: 14 }}>
                  <div style={{
                    flex: 1, borderRadius: '10px 0 0 10px', background: '#f0fdf4',
                    border: '1px solid #d1fae5', padding: '10px 14px',
                    display: 'flex', flexDirection: 'column', gap: 2,
                  }}>
                    <span style={{ fontSize: 30, fontWeight: 900, color: '#059669', lineHeight: 1, letterSpacing: -1 }}>{report.documented}</span>
                    <span style={{ fontSize: 11, color: '#059669', fontWeight: 600 }}>documented</span>
                  </div>
                  <div style={{
                    flex: 1, borderRadius: '0 10px 10px 0', background: '#fff5f5',
                    border: '1px solid #fecaca', borderLeft: 'none', padding: '10px 14px',
                    display: 'flex', flexDirection: 'column', gap: 2,
                  }}>
                    <span style={{ fontSize: 30, fontWeight: 900, color: '#dc2626', lineHeight: 1, letterSpacing: -1 }}>{report.undocumented}</span>
                    <span style={{ fontSize: 11, color: '#dc2626', fontWeight: 600 }}>need docstrings</span>
                  </div>
                </div>

                {/* Stacked gradient bar */}
                <div style={{ marginBottom: 14 }}>
                  <div style={{ height: 10, borderRadius: 99, background: 'var(--border)', overflow: 'hidden', display: 'flex' }}>
                    <div style={{
                      width: `${barDoc}%`, height: '100%',
                      background: 'linear-gradient(90deg, #34d399, #059669)',
                      transition: 'width 1.2s cubic-bezier(0.34,1.2,0.64,1)',
                    }} />
                    <div style={{
                      width: `${barUndoc}%`, height: '100%',
                      background: 'linear-gradient(90deg, #f87171, #dc2626)',
                      transition: 'width 1.2s cubic-bezier(0.34,1.2,0.64,1) 0.06s',
                    }} />
                  </div>
                </div>

                {/* Stat pills */}
                <div style={{ display: 'flex', gap: 8 }}>
                  {[
                    { label: 'Missing params',  value: report.missingParams,
                      color: report.missingParams  === 0 ? '#059669' : '#d97706',
                      bg:    report.missingParams  === 0 ? '#f0fdf4' : '#fffbeb',
                      border:report.missingParams  === 0 ? '#d1fae5' : '#fed7aa' },
                    { label: 'Missing returns', value: report.missingReturns,
                      color: report.missingReturns === 0 ? '#059669' : '#7c3aed',
                      bg:    report.missingReturns === 0 ? '#f0fdf4' : '#f5f3ff',
                      border:report.missingReturns === 0 ? '#d1fae5' : '#ddd6fe' },
                  ].map(s => (
                    <div key={s.label} style={{
                      flex: 1, background: s.bg, borderRadius: 9, padding: '8px 12px',
                      border: `1px solid ${s.border}`,
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <span style={{ fontSize: 22, fontWeight: 900, color: s.color, lineHeight: 1 }}>{s.value}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.3 }}>{s.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {/* ── Row 2: Per-file coverage chart ─────────────────────────────── */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 14, overflow: 'hidden', marginBottom: 18,
        }}>
          <div style={{
            padding: '12px 20px', borderBottom: '1px solid var(--border)',
            background: 'var(--bg-surface)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Coverage by File</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>sorted by worst coverage first</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 10, color: 'var(--text-muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: '#059669', display: 'inline-block' }} /> ≥70%
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: '#d97706', display: 'inline-block' }} /> 40–69%
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: '#dc2626', display: 'inline-block' }} /> &lt;40%
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {report.perFile.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: '16px 20px' }}>No files detected</div>
            ) : report.perFile.map((f, idx) => {
              const name = f.file.split(/[/\\]/).pop() ?? f.file;
              const color = covColor(f.coveragePct);
              const isExpanded = expandedFile === f.file;
              const fileFns = fnsByFile.get(f.file) ?? [];
                      // Use the style-aware `skipped` flag (backend sets this via
                      // is_style_match + is_complete for the currently selected style).
                      // Never use raw docstring presence — that is style-blind.
                      const docFns   = fileFns.filter(fn => fn.skipped);
                      const undocFns = fileFns.filter(fn => !fn.skipped);
              return (
                <div key={f.file} style={{ borderBottom: idx < report.perFile.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  {/* Clickable file row */}
                  <div
                    onClick={() => setExpandedFile(isExpanded ? null : f.file)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '12px 20px', cursor: 'pointer',
                      background: isExpanded ? '#fafaf8' : 'transparent',
                      transition: 'background 0.15s',
                    }}
                  >
                    <span style={{ fontSize: 12 }}>🐍</span>
                    <code style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: '#b45309', fontWeight: 600 }}>
                      {name}
                    </code>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                      {f.documented}/{f.total} documented
                    </span>
                    <div style={{ flex: 1, margin: '0 10px' }}>
                      <HBar pct={f.coveragePct} color={color} height={5} />
                    </div>
                    <span style={{
                      fontSize: 11, fontWeight: 700, color,
                      background: f.coveragePct >= 70 ? '#f0fdf4' : f.coveragePct >= 40 ? '#fffbeb' : '#fef2f2',
                      padding: '2px 7px', borderRadius: 5, minWidth: 36, textAlign: 'center',
                    }}>{f.coveragePct}%</span>
                    <span style={{
                      fontSize: 10, color: isExpanded ? '#b45309' : 'var(--text-muted)',
                      transform: isExpanded ? 'rotate(180deg)' : 'none',
                      transition: 'transform 0.2s',
                      display: 'inline-block', lineHeight: 1,
                    }}>▼</span>
                  </div>

                  {/* Expandable drill-down */}
                  {isExpanded && (
                    <div style={{
                      borderTop: '1px solid var(--border)',
                      background: 'var(--bg-page)',
                      padding: '16px 20px 18px',
                      display: 'flex', gap: 24, alignItems: 'flex-start',
                    }}>
                      {/* Ring */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                        <MiniRing pct={f.coveragePct} />
                        <span style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center' }}>
                          {f.documented}/{f.total}<br />functions
                        </span>
                      </div>

                      {/* Function list */}
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0 }}>
                        {undocFns.length > 0 && (
                          <div style={{ marginBottom: 8 }}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#dc2626', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 4 }}>
                              Needs documentation ({undocFns.length})
                            </div>
                            {undocFns.map(fn => (
                              <div key={fn.function + fn.lineno} style={{
                                display: 'flex', alignItems: 'center', gap: 7,
                                padding: '4px 0', borderBottom: '1px solid var(--border)',
                              }}>
                                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
                                <code style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-primary)', flex: 1 }}>
                                  {fn.function}
                                </code>
                                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                                  :{fn.lineno}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                        {docFns.length > 0 && (
                          <div>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#059669', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 4 }}>
                              Documented ({docFns.length})
                            </div>
                            {docFns.map(fn => (
                              <div key={fn.function + fn.lineno} style={{
                                display: 'flex', alignItems: 'center', gap: 7,
                                padding: '4px 0', borderBottom: '1px solid var(--border)',
                              }}>
                                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#059669', flexShrink: 0 }} />
                                <code style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-secondary)', flex: 1 }}>
                                  {fn.function}
                                </code>
                                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                                  :{fn.lineno}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
