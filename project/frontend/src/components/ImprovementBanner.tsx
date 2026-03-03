interface Props {
  before: number;
  after: number;
  added: number;
  qualityScore?: number;
}

export function ImprovementBanner({ before, after, added, qualityScore = 100 }: Props) {
  const delta = after - before;

  // Quality badge colour
  const qColor = qualityScore >= 90 ? '#059669'
    : qualityScore >= 70 ? '#d97706'
    : '#dc2626';
  const qBg = qualityScore >= 90 ? '#ecfdf5'
    : qualityScore >= 70 ? '#fffbeb'
    : '#fef2f2';
  const qLabel = qualityScore >= 90 ? 'Excellent'
    : qualityScore >= 70 ? 'Good'
    : 'Needs review';

  return (
    <div style={{
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border)',
      padding: '16px 20px',
      display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 20,
    }}>
      {/* Left side: Success Message */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: '#ecfdf5', color: '#059669',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24, flexShrink: 0, border: '1px solid #a7f3d0'
        }}>
          ✓
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--text-primary)', letterSpacing: '-0.3px', marginBottom: 2 }}>
            Documentation Complete
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Successfully generated <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{added}</span> new docstrings across all files
          </div>
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right side: Stats Dashboard */}
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 16 }}>
        
        {/* Coverage Stat */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '12px 20px',
          display: 'flex', alignItems: 'center', gap: 16,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
              Coverage
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-secondary)' }}>{before}%</span>
              <span style={{ fontSize: 16, color: '#059669' }}>→</span>
              <span style={{ fontSize: 24, fontWeight: 800, color: '#059669' }}>{after}%</span>
            </div>
          </div>
          <div style={{
            background: '#ecfdf5', color: '#059669',
            padding: '4px 8px', borderRadius: 6,
            fontSize: 12, fontWeight: 700
          }}>
            +{delta.toFixed(0)}%
          </div>
        </div>

        {/* Quality Score Stat */}
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '12px 20px',
          display: 'flex', alignItems: 'center', gap: 16,
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>
              Quality Score
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: qColor }}>{qualityScore}</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>/ 100</span>
            </div>
          </div>
          <div style={{
            background: qBg, color: qColor, border: `1px solid ${qColor}30`,
            padding: '4px 8px', borderRadius: 6,
            fontSize: 12, fontWeight: 700
          }}>
            {qLabel}
          </div>
        </div>

      </div>
    </div>
  );
}
