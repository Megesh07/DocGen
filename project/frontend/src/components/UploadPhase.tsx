import { useRef, useState } from 'react';

interface Props {
  onFiles: (files: File[]) => void;
  loading: boolean;
  fileCount?: number;
}

export function UploadPhase({ onFiles, loading, fileCount = 0 }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handle = (raw: FileList | null | undefined) => {
    setUploadError(null);
    if (!raw || raw.length === 0) {
      setUploadError('No files received. Try dragging .py files directly.');
      return;
    }
    const allFiles = Array.from(raw);
    const py = allFiles.filter(
      f => f.name.endsWith('.py') || ((f as any).webkitRelativePath as string || '').endsWith('.py')
    );
    if (py.length > 0) {
      onFiles(py);
    } else {
      setUploadError(`No Python (.py) files found in ${allFiles.length} file(s).`);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (loading) return;
    const items = e.dataTransfer.items;
    if (!items || items.length === 0) return;
    const files: File[] = [];
    const readEntry = async (entry: any, path = '') => {
      if (entry.isFile) {
        if (entry.name.endsWith('.py')) {
          const file = await new Promise<File>(resolve => entry.file(resolve));
          Object.defineProperty(file, 'webkitRelativePath', { value: path + file.name, writable: true });
          files.push(file);
        }
      } else if (entry.isDirectory) {
        const reader = entry.createReader();
        const readAll = (): Promise<any[]> =>
          new Promise(resolve =>
            reader.readEntries(async (batch: any[]) => {
              if (!batch.length) { resolve([]); return; }
              const rest = await readAll();
              resolve([...batch, ...rest]);
            })
          );
        for (const child of await readAll()) await readEntry(child, path + entry.name + '/');
      }
    };
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry?.();
      if (entry) await readEntry(entry);
    }
    if (files.length > 0) onFiles(files);
    else setUploadError('No Python (.py) files found in the dropped items.');
  };

  const features = [
    { icon: '◎', label: 'Coverage Analysis', desc: 'Precise per-function documentation scoring' },
    { icon: '◈', label: 'AI Docstring Writer', desc: 'Google, NumPy, reST, Epytext, Sphinx styles' },
    { icon: '◰', label: 'Side-by-Side Review', desc: 'Diff view — original vs documented code' },
    { icon: '◩', label: 'Safe Export', desc: 'Download patched project, original preserved' },
  ];

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Left panel: value proposition ────────────────────────────────── */}
      <div style={{
        width: 400,
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '48px 40px',
        overflow: 'auto',
      }}>
        {/* Logo mark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 36 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, #b45309, #d97706)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 16, letterSpacing: -1,
          }}>D</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', lineHeight: 1 }}>DocGen</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 0.4 }}>Python Documentation AI</div>
          </div>
        </div>

        <h1 style={{
          fontSize: 28, fontWeight: 800, color: 'var(--text-primary)',
          lineHeight: 1.2, letterSpacing: -0.8, marginBottom: 12,
        }}>
          Never write a{' '}
          <span style={{ color: 'var(--text-accent)' }}>docstring</span>
          {' '}manually again
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 36 }}>
          Upload your Python project and get complete, consistent documentation
          in seconds. Analyse gaps, generate docstrings, review changes,
          export clean code.
        </p>

        {/* Feature list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {features.map(f => (
            <div key={f.label} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: '#fef3c7', border: '1px solid #fde68a',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, color: '#b45309', fontWeight: 700,
              }}>{f.icon}</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 1 }}>{f.label}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Accent line */}
        <div style={{
          marginTop: 40, paddingTop: 28, borderTop: '1px solid var(--border)',
          display: 'flex', gap: 0, flexWrap: 'wrap',
        }}>
          {[['100%', 'Safe — originals untouched'], ['5 styles', 'Docstring formats']].map(([v, l]) => (
            <div key={l} style={{ flex: '1 1 90px', minWidth: 90, paddingRight: 12, marginBottom: 8 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-accent)', letterSpacing: -0.5 }}>{v}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{l}</div>
            </div>
          ))}
          <div style={{ flex: '1 1 90px', minWidth: 90, paddingRight: 12, marginBottom: 8 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-accent)', letterSpacing: -0.5 }}>Local AI</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>No data sent to cloud</div>
          </div>
        </div>
      </div>

      {/* ── Right panel: upload zone ──────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 48px',
        background: 'var(--bg-page)',
        overflow: 'auto',
      }}>
        {loading ? (
          /* Analyzing state */
          <div style={{ width: '100%', maxWidth: 520, textAlign: 'center' }}>
            <div style={{ marginBottom: 32 }}>
              <div style={{
                width: 64, height: 64, borderRadius: '50%',
                border: '4px solid var(--border)', borderTopColor: 'var(--btn-bg)',
                animation: 'spin 0.9s linear infinite',
                margin: '0 auto 20px',
              }} />
              <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--text-primary)', marginBottom: 6 }}>
                {fileCount > 0 ? `Scanning ${fileCount} file${fileCount === 1 ? '' : 's'}…` : 'Scanning repository…'}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Running static analysis — checking documentation coverage
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, textAlign: 'left' }}>
              {[
                'Discovering Python files',
                'Parsing AST structure',
                'Identifying functions and classes',
                'Scoring documentation coverage',
              ].map((step, i) => (
                <div key={step} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 16px', borderRadius: 10,
                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                    background: i === 0 ? '#ecfdf5' : 'var(--bg-page)',
                    border: `1.5px solid ${i === 0 ? '#059669' : 'var(--border)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 10, color: i === 0 ? '#059669' : 'var(--text-muted)',
                  }}>
                    {i === 0 ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize: 13, color: i === 0 ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: i === 0 ? 500 : 400 }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Upload state */
          <div style={{ width: '100%', maxWidth: 540 }}>
            <div style={{ marginBottom: 24, textAlign: 'center' }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
                Upload your Python project
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Drop a folder or select individual .py files
              </div>
            </div>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              style={{
                border: `2px dashed ${isDragging ? '#d97706' : 'var(--border)'}`,
                borderRadius: 20,
                padding: '48px 32px',
                background: isDragging ? '#fffbeb' : 'var(--bg-card)',
                textAlign: 'center',
                transition: 'all 0.2s ease',
                boxShadow: isDragging ? '0 0 0 4px rgba(180,83,9,0.10)' : 'var(--shadow-card)',
                cursor: 'pointer',
                marginBottom: 16,
              }}
              onClick={() => inputRef.current?.click()}
            >
              <div style={{
                width: 56, height: 56, borderRadius: 16, margin: '0 auto 16px',
                background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
                border: '1.5px solid #fbbf24',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 26,
              }}>📂</div>

              <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)', marginBottom: 6 }}>
                Drop .py files or folders here
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 20 }}>
                or click to browse from your computer
              </div>

              {uploadError && (
                <div style={{
                  color: '#dc2626', fontSize: 12, background: '#fef2f2',
                  borderRadius: 8, padding: '8px 12px', marginBottom: 14,
                  border: '1px solid #fca5a5', textAlign: 'left',
                }}>
                  ⚠️ {uploadError}
                </div>
              )}

              <button
                onClick={e => { e.stopPropagation(); inputRef.current?.click(); }}
                style={{
                  padding: '9px 28px', borderRadius: 999,
                  background: 'var(--btn-bg)', color: '#fff', border: 'none',
                  fontWeight: 600, fontSize: 13, cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(180,83,9,0.28)',
                  transition: 'all 0.15s',
                }}
              >
                Browse Files
              </button>
            </div>

            {/* Supported format note */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '10px 16px', borderRadius: 10,
              background: 'var(--bg-surface)', border: '1px solid var(--border)',
            }}>
              <span style={{ fontSize: 13, color: '#059669' }}>✓</span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Accepts <strong>.py</strong> files and folders — nested directories fully supported
              </span>
            </div>
          </div>
        )}

        <input ref={inputRef} type="file" accept=".py" multiple style={{ display: 'none' }}
          onChange={e => { handle(e.target.files); e.target.value = ''; }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );
}
