import { useEffect, useState } from 'react';
import type { AnalysisReport } from '../store/sessionStore';

function CoverageRing({ pct }: { pct: number }) {
  const r = 48;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 70 ? '#059669' : pct >= 40 ? '#d97706' : '#dc2626';

  return (
    <div style={{ position: 'relative', width: 116, height: 116, flexShrink: 0 }}>
      <svg width={116} height={116} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={58} cy={58} r={r} fill="none" stroke="var(--border)" strokeWidth={9} />
        <circle
          cx={58} cy={58} r={r} fill="none"
          stroke={color} strokeWidth={9}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 1.2s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: 20, fontWeight: 700, color }}>{pct}%</span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: 0.5 }}>covered</span>
      </div>
    </div>
  );
}

function BarRow({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const [width, setWidth] = useState(0);
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  useEffect(() => { setTimeout(() => setWidth(pct), 80); }, [pct]);

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>
          {value} <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>/ {max}</span>
        </span>
      </div>
      <div style={{ height: 7, background: 'var(--border)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 99, background: color,
          width: `${width}%`, transition: 'width 1s ease',
        }} />
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)', 
      borderRadius: 12,
      border: '1px solid var(--border)',
      boxShadow: 'var(--shadow-sm)',
      padding: '16px 20px', flex: 1, minWidth: 120,
    }}>
      <div style={{ fontSize: 28, fontWeight: 800, color: color || 'var(--text-primary)', marginBottom: 4, lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{sub}</div>}
    </div>
  );
}

interface Props { report: AnalysisReport; compact?: boolean; }

export function CoverageReport({ report, compact = false }: Props) {
  const wrapperStyle = compact
    ? { padding: 0, margin: 0, maxWidth: '100%' }
    : { maxWidth: 860, margin: '0 auto', padding: '28px 20px' };

  return (
    <div style={wrapperStyle}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
          Documentation Coverage Report
        </h2>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Static analysis complete —{' '}
          {report.undocumented > 0
            ? `${report.undocumented} function${report.undocumented > 1 ? 's' : ''} require documentation`
            : 'All functions are already documented'}
        </p>
      </div>

      {/* Summary card */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: 12,
        border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)',
        padding: '24px 32px', marginBottom: 16,
        display: 'flex', gap: 32, alignItems: 'center', flexWrap: 'wrap',
      }}>
        <CoverageRing pct={report.coveragePct} />
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 16 }}>
            Coverage Breakdown
          </div>
          <BarRow label="Documented functions" value={report.documented} max={report.totalFunctions} color="#059669" />
          <BarRow label="Missing parameter docs" value={report.missingParams} max={report.totalFunctions} color="#d97706" />
          <BarRow label="Missing return type docs" value={report.missingReturns} max={report.totalFunctions} color="#7c3aed" />
        </div>
      </div>

      {/* Stat grid */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
        <StatCard label="Total Functions" value={report.totalFunctions} />
        <StatCard label="Documented" value={report.documented} color="#059669" />
        <StatCard label="Undocumented" value={report.undocumented} color="#dc2626" sub="Pending Generation" />
        <StatCard label="Missing Params" value={report.missingParams} color="#d97706" />
        <StatCard label="Missing Returns" value={report.missingReturns} color="#7c3aed" />
      </div>

      {/* Undocumented list */}
      {report.undocumentedList.length > 0 && (
        <div style={{
          background: 'var(--bg-card)', borderRadius: 12,
          border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', overflow: 'hidden',
        }}>
          <div style={{
            padding: '16px 20px', borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', gap: 8, background: 'var(--bg-surface)'
          }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
              Functions Pending Documentation
            </span>
            <span style={{
              background: '#fef2f2', color: '#dc2626',
              borderRadius: 999, padding: '1px 8px', fontSize: 11, fontWeight: 600,
            }}>{report.undocumentedList.length}</span>
          </div>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {report.undocumentedList.map((item, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center',
                padding: '9px 18px', gap: 10,
                borderBottom: i < report.undocumentedList.length - 1 ? '1px solid var(--border-light)' : 'none',
              }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#dc2626', flexShrink: 0 }} />
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-primary)', flex: 1 }}>
                  {item.name}
                </code>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {item.file.split(/[/\\]/).pop()} :{item.lineno}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
