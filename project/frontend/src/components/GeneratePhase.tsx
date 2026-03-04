import { useEffect, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';

interface Props {
  fileCount: number;
  filePaths: string[];
}

interface LogLine {
  text: string;
  type: 'info' | 'success' | 'dim' | 'accent';
}

function buildLogSequences(useAI: boolean): LogLine[][] {
  return [
    [
      { text: 'Initialising generation session…', type: 'dim' },
      useAI
        ? { text: 'Connecting to Groq API…', type: 'dim' }
        : { text: 'Template-only mode active…', type: 'dim' },
      useAI
        ? { text: 'Template + AI generation ready. Starting analysis…', type: 'info' }
        : { text: 'Template generation ready. Starting analysis…', type: 'info' },
    ],
    [
      { text: 'Parsing Python AST…', type: 'info' },
      { text: 'Identified function definitions', type: 'dim' },
      { text: 'Building call graph…', type: 'dim' },
    ],
    [
      useAI
        ? { text: 'Generating docstrings via Template + AI…', type: 'accent' }
        : { text: 'Generating docstrings via Template…', type: 'accent' },
      { text: 'Inferring parameter types from usage', type: 'dim' },
      { text: 'Inferring return types from annotations', type: 'dim' },
      { text: 'Writing documentation…', type: 'info' },
    ],
    [
      { text: 'Patching source files…', type: 'accent' },
      { text: 'Validating output syntax…', type: 'dim' },
      useAI
        ? { text: '✓ All files patched successfully (Template + AI)', type: 'success' }
        : { text: '✓ All files patched successfully (Template only)', type: 'success' },
      { text: 'Preview ready.', type: 'success' },
    ],
  ];
}

export function GeneratePhase({ fileCount, filePaths }: Props) {
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [step, setStep] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);
  const report = useSessionStore(state => state.report);
  const docstringStyle = useSessionStore(state => state.docstringStyle);
  const llmProvider = useSessionStore(state => state.llmProvider);
  const useAI = llmProvider === 'local' || llmProvider === 'gemini';
  const LOG_SEQUENCES = buildLogSequences(useAI);
  const styleLabel = docstringStyle.charAt(0).toUpperCase() + docstringStyle.slice(1);
  const styleColors: Record<string, { text: string; bg: string; border: string }> = {
    google: { text: '#b45309', bg: '#fffbeb', border: '#fcd34d' },
    numpy: { text: '#1d4ed8', bg: '#eff6ff', border: '#bfdbfe' },
    rest: { text: '#047857', bg: '#ecfdf5', border: '#a7f3d0' },
    epytext: { text: '#6d28d9', bg: '#f5f3ff', border: '#ddd6fe' },
    sphinx: { text: '#0f766e', bg: '#f0fdfa', border: '#99f6e4' },
  };
  const styleBadge = styleColors[docstringStyle] ?? styleColors.google;

  // Sort files: undocumented (needs docs) FIRST, fully-documented (skipped) LAST
  const sortedFilePaths = [...filePaths].sort((a, b) => {
    const statsA = report?.perFile?.find(f => f.file === a);
    const statsB = report?.perFile?.find(f => f.file === b);
    const covA = statsA ? statsA.coveragePct : 0;
    const covB = statsB ? statsB.coveragePct : 0;
    return covA - covB; // lower coverage → first
  });

  useEffect(() => {
    let cancelled = false;
    let logIndex = 0;
    let seqIndex = 0;

    const scheduleNext = (delay: number) => {
      if (cancelled) return;
      setTimeout(() => {
        if (cancelled) return;
        if (seqIndex < LOG_SEQUENCES.length) {
          const seq = LOG_SEQUENCES[seqIndex];
          if (logIndex < seq.length) {
            const entry = seq[logIndex]; // capture NOW before increment
            logIndex++;
            if (entry) setLogs(prev => [...prev, entry]);
          } else {
            seqIndex++;
            logIndex = 0;
            setStep(prev => Math.min(prev + 1, 3));
          }
          scheduleNext(220);
        }
      }, delay);
    };

    scheduleNext(300);
    return () => { cancelled = true; };
  }, []);

  // Add file-specific logs — only for files that actually need generation
  useEffect(() => {
    if (sortedFilePaths.length === 0) return;
    const pathsToProcess = sortedFilePaths.filter(fp => {
      const s = report?.perFile?.find(f => f.file === fp);
      return !s || s.coveragePct < 100;
    });
    const timer = setTimeout(() => {
      pathsToProcess.slice(0, 6).forEach((fp, i) => {
        setTimeout(() => {
          const name = fp.split(/[/\\]/).pop() ?? fp;
          setLogs(prev => [...prev, { text: `Processing ${name}…`, type: 'accent' }]);
        }, i * 320);
      });
    }, 900);
    return () => clearTimeout(timer);
  }, [sortedFilePaths.length]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  const logDot = (type: LogLine['type']) => {
    if (type === 'success') return '#059669';
    if (type === 'accent')  return '#d97706';
    if (type === 'info')    return '#3b82f6';
    return '#9ca3af';  // clearly visible grey for dim entries
  };
  const logTextColor = (type: LogLine['type']) => {
    if (type === 'success') return '#059669';
    if (type === 'accent')  return '#92400e';
    if (type === 'info')    return 'var(--text-primary)';
    return 'var(--text-muted)';
  };

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden', background: 'var(--bg-page)' }}>

      {/* ── Left panel: file list ─────────────────────────────────────────────*/}
      <div style={{
        width: 220, flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 2 }}>
            Files
          </div>
          {(() => {
            const needsGen = sortedFilePaths.filter(fp => {
              const s = report?.perFile?.find(f => f.file === fp);
              return !s || s.coveragePct < 100;
            }).length;
            const skipped = sortedFilePaths.length - needsGen;
            return (
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {needsGen} queued
                {skipped > 0 && <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--text-muted)' }}>· {skipped} skipped</span>}
              </div>
            );
          })()}
        </div>

        {/* File list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          {sortedFilePaths.length === 0 ? (
            <div style={{ padding: '12px 20px', fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
              Loading…
            </div>
          ) : (
            sortedFilePaths.map((fp) => {
              const name = fp.split(/[/\\]/).pop() ?? fp;
              const fileStats = report?.perFile?.find(f => f.file === fp);
              const isFullyDocumented = fileStats ? fileStats.coveragePct === 100 : false;
              const undocCount = fileStats ? fileStats.total - fileStats.documented : null;
              const nonSkippedPaths = sortedFilePaths.filter(p => {
                const s = report?.perFile?.find(f => f.file === p);
                return !s || s.coveragePct < 100;
              });
              const nonSkippedIndex = nonSkippedPaths.indexOf(fp);
              const processed = !isFullyDocumented && nonSkippedIndex >= 0 &&
                nonSkippedIndex < step * Math.ceil(nonSkippedPaths.length / 4);

              return (
                <div key={fp} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 16px',
                  opacity: isFullyDocumented ? 0.45 : 1,
                  borderBottom: '1px solid var(--border-light)',
                }}>
                  {/* Status dot / check */}
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: isFullyDocumented ? '#e5e7eb' : processed ? '#dcfce7' : '#fef9c3',
                    border: `1.5px solid ${isFullyDocumented ? '#d1d5db' : processed ? '#86efac' : '#fcd34d'}`,
                  }}>
                    <span style={{
                      fontSize: 8, fontWeight: 800,
                      color: isFullyDocumented ? '#9ca3af' : processed ? '#16a34a' : '#d97706',
                      lineHeight: 1,
                    }}>
                      {isFullyDocumented ? '–' : processed ? '✓' : '○'}
                    </span>
                  </div>
                  <code style={{
                    fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
                    color: isFullyDocumented ? 'var(--text-muted)' : 'var(--text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                  }}>{name}</code>
                  {isFullyDocumented ? (
                    <span style={{
                      fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 99,
                      background: '#f3f4f6', color: '#9ca3af', flexShrink: 0,
                      border: '1px solid #e5e7eb',
                    }}>skip</span>
                  ) : undocCount !== null ? (
                    <span style={{
                      fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 99,
                      background: '#fef3c7', color: '#92400e', flexShrink: 0,
                      border: '1px solid #fcd34d',
                    }}>{undocCount}</span>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── Right panel: activity log ─────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '28px 32px' }}>

        {/* Title */}
        <div style={{ flexShrink: 0, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: -0.3 }}>
            Generating docstrings
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, color: styleBadge.text,
            background: styleBadge.bg, border: `1px solid ${styleBadge.border}`,
            padding: '3px 10px', borderRadius: 99, flexShrink: 0,
            letterSpacing: 0.3,
          }}>
            {styleLabel}
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            · This may take a moment
          </span>
        </div>

        {/* Activity log card */}
        <div style={{
          flex: 1, minHeight: 0,
          background: '#ffffff', border: '1px solid var(--border)',
          borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column',
          boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
        }}>
          {/* Card header */}
          <div style={{
            padding: '11px 20px', borderBottom: '1px solid var(--border)',
            background: '#f9fafb', flexShrink: 0,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8 }}>
              Activity Log
            </span>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
              {fileCount} file{fileCount !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Log entries */}
          <div ref={logRef} style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
            {logs.filter(Boolean).map((line, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '7px 20px',
                borderBottom: '1px solid #f3f4f6',
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: logDot(line.type),
                  boxShadow: line.type !== 'dim' ? `0 0 0 2px ${logDot(line.type)}33` : 'none',
                }} />
                <span style={{
                  fontSize: 12.5, lineHeight: '20px',
                  color: logTextColor(line.type),
                  fontWeight: line.type === 'success' || line.type === 'accent' ? 600 : 400,
                }}>{line.text}</span>
              </div>
            ))}

            {/* Typing indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '10px 20px' }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: '#d97706',
                  animation: `logPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes logPulse { 0%,80%,100%{opacity:0.15;transform:scale(0.75);} 40%{opacity:0.9;transform:scale(1);} }
      `}</style>
    </div>
  );
}
