import { create } from 'zustand';

export type Phase = 'idle' | 'analyzing' | 'analyzed' | 'generating' | 'done';

export interface UndocumentedItem {
  name: string;
  file: string;
  lineno: number;
}

export interface PerFileStats {
  file: string;
  total: number;
  documented: number;
  coveragePct: number;
}

export interface AnalysisReport {
  totalFunctions: number;
  documented: number;
  undocumented: number;
  coveragePct: number;
  missingParams: number;
  missingReturns: number;
  qualityScore: number;
  undocumentedList: UndocumentedItem[];
  // enriched AST data
  perFile: PerFileStats[];
  withReturnAnnotation: number;
  withParams: number;
  skipped: number;
  totalFiles: number;
}

// A range of lines [start, end] (1-indexed, inclusive) added by AI
export interface LineRange {
  start: number;
  end: number;
}

export interface FileData {
  path: string;
  originalContent: string;
  documentedContent: string;
  generatedRanges: LineRange[]; // line ranges of AI-written docstrings
}

interface SessionState {
  phase: Phase;
  sessionId: string | null;
  sessionDir: string | null;
  report: AnalysisReport | null;
  files: Record<string, FileData>;
  activeFile: string | null;
  docstringsAdded: number;
  coverageBefore: number;
  coverageAfter: number;
  qualityScore: number;
  error: string | null;
  llmProvider: 'local' | 'gemini';
  docstringStyle: 'google' | 'numpy' | 'rest' | 'epytext' | 'sphinx';

  // Actions
  startAnalyzing: () => void;
  setAnalysisComplete: (
    sessionId: string,
    sessionDir: string,
    report: AnalysisReport,
    filePaths: string[]
  ) => void;
  startGenerating: () => void;
  setGenerationComplete: (
    files: Record<string, FileData>,
    docstringsAdded: number,
    coverageBefore: number,
    coverageAfter: number,
    qualityScore: number
  ) => void;
  setReport: (report: AnalysisReport) => void;
  setActiveFile: (path: string) => void;
  setLlmProvider: (provider: 'local' | 'gemini') => void;
  setDocstringStyle: (style: 'google' | 'numpy' | 'rest' | 'epytext' | 'sphinx') => void;
  setError: (msg: string) => void;
  reset: () => void;
  setPhase: (phase: Phase) => void;
}

const defaultState = {
  phase: 'idle' as Phase,
  sessionId: null,
  sessionDir: null,
  report: null,
  files: {},
  activeFile: null,
  docstringsAdded: 0,
  coverageBefore: 0,
  coverageAfter: 0,
  qualityScore: 100,
  error: null,
  llmProvider: 'local' as 'local' | 'gemini',
  docstringStyle: 'google' as 'google' | 'numpy' | 'rest' | 'epytext' | 'sphinx',
};

export const useSessionStore = create<SessionState>((set) => ({
  ...defaultState,

  startAnalyzing: () => set({ phase: 'analyzing', error: null }),

  setAnalysisComplete: (sessionId, sessionDir, report, filePaths) => {
    const files: Record<string, FileData> = {};
    filePaths.forEach((fp) => {
      files[fp] = {
        path: fp,
        originalContent: '',
        documentedContent: '',
        generatedRanges: [],
      };
    });
    set({
      phase: 'analyzed',
      sessionId,
      sessionDir,
      report,
      files,
      activeFile: filePaths[0] ?? null,
    });
  },

  startGenerating: () => set({ phase: 'generating' }),

  setGenerationComplete: (files, docstringsAdded, coverageBefore, coverageAfter, qualityScore) =>
    set({
      phase: 'done',
      files,
      docstringsAdded,
      coverageBefore,
      coverageAfter,
      qualityScore,
    }),

  setReport: (report) => set({ report }),

  setActiveFile: (path) => set({ activeFile: path }),

  setLlmProvider: (provider) => set({ llmProvider: provider }),

  setDocstringStyle: (style) => set({ docstringStyle: style }),

  setError: (msg) => set({ error: msg, phase: 'idle' }),

  reset: () => set(defaultState),

  setPhase: (phase) => set((state) => {
    // Only allow navigating forward if the data supports it
    if (phase === 'generating' && (!state.sessionId || !state.sessionDir)) return state;
    if (phase === 'done' && Object.keys(state.files).length === 0) return state;
    if (phase === 'analyzed' && !state.report) return state;
    return { phase };
  }),
}));
