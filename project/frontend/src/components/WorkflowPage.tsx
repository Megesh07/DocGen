import type { FileData, LineRange, AnalysisReport } from '../store/sessionStore';
import { useSessionStore } from '../store/sessionStore';
import { apiClient } from '../apiClient';
import type { ScanFunction } from '../apiClient';
import { PhaseHeader } from './PhaseHeader';
import { UploadPhase } from './UploadPhase';
import { AnalyzePhase } from './AnalyzePhase';
import { GeneratePhase } from './GeneratePhase';
import { ReviewPhase } from './ReviewPhase';

// ── diff helper: compute line ranges added in documented vs original ──────────
/**
 * Find all triple-quoted docstring blocks in a Python source text.
 * Returns each block's 1-indexed [start, end] line range and its trimmed content.
 */
function findDocstringBlocks(text: string): Array<{ start: number; end: number; content: string }> {
  const lines = text.split('\n');
  const blocks: Array<{ start: number; end: number; content: string }> = [];

  let i = 0;
  while (i < lines.length) {
    const stripped = lines[i].trimStart();

    // Must look like a solo docstring opener (not inside an expression)
    if (stripped.startsWith('"""') || stripped.startsWith("'''")) {
      const quote = stripped.startsWith('"""') ? '"""' : "'''";
      const after = stripped.slice(3);

      if (after.includes(quote)) {
        // Single-line docstring: """text"""
        blocks.push({ start: i + 1, end: i + 1, content: lines[i].trim() });
        i++;
        continue;
      }

      // Multi-line: scan forward for the closing quotes
      const blockStart = i + 1; // 1-indexed
      let j = i + 1;
      let closed = false;
      while (j < lines.length) {
        if (lines[j].trimStart().startsWith(quote)) {
          closed = true;
          break;
        }
        j++;
      }

      const blockEnd = closed ? j + 1 : lines.length; // 1-indexed inclusive end
      const content = lines.slice(i, closed ? j + 1 : lines.length).join('\n').trim();
      blocks.push({ start: blockStart, end: blockEnd, content });
      i = closed ? j + 1 : lines.length;
      continue;
    }

    i++;
  }

  return blocks;
}

/**
 * Compute which line ranges in `documented` are NEW docstring blocks vs `original`.
 * Only highlights genuinely new triple-quoted docstring blocks, never code lines.
 */
function computeHighlightRanges(original: string, documented: string): LineRange[] {
  const origBlocks = findDocstringBlocks(original);
  const docBlocks  = findDocstringBlocks(documented);

  // Build a set of original docstring contents so we can skip pre-existing ones
  const origContentSet = new Set(origBlocks.map(b => b.content));

  const ranges: LineRange[] = [];
  for (const block of docBlocks) {
    if (!origContentSet.has(block.content)) {
      ranges.push({ start: block.start, end: block.end });
    }
  }

  return ranges;
}


