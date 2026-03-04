import { useState, useEffect } from 'react';
import type { FileData } from '../store/sessionStore';
import { useSessionStore } from '../store/sessionStore';



interface Props {
  files: Record<string, FileData>;
  activeFile: string | null;
  onSelectFile: (path: string) => void;
  onDownload: () => void;
}


/** Parse a Python source string and return all function/class definition names with line numbers and indentation level */
function parseEntries(source: string): Array<{ name: string; lineno: number; level: number }> {
  const lines = source.split('\n');
  const results: Array<{ name: string; lineno: number; level: number }> = [];
  lines.forEach((line, i) => {
    const m = line.match(/^(\s*)(?:(?:async\s+)?def\s+(\w+)|class\s+(\w+))/);
    if (m) {
      const indent = m[1].length;
      results.push({ name: m[2] || m[3], lineno: i + 1, level: indent });
    }
  });
  return results;
}

/** Scroll the visible code pane to show a given line */
function scrollCodePaneToLine(lineno: number) {
  // Try the documented pane first (generated files), fall back to source pane (pre-existing files)
  let rows = document.querySelectorAll<HTMLTableRowElement>('[data-documented-line]');
  let key: 'documentedLine' | 'sourceLine' = 'documentedLine';
  if (rows.length === 0) {
    rows = document.querySelectorAll<HTMLTableRowElement>('[data-source-line]');
    key = 'sourceLine';
  }
  for (const row of rows) {
    if (Number(row.dataset[key]) >= lineno) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
  }
}

