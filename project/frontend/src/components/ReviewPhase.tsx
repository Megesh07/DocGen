import { useEffect, useRef, useState } from 'react';
import type { FileData } from '../store/sessionStore';
import { useSessionStore } from '../store/sessionStore';
import { ComparisonViewer } from './ComparisonViewer';
import { FunctionNavigator } from './FunctionNavigator';

// ── tiny animated bar ──────────────────────────────────────────────────────────
function CovBar({ pct, color, height = 6 }: { pct: number; color: string; height?: number }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(Math.min(pct, 100)), 120); return () => clearTimeout(t); }, [pct]);
  return (
    <div style={{ height, borderRadius: 99, background: 'var(--border)', overflow: 'hidden', width: '100%' }}>
      <div style={{ height: '100%', borderRadius: 99, background: color, width: `${w}%`, transition: 'width 1.1s cubic-bezier(0.34,1.2,0.64,1)' }} />
    </div>
  );
}

// ── SVG ring ──────────────────────────────────────────────────────────────────
function Ring({ pct, color, size = 80 }: { pct: number; color: string; size?: number }) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const [filled, setFilled] = useState(0);
  useEffect(() => { const t = setTimeout(() => setFilled(pct), 200); return () => clearTimeout(t); }, [pct]);
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth={9} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={9}
        strokeDasharray={circ} strokeDashoffset={circ * (1 - filled / 100)}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34,1.2,0.64,1)' }}
      />
    </svg>
  );
}

function covColor(pct: number) {
  return pct >= 70 ? '#059669' : pct >= 40 ? '#d97706' : '#c2410c';
}

interface Props {
  files: Record<string, FileData>;
  activeFile: string | null;
  onSelectFile: (path: string) => void;
  before: number;
  after: number;
  added: number;
  qualityScore: number;
  onDownload: () => void;
}

