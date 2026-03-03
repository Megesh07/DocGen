import { useState, useRef, useCallback, useEffect } from 'react';
import type { LineRange } from '../store/sessionStore';

// ── Lightweight Python syntax tokenizer ──────────────────────────────────────
type TT = 'kw' | 'bi' | 'str' | 'cmt' | 'deco' | 'num' | 'fname' | 'cname' | 'op' | 'plain';

const KEYWORDS = new Set([
  'def','class','return','if','elif','else','for','while','import','from','as',
  'with','try','except','finally','raise','pass','break','continue','lambda',
  'yield','True','False','None','and','or','not','in','is','del','global',
  'nonlocal','assert','async','await',
]);
const BUILTINS = new Set([
  'print','len','range','type','isinstance','str','int','float','list','dict',
  'set','tuple','bool','bytes','enumerate','zip','map','filter','sorted',
  'reversed','sum','min','max','abs','round','open','super','property',
  'staticmethod','classmethod','object','Exception','ValueError','TypeError',
  'KeyError','IndexError','AttributeError','NotImplementedError','self','cls',
  'None','True','False','iter','next','hasattr','getattr','setattr','vars',
  'dir','id','repr','format','input','any','all','callable','chr','ord',
]);
const TOKEN_COLOR: Record<TT, string> = {
  kw:    '#b45309',          // amber — keywords
  bi:    '#0369a1',          // blue — builtins
  str:   '#15803d',          // green — strings / docstrings
  cmt:   '#9ca3af',          // gray italic — comments
  deco:  '#7c3aed',          // purple — decorators
  num:   '#b91c1c',          // red — numbers
  fname: '#1d4ed8',          // blue — function name after def
  cname: '#0f766e',          // teal — class name after class
  op:    '#6b7280',          // gray — operators / punctuation
  plain: 'inherit',          // default text color
};

interface Token { text: string; tt: TT; }

/** Tokenize one line; tripleState carries open triple-quote context across lines */
function tokenizeLine(
  line: string,
  tripleState: { open: boolean; q: string },
): Token[] {
  const out: Token[] = [];
  let i = 0;

  function push(text: string, tt: TT) {
    if (!text) return;
    const last = out[out.length - 1];
    if (last && last.tt === tt) last.text += text;
    else out.push({ text, tt });
  }

  while (i < line.length) {
    const rest = line.slice(i);
    const ch = line[i];

    // ── still inside a multiline string ──
    if (tripleState.open) {
      const tq = tripleState.q + tripleState.q + tripleState.q;
      const end = rest.indexOf(tq);
      if (end === -1) { push(rest, 'str'); i = line.length; }
      else { push(rest.slice(0, end + 3), 'str'); i += end + 3; tripleState.open = false; tripleState.q = ''; }
      continue;
    }

    // ── comment ──
    if (ch === '#') { push(rest, 'cmt'); break; }

    // ── decorator ──
    if (ch === '@' && /^\s*$/.test(line.slice(0, i))) {
      const m = rest.match(/^@[\w.]+/);
      if (m) { push(m[0], 'deco'); i += m[0].length; continue; }
    }

    // ── triple-quoted string ──
    if (rest.startsWith('"""') || rest.startsWith("'''")) {
      const q = ch;
      const tq = q + q + q;
      const end = rest.indexOf(tq, 3);
      if (end === -1) {
        push(rest, 'str'); i = line.length;
        tripleState.open = true; tripleState.q = q;
      } else {
        push(rest.slice(0, end + 3), 'str'); i += end + 3;
      }
      continue;
    }

    // ── single-quoted string ──
    if (ch === '"' || ch === "'") {
      let j = i + 1;
      while (j < line.length) {
        if (line[j] === '\\') { j += 2; continue; }
        if (line[j] === ch) { j++; break; }
        j++;
      }
      push(line.slice(i, j), 'str'); i = j; continue;
    }

    // ── number ──
    if (/\d/.test(ch) || (ch === '.' && /\d/.test(line[i + 1] ?? ''))) {
      const m = rest.match(/^0[xXoObB][\da-fA-F_]+|^\d+\.?\d*([eEjJ][+-]?\d+)?/);
      if (m) { push(m[0], 'num'); i += m[0].length; continue; }
    }

    // ── identifier / keyword / builtin ──
    if (/[a-zA-Z_]/.test(ch)) {
      const m = rest.match(/^[a-zA-Z_]\w*/);
      if (m) {
        const word = m[0];
        // Determine function/class name: look for last meaningful keyword token
        const prevKw = [...out].reverse().find(t => t.tt !== 'plain' && t.tt !== 'op' || t.text.trim() !== '');
        let tt: TT;
        if (KEYWORDS.has(word))       tt = 'kw';
        else if (BUILTINS.has(word))  tt = 'bi';
        else if (prevKw?.tt === 'kw' && prevKw.text === 'def')   tt = 'fname';
        else if (prevKw?.tt === 'kw' && prevKw.text === 'class') tt = 'cname';
        else tt = 'plain';
        push(word, tt); i += word.length; continue;
      }
    }

    // ── operator / punctuation ──
    if (/[+\-*/%=<>!&|^~:.,()\[\]{};@]/.test(ch)) { push(ch, 'op'); i++; continue; }

    push(ch, 'plain'); i++;
  }

  return out;
}

/** Pre-tokenize entire source into per-line token arrays */
function tokenize(src: string): Token[][] {
  const lines = src.split('\n');
  const result: Token[][] = [];
  const state = { open: false, q: '' };
  for (const line of lines) {
    result.push(tokenizeLine(line, state));
  }
  return result;
}