// ── build AnalysisReport from scan response ───────────────────────────────────
function buildReport(functions: ScanFunction[]): AnalysisReport {
  const total = functions.length;

  // A function is "documented" only when the backend's style-aware check passed.
  // f.skipped === true  →  docstring exists AND matches the chosen style AND is
  //                        complete (all params + Returns section if needed).
  // f.skipped === false →  needs a new docstring (missing, wrong style, partial).
  const documented = functions.filter(f => f.skipped).length;
  const undocumented = total - documented;
  const coveragePct = total > 0 ? Math.round((documented / total) * 100) : 100;

  // Functions that need docs AND have typed params / return annotations
  // (used as secondary "richness" metrics — not the primary coverage number).
  const missingParams = functions.filter(f => !f.skipped && f.signature?.includes(':')).length;
  const missingReturns = functions.filter(f => !f.skipped && f.signature?.includes('->')).length;
  const qualityScore = Math.min(100, Math.round(coveragePct * 0.8 + (documented > 0 ? 20 : 0)));

  // undocumentedList: every function that still needs a docstring
  const undocumentedList = functions
    .filter(f => !f.skipped)
    .map(f => ({ name: f.function, file: f.file, lineno: f.lineno }));

  // Per-file breakdown — use the same style-aware skipped flag
  const fileMap = new Map<string, { total: number; documented: number }>();
  functions.forEach(f => {
    const key = f.file;
    const entry = fileMap.get(key) ?? { total: 0, documented: 0 };
    entry.total++;
    // Count as documented only when the style check passed
    if (f.skipped) entry.documented++;
    fileMap.set(key, entry);
  });
  const perFile = Array.from(fileMap.entries())
    .map(([file, s]) => ({
      file,
      total: s.total,
      documented: s.documented,
      coveragePct: s.total > 0 ? Math.round((s.documented / s.total) * 100) : 100,
    }))
    .sort((a, b) => a.coveragePct - b.coveragePct); // worst coverage first

  // AST-detected enrichments (driven by the signature string from the backend)
  const withReturnAnnotation = functions.filter(f => f.signature?.includes('->')).length;
  const withParams = functions.filter(f => {
    const sig = f.signature ?? '';
    const inner = sig.slice(sig.indexOf('(') + 1, sig.lastIndexOf(')'));
    const stripped = inner.replace(/self\s*,?\s*/, '').trim();
    return stripped.length > 0;
  }).length;
  const skipped = functions.filter(f => f.skipped).length;
  const totalFiles = fileMap.size;

  return {
    totalFunctions: total, documented, undocumented, coveragePct,
    missingParams, missingReturns, qualityScore, undocumentedList,
    perFile, withReturnAnnotation, withParams, skipped, totalFiles,
  };
}

// ── WorkflowPage ─────────────────────────────────────────────────────────────
import { useEffect, useState } from 'react';