export function ReviewPhase({
  files, activeFile, onSelectFile,
  before, after, added, qualityScore, onDownload,
}: Props) {
  const activeData = activeFile ? files[activeFile] : null;
  const delta = Math.min(after, 100) - before;
  const [expanded, setExpanded] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const report = useSessionStore(state => state.report);
  const docstringStyle = useSessionStore(state => state.docstringStyle);
  const styleLabel = docstringStyle.charAt(0).toUpperCase() + docstringStyle.slice(1);
  const styleColors: Record<string, { text: string; bg: string; border: string }> = {
    google: { text: '#b45309', bg: '#fffbeb', border: '#fcd34d' },
    numpy: { text: '#1d4ed8', bg: '#eff6ff', border: '#bfdbfe' },
    rest: { text: '#047857', bg: '#ecfdf5', border: '#a7f3d0' },
    epytext: { text: '#6d28d9', bg: '#f5f3ff', border: '#ddd6fe' },
    sphinx: { text: '#0f766e', bg: '#f0fdfa', border: '#99f6e4' },
  };
  const styleBadge = styleColors[docstringStyle] ?? styleColors.google;
  const activeFileStats = activeFile ? report?.perFile?.find(f => f.file === activeFile) : null;
  const isPreDocumented = activeFileStats ? activeFileStats.coveragePct === 100 : false;

  const afterClamped = Math.min(after, 100);
  const qColor = qualityScore >= 90 ? '#059669' : qualityScore >= 70 ? '#d97706' : '#c2410c';

  // Derived post-generation stats
  const totalFns   = report?.totalFunctions ?? 0;
  const beforeDoc  = report?.documented ?? 0;
  const afterDoc   = Math.min(beforeDoc + added, totalFns);
  const afterUndoc = Math.max(totalFns - afterDoc, 0);
  const totalFiles = report?.totalFiles ?? Object.keys(files).length;
  // A file is truly "updated by AI" only if it had generatedRanges AND was not already 100% covered
  const perFileCovMap = Object.fromEntries((report?.perFile ?? []).map(f => [f.file, f.coveragePct]));
  const generatedFilesCount = Object.entries(files).filter(
    ([path, f]) => f.generatedRanges.length > 0 && (perFileCovMap[path] ?? 100) < 100
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Collapsed summary bar ────────────────────────────────────────────── */}
      <div style={{
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderBottom: expanded ? 'none' : '1px solid var(--border)',
        padding: '9px 20px',
        display: 'flex', alignItems: 'center', gap: 14,
      }}>
        {/* ✓ badge */}
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg,#34d399,#059669)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, color: '#fff', fontWeight: 900,
          boxShadow: '0 1px 6px rgba(5,150,105,0.28)',
        }}>✓</div>

        {/* Before pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6 }}>Before</span>
          <span style={{ fontSize: 15, fontWeight: 800, color: covColor(before), letterSpacing: -0.3 }}>{before}%</span>
        </div>

        <span style={{ fontSize: 13, color: 'var(--border)', fontWeight: 300 }}>→</span>

        {/* After pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6 }}>After</span>
          <span style={{ fontSize: 15, fontWeight: 800, color: covColor(afterClamped), letterSpacing: -0.3 }}>{afterClamped}%</span>
        </div>

        {/* Delta badge */}
        <span style={{
          fontSize: 11, fontWeight: 800, color: '#059669',
          background: 'rgba(5,150,105,0.1)', border: '1px solid rgba(5,150,105,0.25)',
          padding: '2px 8px', borderRadius: 99,
        }}>+{delta.toFixed(0)}%</span>

        {/* Mini progress bar */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{added} docstrings added · {generatedFilesCount} files updated</span>
            <span style={{ fontSize: 9, color: qColor, fontWeight: 700 }}>Quality {qualityScore} — {qualityScore >= 90 ? 'Excellent' : qualityScore >= 70 ? 'Good' : 'Fair'}</span>
          </div>
          <div style={{ position: 'relative', height: 6, borderRadius: 99, background: 'var(--border)', overflow: 'hidden' }}>
            {/* Before layer */}
            <div style={{ position: 'absolute', inset: 0, borderRadius: 99, background: covColor(before), width: `${before}%`, opacity: 0.35 }} />
            {/* After layer animated */}
            <CovBar pct={afterClamped} color={covColor(afterClamped)} height={6} />
          </div>
        </div>

        {/* Style label */}
        <span style={{
          fontSize: 10, fontWeight: 700, color: styleBadge.text,
          background: styleBadge.bg, border: `1px solid ${styleBadge.border}`,
          padding: '3px 8px', borderRadius: 99, flexShrink: 0,
        }}>
          {styleLabel} style
        </span>

        {/* Expand button */}
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            flexShrink: 0, display: 'flex', alignItems: 'center', gap: 5,
            padding: '5px 14px', borderRadius: 8,
            border: `1.5px solid ${expanded ? '#d97706' : '#c9b99a'}`,
            background: expanded ? '#fffbeb' : 'var(--bg-card)',
            color: expanded ? '#92400e' : 'var(--text-secondary)',
            fontSize: 11, fontWeight: 700, cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          <span>Coverage Report</span>
          <span style={{ display: 'inline-block', transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▾</span>
        </button>
      </div>

      {/* ── Expandable detailed report ───────────────────────────────────────── */}
      <div
        ref={panelRef}
        style={{
          flexShrink: 0,
          overflow: 'hidden',
          maxHeight: expanded ? 500 : 0,
          transition: 'max-height 0.35s cubic-bezier(0.4,0,0.2,1)',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-page)',
        }}
      >
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', maxHeight: 500 }}>

          {/* ── Row 1: Before | arrow | After (each shrink-wraps its own content) ── */}
          <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>

            {/* Before card */}
            <div style={{ flex: 1, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '9px 16px', background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8 }}>Before</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{totalFns} fn · {before}% covered</span>
              </div>
              <div style={{ padding: '12px 16px', background: '#fdfcf9', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <Ring pct={before} color={covColor(before)} size={76} />
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                      <span style={{ fontSize: 16, fontWeight: 900, color: covColor(before), lineHeight: '16px' }}>{before}%</span>
                    </div>
                  </div>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <div style={{ flex: 1, background: '#f0fdf4', border: '1px solid #d1fae5', borderRadius: 8, padding: '6px 10px' }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: '#059669', lineHeight: 1 }}>{beforeDoc}</div>
                        <div style={{ fontSize: 10, color: '#059669', fontWeight: 600 }}>had docs</div>
                      </div>
                      <div style={{ flex: 1, background: '#fff5f5', border: '1px solid #fecaca', borderRadius: 8, padding: '6px 10px' }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: '#c2410c', lineHeight: 1 }}>{report?.undocumented ?? 0}</div>
                        <div style={{ fontSize: 10, color: '#c2410c', fontWeight: 600 }}>undocumented</div>
                      </div>
                    </div>
                    <CovBar pct={before} color={covColor(before)} height={7} />
                  </div>
                </div>
                {/* Per-file list — Before */}
                {(report?.perFile ?? []).length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 2 }}>
                    {(report?.perFile ?? []).map(f => {
                      const name = f.file.split(/[/\\]/).pop() ?? f.file;
                      const bc = covColor(f.coveragePct);
                      return (
                        <div key={f.file} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <code style={{ fontSize: 10, fontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace", color: '#b45309', width: 120, flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</code>
                          <div style={{ flex: 1 }}><CovBar pct={f.coveragePct} color={bc} height={5} /></div>
                          <span style={{ fontSize: 10, fontWeight: 700, color: bc, width: 28, textAlign: 'right', flexShrink: 0 }}>{f.coveragePct}%</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Centre arrow */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 5, flexShrink: 0, paddingTop: 36 }}>
              <span style={{ fontSize: 20, color: '#059669', fontWeight: 900 }}>→</span>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#059669', background: 'rgba(5,150,105,0.1)', border: '1px solid rgba(5,150,105,0.25)', padding: '3px 9px', borderRadius: 99, whiteSpace: 'nowrap' }}>+{delta.toFixed(0)}%</span>
            </div>

            {/* After card */}
            <div style={{ flex: 1, background: 'var(--bg-card)', border: '1px solid #d1fae5', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '9px 16px', background: '#f0fdf4', borderBottom: '1px solid #d1fae5', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#059669', textTransform: 'uppercase', letterSpacing: 0.8 }}>After</span>
                <span style={{ fontSize: 11, color: '#059669', fontWeight: 600 }}>+{added} added · {afterClamped}% ↑</span>
              </div>
              <div style={{ padding: '12px 16px', background: 'rgba(5,150,105,0.03)', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <Ring pct={afterClamped} color={covColor(afterClamped)} size={76} />
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
                      <span style={{ fontSize: 16, fontWeight: 900, color: covColor(afterClamped), lineHeight: '16px' }}>{afterClamped}%</span>
                    </div>
                  </div>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <div style={{ flex: 1, background: '#f0fdf4', border: '1px solid #d1fae5', borderRadius: 8, padding: '6px 10px' }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: '#059669', lineHeight: 1 }}>{afterDoc}</div>
                        <div style={{ fontSize: 10, color: '#059669', fontWeight: 600 }}>now covered</div>
                      </div>
                      <div style={{ flex: 1, background: afterUndoc === 0 ? '#f0fdf4' : '#fff5f5', border: `1px solid ${afterUndoc === 0 ? '#d1fae5' : '#fecaca'}`, borderRadius: 8, padding: '6px 10px' }}>
                        <div style={{ fontSize: 20, fontWeight: 900, color: afterUndoc === 0 ? '#059669' : '#c2410c', lineHeight: 1 }}>{afterUndoc === 0 ? '✓' : afterUndoc}</div>
                        <div style={{ fontSize: 10, color: afterUndoc === 0 ? '#059669' : '#c2410c', fontWeight: 600 }}>{afterUndoc === 0 ? 'all done' : 'still missing'}</div>
                      </div>
                    </div>
                    <CovBar pct={afterClamped} color={covColor(afterClamped)} height={7} />
                  </div>
                </div>
                {/* Per-file list — After */}
                {(report?.perFile ?? []).length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 2 }}>
                    {(report?.perFile ?? []).map(f => {
                      const name = f.file.split(/[/\\]/).pop() ?? f.file;
                      const wasGenerated = (files[f.file]?.generatedRanges.length ?? 0) > 0;
                      const afterPct = wasGenerated ? 100 : f.coveragePct;
                      return (
                        <div key={f.file} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <code style={{ fontSize: 10, fontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace", color: '#059669', width: 120, flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</code>
                          <div style={{ flex: 1 }}><CovBar pct={afterPct} color='#059669' height={5} /></div>
                          {wasGenerated
                            ? <span style={{ fontSize: 8, fontWeight: 700, color: '#059669', background: 'rgba(5,150,105,0.12)', border: '1px solid rgba(5,150,105,0.3)', borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>AI</span>
                            : <span style={{ fontSize: 10, fontWeight: 700, color: '#059669', width: 28, textAlign: 'right', flexShrink: 0 }}>{afterPct}%</span>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Stats strip ─── */}
          <div style={{ display: 'flex', gap: 10 }}>
            {[
              { label: 'Added',     value: added,                           color: '#b45309',                                                bg: '#fffbeb', border: '#fcd34d' },
              { label: 'Updated',   value: generatedFilesCount,             color: '#b45309',                                                bg: '#fffbeb', border: '#fcd34d' },
              { label: 'Skipped',   value: totalFiles - generatedFilesCount, color: 'var(--text-muted)',                                     bg: 'var(--bg-surface)', border: 'var(--border)' },
              { label: qualityScore >= 90 ? 'Excellent' : qualityScore >= 70 ? 'Good' : 'Fair', value: qualityScore, color: qColor,          bg: qColor === '#059669' ? '#f0fdf4' : '#fffbeb', border: qColor === '#059669' ? '#d1fae5' : '#fcd34d' },
              { label: 'Functions', value: totalFns,                        color: 'var(--text-accent)',                                     bg: 'var(--bg-surface)', border: 'var(--border)' },
            ].map(s => (
              <div key={s.label} style={{
                flex: 1, background: s.bg, border: `1px solid ${s.border}`,
                borderRadius: 10, padding: '10px 14px',
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: s.color, lineHeight: 1, flexShrink: 0 }}>{s.value}</div>
                <div style={{ fontSize: 10, color: s.color, fontWeight: 700, lineHeight: 1.4 }}>{s.label}</div>
              </div>
            ))}
          </div>

        </div>
      </div>

      {/* ── 3-panel workspace ───────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>
        <FunctionNavigator files={files} activeFile={activeFile} onSelectFile={onSelectFile} onDownload={onDownload} />
        <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
          {activeData ? (
            <ComparisonViewer
              originalContent={activeData.originalContent}
              documentedContent={activeData.documentedContent}
              generatedRanges={activeData.generatedRanges}
              isPreDocumented={isPreDocumented}
            />
          ) : (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', flexDirection: 'column', gap: 8, color: 'var(--text-muted)',
            }}>
              <span style={{ fontSize: 28 }}>📄</span>
              <span style={{ fontSize: 13 }}>Select a file from the navigator</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
