import type { Phase } from '../store/sessionStore';

const steps: { phase: Phase; label: string; num: number }[] = [
  { num: 1, phase: 'idle',       label: 'Upload'   },
  { num: 2, phase: 'analyzed',   label: 'Inspect'  },
  { num: 3, phase: 'generating', label: 'Generate' },
  { num: 4, phase: 'done',       label: 'Review'   },
];

function phaseToStepIndex(phase: Phase): number {
  if (phase === 'idle' || phase === 'analyzing') return 1;
  if (phase === 'analyzed') return 2;
  if (phase === 'generating') return 3;
  return 4;
}

interface Props {
  phase: Phase;
  onDownload?: () => void;
  onReset?: () => void;
  onTabClick?: (phase: Phase) => void;
  primaryActionLabel?: string;
  onPrimaryAction?: () => void;
  primaryDisabled?: boolean;
}

export function PhaseHeader({
  phase,
  onDownload,
  onReset,
  onTabClick,
  primaryActionLabel,
  onPrimaryAction,
  primaryDisabled,
}: Props) {
  const current  = phaseToStepIndex(phase);
  const isLoading = phase === 'analyzing' || phase === 'generating';
  const isDone    = phase === 'done';

  return (
    <header style={{
      background: 'var(--bg-card)',
      borderBottom: '1px solid var(--border)',
      padding: '0 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: 52,
      position: 'sticky',
      top: 0,
      zIndex: 100,
      gap: 12,
      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'linear-gradient(135deg, #b45309, #d97706)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: 13,
        }}>D</div>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
          DocGen
        </span>
      </div>

      {/* Steps breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
        {steps.map((step, i) => {
          const isActive = current === step.num;
          const isDoneStep = current > step.num;
          return (
            <div key={step.num} style={{ display: 'flex', alignItems: 'center' }}>
              <button
                onClick={() => onTabClick && onTabClick(step.phase as Phase)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '4px 12px', borderRadius: 999,
                  background: isActive ? 'rgba(217,119,6,0.18)' : 'transparent',
                  border: isActive ? '1.5px solid #d97706' : '1.5px solid transparent',
                  cursor: onTabClick ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{
                  width: 18, height: 18, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700,
                  background: isDoneStep ? '#059669' : isActive ? '#b45309' : 'var(--border)',
                  color: isDoneStep || isActive ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.2s ease',
                }}>
                  {isDoneStep ? '✓' : step.num}
                </div>
                <span style={{
                  fontSize: 12, fontWeight: isActive ? 600 : 500,
                  color: isDoneStep ? '#059669' : isActive ? '#d97706' : 'var(--text-muted)',
                }}>
                  {step.label}
                </span>
              </button>
              {i < steps.length - 1 && (
                <div style={{ width: 18, height: 1.5, background: isDoneStep ? '#059669' : 'var(--border)', margin: '0 1px' }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Right actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        {/* Cancel button during loading */}
        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {onReset && (
              <button onClick={onReset} style={{
                padding: '5px 14px', borderRadius: 8,
                border: 'none',
                background: 'linear-gradient(135deg, #b45309, #d97706)',
                color: '#fff',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 5,
                boxShadow: '0 2px 8px rgba(180,83,9,0.28)',
                transition: 'opacity 0.15s, box-shadow 0.15s',
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.88'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 3px 12px rgba(180,83,9,0.42)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 2px 8px rgba(180,83,9,0.28)'; }}
              >
                <span style={{ fontSize: 11, lineHeight: 1 }}>×</span> Cancel
              </button>
            )}
          </div>
        )}

        {primaryActionLabel && onPrimaryAction && (
          <button onClick={onPrimaryAction} disabled={primaryDisabled} style={{
            padding: '6px 16px', borderRadius: 8, border: 'none',
            background: primaryDisabled ? 'var(--border)' : 'linear-gradient(135deg, #b45309, #d97706)',
            color: primaryDisabled ? 'var(--text-muted)' : '#fff',
            fontSize: 12, fontWeight: 600,
            cursor: primaryDisabled ? 'not-allowed' : 'pointer',
            boxShadow: primaryDisabled ? 'none' : '0 2px 8px rgba(180,83,9,0.25)',
          }}>
            {primaryActionLabel}
          </button>
        )}

        {/* New Upload button on analyzed/inspect phase */}
        {phase === 'analyzed' && onReset && (
          <button onClick={onReset} style={{
            padding: '5px 14px', borderRadius: 8,
            border: 'none',
            background: 'linear-gradient(135deg, #b45309, #d97706)',
            color: '#fff',
            fontSize: 12, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 5,
            boxShadow: '0 2px 8px rgba(180,83,9,0.28)',
            transition: 'opacity 0.15s, box-shadow 0.15s',
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '0.88'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 3px 12px rgba(180,83,9,0.42)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = '1'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 2px 8px rgba(180,83,9,0.28)'; }}
          >
            <span style={{ fontSize: 13 }}>↑</span> New Upload
          </button>
        )}

        {/* Back-compat download button (if still used) */}
        {isDone && onDownload && !primaryActionLabel && (
          <button onClick={onDownload} style={{
            padding: '6px 16px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, #b45309, #d97706)',
            color: '#fff', fontSize: 12, fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(180,83,9,0.25)',
          }}>
            ↓ Download
          </button>
        )}

        {/* New Upload button on done phase */}
        {isDone && onReset && !onDownload && !primaryActionLabel && (
          <button onClick={onReset} style={{
            padding: '7px 18px', borderRadius: 8, border: 'none',
            background: 'linear-gradient(135deg, #b45309, #d97706)',
            color: '#fff', fontSize: 13, fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(180,83,9,0.35)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span style={{ fontSize: 14 }}>↑</span> New Upload
          </button>
        )}
      </div>
    </header>
  );
}