export function WorkflowPage() {
  const store = useSessionStore();
  const { phase, sessionId, report, files, activeFile, docstringsAdded, coverageBefore, coverageAfter } = store;
  const [rawFunctions, setRawFunctions] = useState<ScanFunction[]>([]);

  useEffect(() => {
    if (phase !== 'analyzed' || !sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const rescan = await apiClient.rescan(sessionId, store.docstringStyle);
        if (cancelled) return;
        const rpt = buildReport(rescan.functions);
        store.setReport(rpt);
        setRawFunctions(rescan.functions);
      } catch (err: any) {
        if (cancelled) return;
        store.setError(err.message || 'Rescan failed');
      }
    })();
    return () => { cancelled = true; };
  }, [phase, sessionId, store.docstringStyle]);

  // ── PHASE ACTIONS ──────────────────────────────────────────────────────────

  const handleFiles = async (uploadedFiles: File[]) => {
    store.startAnalyzing();
    try {
      const res = await apiClient.uploadProject(uploadedFiles as any, store.docstringStyle);
      const rpt = buildReport(res.functions);
      setRawFunctions(res.functions);
      // Sort file paths: undocumented (lower coverage) FIRST, fully-documented LAST
      const filePaths = Array.from(new Set(res.functions.map(f => f.file))).sort((a, b) => {
        const statsA = rpt.perFile.find(p => p.file === a);
        const statsB = rpt.perFile.find(p => p.file === b);
        const covA = statsA ? statsA.coveragePct : 100;
        const covB = statsB ? statsB.coveragePct : 100;
        return covA - covB;
      });
      store.setAnalysisComplete(res.session_id, res.session_dir, rpt, filePaths);
    } catch (err: any) {
      store.setError(err.message || 'Upload failed');
    }
  };

  const handleGenerate = async () => {
    // Always read fresh state — avoids stale closure bugs with multiple files
        const { sessionId, sessionDir, files, llmProvider, docstringStyle,
          startGenerating, setGenerationComplete, setError, setReport } = useSessionStore.getState();

    if (!sessionId || !sessionDir) return;
    try {
      const rescan = await apiClient.rescan(sessionId, docstringStyle);
      const rpt = buildReport(rescan.functions);
      setReport(rpt);
      setRawFunctions(rescan.functions);
    } catch (err: any) {
      useSessionStore.getState().setErrorOnly(err.message || 'Rescan failed');
      return;
    }
    startGenerating();
    try {
      const genSummary = await apiClient.generateAll(sessionId, llmProvider, docstringStyle);

      const filePaths = Object.keys(files);

      // Fetch all file previews — sequentially to avoid overloading the backend
      const newFiles: Record<string, FileData> = {};
      for (const fp of filePaths) {
        try {
          const [orig, prev] = await Promise.all([
            apiClient.getFileSource(sessionId, fp),
            apiClient.previewFile(sessionId, fp),
          ]);
          const ranges = computeHighlightRanges(orig.content, prev.content);
          newFiles[fp] = {
            path: fp,
            originalContent: orig.content,
            documentedContent: prev.content,
            generatedRanges: ranges,
          };
        } catch {
          // File preview failed — include it with empty content so UI still loads
          newFiles[fp] = {
            path: fp,
            originalContent: '# Could not load original source',
            documentedContent: '# Could not load preview',
            generatedRanges: [],
          };
        }
      }

      // Get coverage after
      const cov = await apiClient.getCoverage(sessionDir, sessionId);
      setGenerationComplete(
        newFiles,
        genSummary.total_generated,
        cov.coverage_before,
        cov.coverage_after,
        genSummary.quality_score,
      );
      // Auto-select the first file that actually received new docstrings
      const firstChanged = Object.values(newFiles).find(fd => fd.generatedRanges.length > 0);
      if (firstChanged) {
        useSessionStore.getState().setActiveFile(firstChanged.path);
      }
    } catch (err: any) {
      // Use setErrorOnly so the error banner shows but the user stays on the
      // Inspect page (setError would reset phase to 'idle' = Upload page).
      const s = useSessionStore.getState();
      if (s.sessionId && s.report) {
        s.setErrorOnly(err.message || 'Generation failed');
        s.setPhase('analyzed');
      } else {
        setError(err.message || 'Generation failed');
      }
    }
  };

  const handleDownload = async () => {
    if (!sessionId) return;
    await apiClient.downloadProject(sessionId);
  };

  // ── fileCount for upload phase display ────────────────────────────────────
  const fileCount = Object.keys(files).length;
  const filePaths  = Object.keys(files);

  // ── render ────────────────────────────────────────────────────────────────
  const error = store.error;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Fixed topbar */}
      <PhaseHeader phase={phase} onReset={store.reset} />

      {/* Error banner — shown above all content areas */}
      {error && (
        <div style={{
          flexShrink: 0,
          background: '#fef2f2', borderBottom: '1px solid #fca5a5', color: '#dc2626',
          padding: '9px 20px', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span>⚠️</span>
          <span style={{ flex: 1 }}>{error}</span>
          <button
            onClick={() => {
              if (sessionId && report) {
                store.setErrorOnly('');
              } else {
                store.reset();
              }
            }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontWeight: 600, fontSize: 13 }}
          >
            {sessionId && report ? 'Dismiss' : 'Try Again'}
          </button>
        </div>
      )}

      {/* Phase content — fills all remaining height */}
      <div key={phase} style={{ flex: 1, overflow: 'hidden', minHeight: 0, animation: 'phaseIn 0.22s ease' }}>
        <style>{`@keyframes phaseIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }`}</style>

        {/* UPLOAD / ANALYZING */}
        {(phase === 'idle' || phase === 'analyzing') && (
          <UploadPhase
            onFiles={handleFiles}
            loading={phase === 'analyzing'}
            fileCount={fileCount}
          />
        )}

        {/* ANALYZED */}
        {phase === 'analyzed' && report && (
          <AnalyzePhase report={report} onGenerate={handleGenerate} functions={rawFunctions} />
        )}

        {/* GENERATING */}
        {phase === 'generating' && (
          <GeneratePhase fileCount={fileCount || report?.totalFunctions || 0} filePaths={filePaths} />
        )}

        {/* DONE */}
        {phase === 'done' && (
          <ReviewPhase
            files={files}
            activeFile={activeFile}
            onSelectFile={store.setActiveFile}
            before={Math.round(coverageBefore)}
            after={Math.round(coverageAfter)}
            added={docstringsAdded}
            qualityScore={store.qualityScore}
            onDownload={handleDownload}
          />
        )}
      </div>
    </div>
  );
}