export function FunctionNavigator({ files, activeFile, onSelectFile, onDownload }: Props) {
  const report = useSessionStore(state => state.report);

  // Sort files: undocumented (lower coverage) FIRST, fully-documented LAST
  // Edge cases: file not in perFile → treat as 100% (no functions, skip to bottom)
  const sortedFileKeys = Object.keys(files).sort((a, b) => {
    const statsA = report?.perFile?.find(f => f.file === a);
    const statsB = report?.perFile?.find(f => f.file === b);
    const covA = statsA ? statsA.coveragePct : 100;
    const covB = statsB ? statsB.coveragePct : 100;
    // Secondary sort: most undocumented count first
    if (covA !== covB) return covA - covB;
    const undocA = statsA ? statsA.total - statsA.documented : 0;
    const undocB = statsB ? statsB.total - statsB.documented : 0;
    return undocB - undocA;
  });

  const isMulti = sortedFileKeys.length > 1;

  // For multi-file: track which files have their function list expanded
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(() => new Set(activeFile ? [activeFile] : sortedFileKeys.slice(0, 1)));

  // When active file changes in multi mode, auto-expand it
  useEffect(() => {
    if (isMulti && activeFile) {
      setExpandedFiles(prev => new Set([...prev, activeFile]));
    }
  }, [activeFile, isMulti]);

  const toggleExpand = (fp: string) => {
    setExpandedFiles(prev => {
      const next = new Set(prev);
      if (next.has(fp)) next.delete(fp); else next.add(fp);
      return next;
    });
  };

  if (sortedFileKeys.length === 0) return null;

  return (
    <div style={{
      width: 220, flexShrink: 0,
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 20px',
        minHeight: 44,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 12, fontWeight: 600, letterSpacing: 0.8,
        color: 'var(--text-muted)', textTransform: 'uppercase',
        flexShrink: 0,
      }}>
        Navigator
      </div>

      {/* Dot legend */}
      <div style={{
        padding: '6px 14px 6px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', gap: 10, flexWrap: 'wrap', flexShrink: 0,
      }}>
        {([
          { color: '#059669', label: 'Generated' },
          { color: '#3b82f6', label: 'Pre-existing' },
          { color: '#d1d5db', label: 'Skipped' },
        ] as const).map(({ color, label }) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0 }} />
            <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{label}</span>
          </span>
        ))}
      </div>

      {/* Scrollable list — split into two labeled sections */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
        {(() => {
          const needsDocsKeys = sortedFileKeys.filter(fp => {
            const s = report?.perFile?.find(f => f.file === fp);
            return !s || s.coveragePct < 100;
          });
          const documentedKeys = sortedFileKeys.filter(fp => {
            const s = report?.perFile?.find(f => f.file === fp);
            return s && s.coveragePct === 100;
          });

          const SectionLabel = ({ label }: { label: string }) => (
            <div style={{
              padding: '6px 12px 4px',
              fontSize: 9, fontWeight: 700, letterSpacing: 1,
              textTransform: 'uppercase', color: 'var(--text-muted)',
              borderBottom: '1px solid var(--border)',
              marginTop: 4,
            }}>{label}</div>
          );

          const renderFile = (fp: string) => {
            const fileData = files[fp];
            if (!fileData) return null; // guard: file not yet loaded
            const filename = fp.split(/[/\\]/).pop() ?? fp;
            const isActive = fp === activeFile;
            const showEntries = !isMulti || expandedFiles.has(fp);

            const entries = parseEntries(fileData.documentedContent || fileData.originalContent);
            const docBlocks = findDocstringBlocks(fileData.documentedContent || '');

            // For accurate "new vs pre-existing" detection we compare against the
            // ORIGINAL source — this catches classes too, not just functions.
            const originalEntries = parseEntries(fileData.originalContent || '');
            const originalDocBlocks = findDocstringBlocks(fileData.originalContent || '');

            const undocumentedInFile = report?.undocumentedList.filter(u => u.file === fp) || [];

            const fileStats = report?.perFile?.find(f => f.file === fp);
            const fileCovPct = fileStats ? fileStats.coveragePct : (entries.length === 0 ? 100 : 0);
            const fileTotal = fileStats?.total ?? entries.length;
            const fileUndocCount = fileStats ? fileStats.total - fileStats.documented : undocumentedInFile.length;
            const isFullyDocumented = fileTotal === 0 || fileCovPct === 100;

            return (
              <div key={fp}>
                {/* File row */}
                <div style={{
                  display: 'flex', alignItems: 'center',
                  background: isActive ? '#fef3c7' : 'transparent',
                  borderLeft: isActive ? '2px solid #d97706' : isFullyDocumented ? '2px solid #10b981' : '2px solid #f59e0b',
                  transition: 'all 0.15s',
                }}>
                  <button
                    onClick={() => { onSelectFile(fp); if (isMulti) toggleExpand(fp); }}
                    style={{
                      flex: 1, textAlign: 'left',
                      padding: '6px 8px 6px 10px',
                      background: 'transparent', border: 'none', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 6, minWidth: 0,
                    }}
                  >
                    <span
                      title={isFullyDocumented ? 'All documented' : `${fileUndocCount} undocumented`}
                      style={{ fontSize: 11, flexShrink: 0, color: isFullyDocumented ? '#10b981' : '#f59e0b', fontWeight: 700 }}
                    >
                      {isFullyDocumented ? '✓' : '●'}
                    </span>
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: isActive ? '#d97706' : isFullyDocumented ? 'var(--text-muted)' : 'var(--text-primary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                    }}>
                      {filename}
                    </span>
                    {fileTotal > 0 && !isFullyDocumented && (
                      <span style={{
                        fontSize: 9, fontWeight: 700, flexShrink: 0,
                        padding: '1px 5px', borderRadius: 99,
                        background: '#fef3c7',
                        color: '#92400e',
                      }}>
                        {fileCovPct}%
                      </span>
                    )}
                  </button>
                  {isMulti && (
                    <button
                      onClick={() => toggleExpand(fp)}
                      style={{
                        padding: '4px 8px 4px 2px', background: 'transparent', border: 'none',
                        cursor: 'pointer', color: 'var(--text-muted)', fontSize: 10, flexShrink: 0,
                        lineHeight: 1, transition: 'transform 0.2s',
                        transform: showEntries ? 'rotate(0deg)' : 'rotate(-90deg)',
                      }}
                    >▾</button>
                  )}
                </div>

                {/* Function/class entries */}
                {showEntries && entries.map((entry, j) => {
                  const docBlock = docBlocks.find(b => b.start === entry.lineno + 1 || b.start === entry.lineno + 2);
                  const hasDoc = !!docBlock;

                  // Find this entry in the ORIGINAL file by name and check whether
                  // it already had a docstring on the line immediately following the
                  // def/class.  This is accurate for both functions AND classes, so
                  // no separate undocumentedList fallback is needed.
                  const origEntry = originalEntries.find(e => e.name === entry.name);
                  const hadDocOriginal = origEntry
                    ? originalDocBlocks.some(b =>
                        b.start === origEntry.lineno + 1 || b.start === origEntry.lineno + 2
                      )
                    : false;

                  // green = new docstring (engine generated it)
                  // blue  = pre-existing docstring (was already there, possibly updated in style)
                  // grey  = no docstring after generation (skipped by engine)
                  const isNew = hasDoc && !hadDocOriginal;
                  const isPreExisting = hasDoc && hadDocOriginal;
                  const dotColor = isNew ? '#059669' : isPreExisting ? '#3b82f6' : '#d1d5db';
                  const docStatusTitle = isNew ? 'Generated' : isPreExisting ? 'Pre-existing' : 'Skipped';

                  return (
                    <button
                      key={j}
                      onClick={() => { onSelectFile(fp); setTimeout(() => scrollCodePaneToLine(entry.lineno), 50); }}
                      title={`${entry.name} — line ${entry.lineno} (${docStatusTitle})`}
                      style={{
                        width: '100%', textAlign: 'left',
                        padding: `3px 14px 3px ${26 + entry.level * 4}px`,
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 6,
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: '50%', flexShrink: 0, background: dotColor }} />
                      <code style={{
                        fontSize: 11, color: 'var(--text-primary)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                      }}>
                        {entry.name}
                      </code>
                      <span style={{ fontSize: 9, color: 'var(--text-muted)', flexShrink: 0 }}>:{entry.lineno}</span>
                    </button>
                  );
                })}
              </div>
            );
          };

          return (
            <>
              {needsDocsKeys.length > 0 && (
                <>
                  {documentedKeys.length > 0 && <SectionLabel label="Generated" />}
                  {needsDocsKeys.map(renderFile)}
                </>
              )}
              {documentedKeys.length > 0 && (
                <>
                  <SectionLabel label="Pre-existing" />
                  {documentedKeys.map(renderFile)}
                </>
              )}
            </>
          );
        })()}
      </div>

      {/* Download button — pinned at bottom */}
      <div style={{ padding: '12px 14px 14px', flexShrink: 0, borderTop: '1px solid var(--border)' }}>
        <button onClick={onDownload} style={{
          width: '100%', padding: '10px 14px', borderRadius: 10, border: 'none',
          background: 'linear-gradient(135deg, #b45309, #d97706)',
          color: '#fff', fontWeight: 700, fontSize: 12.5, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          boxShadow: '0 2px 10px rgba(180,83,9,0.28)',
        }}>
          <span style={{ fontSize: 14 }}>↓</span> Download Project
        </button>
      </div>
    </div>
  );
}

// Reuse the same docstring block finder from WorkflowPage (kept inline to avoid circular deps)
function findDocstringBlocks(text: string): Array<{ start: number; end: number; content: string }> {
  const lines = text.split('\n');
  const blocks: Array<{ start: number; end: number; content: string }> = [];
  let i = 0;
  while (i < lines.length) {
    const stripped = lines[i].trimStart();
    if (stripped.startsWith('"""') || stripped.startsWith("'''")) {
      const quote = stripped.startsWith('"""') ? '"""' : "'''";
      const after = stripped.slice(3);
      if (after.includes(quote)) {
        blocks.push({ start: i + 1, end: i + 1, content: lines[i].trim() });
        i++; continue;
      }
      const blockStart = i + 1;
      let j = i + 1; let closed = false;
      while (j < lines.length) {
        if (lines[j].trimStart().startsWith(quote)) { closed = true; break; }
        j++;
      }
      blocks.push({ start: blockStart, end: closed ? j + 1 : lines.length, content: lines.slice(i, closed ? j + 1 : lines.length).join('\n').trim() });
      i = closed ? j + 1 : lines.length; continue;
    }
    i++;
  }
  return blocks;
}