function TokenSpan({ tk }: { tk: Token }) {
  const color = TOKEN_COLOR[tk.tt];
  return (
    <span style={{
      color,
      fontStyle: tk.tt === 'cmt' ? 'italic' : undefined,
      fontWeight: (tk.tt === 'kw' || tk.tt === 'fname' || tk.tt === 'cname') ? 600 : undefined,
    }}>{tk.text}</span>
  );
}
// ─────────────────────────────────────────────────────────────────────────────

interface CodePaneProps {
  title: string;
  content: string;
  tokenizedLines: Token[][];
  highlightRanges?: LineRange[];
  accent?: string;
}

function CodePane({ title, content, tokenizedLines, highlightRanges = [], accent }: CodePaneProps) {
  const lines = content.split('\n');

  function isHighlighted(lineNum: number): boolean {
    return highlightRanges.some(r => lineNum >= r.start && lineNum <= r.end);
  }

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', height: '100%', width: '100%' }}>
      {/* Pane header */}
      <div style={{
        padding: '10px 20px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: '50%',
          background: accent || 'var(--border)',
        }} />
        <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: 0.8, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
          {title}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            onClick={handleCopy}
            style={{
              background: 'transparent', border: '1px solid var(--border)',
              borderRadius: 6, padding: '4px 10px', fontSize: 11, fontWeight: 600,
              color: copied ? '#059669' : 'var(--text-secondary)',
              cursor: 'pointer', transition: 'all 0.15s',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      </div>

      {/* Code area */}
      <div style={{ flex: 1, overflow: 'auto', background: '#fdfcf9', position: 'relative' }}>
        <table style={{ borderCollapse: 'collapse', minWidth: '100%' }}>
          <tbody>
            {lines.map((_line, i) => {
              const lineNum = i + 1;
              const hl = isHighlighted(lineNum);
              const rowProps = title.toLowerCase().includes('document')
                ? { 'data-documented-line': lineNum } as any
                : { 'data-source-line': lineNum } as any;
              const toks = tokenizedLines[i] ?? [];
              return (
                <tr key={i} style={{ background: hl ? 'var(--highlight-bg)' : 'transparent' }} {...rowProps}>
                  {/* Line number */}
                  <td style={{
                    width: 48, userSelect: 'none',
                    padding: '1px 12px 1px 8px',
                    textAlign: 'right', color: '#c5bdb2',
                    fontSize: 11, fontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace",
                    borderLeft: hl ? '3px solid var(--highlight-border)' : '3px solid transparent',
                    verticalAlign: 'top', lineHeight: '20px',
                  }}>
                    {lineNum}
                  </td>
                  {/* Syntax-highlighted code */}
                  <td style={{
                    padding: '1px 16px 1px 4px',
                    fontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace",
                    fontSize: 12.5, lineHeight: '20px',
                    whiteSpace: 'pre',
                    verticalAlign: 'top',
                    color: 'var(--text-primary)',
                  }}>
                    {toks.length > 0
                      ? toks.map((tk, j) => <TokenSpan key={j} tk={tk} />)
                      : '\u00a0'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface Props {
  originalContent: string;
  documentedContent: string;
  generatedRanges: LineRange[];
  /** When true, file was fully documented before AI ran — show info panel instead of diff */
  isPreDocumented?: boolean;
}

export function ComparisonViewer({ originalContent, documentedContent, generatedRanges, isPreDocumented = false }: Props) {
  const hasChanges = generatedRanges.length > 0 && !isPreDocumented;

  // Pre-tokenize once — cheap on re-render since content is stable
  const origTokens = tokenize(originalContent);
  const docTokens  = tokenize(documentedContent);

  // split % = how much of the total width the LEFT pane takes (0–100)
  const [splitPct, setSplitPct] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const raw = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(Math.min(Math.max(raw, 15), 85));
    };
    const onMouseUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  // Pre-documented or nothing generated — both show full-width source
  if (isPreDocumented || !hasChanges) {
    return (
      <div style={{ height: '100%', borderTop: '1px solid var(--border)', overflow: 'hidden' }}>
        <CodePane title="Source" content={originalContent} tokenizedLines={origTokens} accent="#9e9890" />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex', height: '100%',
        borderTop: '1px solid var(--border)',
        overflow: 'hidden', position: 'relative',
      }}
    >
      {/* Left pane */}
      <div style={{ width: `${splitPct}%`, overflow: 'hidden', flexShrink: 0 }}>
        <CodePane title="Original" content={originalContent} tokenizedLines={origTokens} accent="#9e9890" />
      </div>

      {/* Drag handle */}
      <div
        onMouseDown={onMouseDown}
        style={{
          width: 6, flexShrink: 0, cursor: 'col-resize',
          background: 'var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 10,
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#b45309')}
        onMouseLeave={e => (e.currentTarget.style.background = 'var(--border)')}
        title="Drag to resize"
      >
        {/* Grip dots */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, pointerEvents: 'none' }}>
          {[0,1,2,3].map(k => (
            <div key={k} style={{ width: 2, height: 2, borderRadius: '50%', background: '#b1a99a' }} />
          ))}
        </div>
      </div>

      {/* Right pane */}
      <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
        <CodePane title="Documented" content={documentedContent} tokenizedLines={docTokens} highlightRanges={generatedRanges} accent="#059669" />
      </div>
    </div>
  );
}
