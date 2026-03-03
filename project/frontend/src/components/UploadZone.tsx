import { useRef, useState } from 'react';

interface Props {
  onFiles: (files: File[]) => void;
  loading: boolean;
}

export function UploadZone({ onFiles, loading }: Props) {
  const singleRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [fileCount, setFileCount] = useState<number>(0);

  const handle = (raw: FileList | null | undefined) => {
    setUploadError(null);
    if (!raw || raw.length === 0) {
      setUploadError('No files received. Try dragging .py files instead.');
      return;
    }

    // Debug: log all files that the browser returned
    const allFiles = Array.from(raw);
    console.log(`[UploadZone] FileList length: ${allFiles.length}`);
    allFiles.slice(0, 10).forEach(f =>
      console.log(`  [file] name=${f.name}  size=${f.size}  relPath=${(f as any).webkitRelativePath}`)
    );

    // Filter .py — match by name, not just the full path, in case webkitRelativePath is empty
    const py = allFiles.filter(f =>
      f.name.endsWith('.py') || ((f as any).webkitRelativePath as string || '').endsWith('.py')
    );

    console.log(`[UploadZone] .py files found: ${py.length}`);
    // The instruction seems to have a malformed line here, interpreting it as a replacement for the subsequent if/else block.
    // Assuming the intent was to update the logic for handling found .py files,
    // and the `const py = await Promise.all(pyFiles);` part was a mistake or from a different context,
    // as `py` is already defined above as an array of File objects.
    // The core change requested seems to be setting `uploadError` to null on success.
    if (py.length > 0) {
      setUploadError(null); // Added this line as per the instruction's implied change
      setFileCount(py.length);
      onFiles(py);
    } else {
      setUploadError(`No Python (.py) files found. Received ${allFiles.length} file(s): ${allFiles.slice(0,5).map(f=>f.name).join(', ')}`);
    }
  };

  // Recursive folder traversal for drag-and-drop
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
    else alert('No Python (.py) files found in the dropped items.');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '52vh', padding: '16px 24px' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: 28, maxWidth: 620 }}>
        <div style={{
          width: 64, height: 64, borderRadius: 18,
          background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
          border: '2px solid #d97706',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, margin: '0 auto 14px',
        }}>📋</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, letterSpacing: -0.5 }}>
          Python Docstring Generator
        </h1>
        <p style={{ fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          Upload your Python files. The AI will analyze documentation coverage,
          then intelligently generate missing docstrings.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); if (!loading) setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        style={{
          width: '100%', maxWidth: 760,
          border: `2px dashed ${isDragging ? '#d97706' : 'var(--border)'}`,
          borderRadius: 28,
          padding: '36px 36px',
          background: isDragging ? '#fffbeb' : 'var(--bg-card)',
          textAlign: 'center',
          transition: 'all 0.25s ease',
          boxShadow: isDragging ? '0 0 0 4px rgba(180,83,9,0.12)' : 'var(--shadow-card)',
        }}
      >
        {loading ? (
          <div>
            <div style={{ fontSize: 36, marginBottom: 16 }}>🔍</div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
              {fileCount > 0 ? `Parsing ${fileCount} file${fileCount === 1 ? '' : 's'}…` : 'Parsing your repository…'}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
              Running static analysis to check documentation coverage
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 20 }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%',
                border: '3px solid var(--border)',
                borderTopColor: 'var(--btn-bg)',
                animation: 'spin 0.8s linear infinite',
              }} />
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📂</div>
            <div style={{ fontWeight: 600, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
              Drop .py files here
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 24 }}>
              or click a button below — single files or entire project folders
            </div>
            {uploadError && (
              <div style={{
                color: '#dc2626', fontSize: 12, fontWeight: 500,
                background: '#fef2f2', borderRadius: 8, padding: '8px 14px',
                marginBottom: 14, border: '1px solid #fca5a5', wordBreak: 'break-word',
              }}>
                ⚠️ {uploadError}
              </div>
            )}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => singleRef.current?.click()}
                style={{
                  padding: '10px 32px', borderRadius: 999,
                  background: 'var(--btn-bg)', color: '#fff', border: 'none',
                  fontWeight: 600, fontSize: 14, cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(180,83,9,0.3)',
                }}
              >
                📄 Browse .py Files
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={singleRef}
        type="file"
        accept=".py"
        multiple
        style={{ display: 'none' }}
        onChange={e => { handle(e.target.files); e.target.value = ''; }}
      />

      <div style={{ display: 'flex', gap: 10, marginTop: 20, flexWrap: 'wrap', justifyContent: 'center' }}>
        {['📊 Coverage Analysis', '⚙️ Documentation', '🔍 Side-by-Side Review', '⬇️ Export Code'].map(f => (
          <span key={f} style={{
            padding: '5px 14px', borderRadius: 999,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--text-secondary)', fontSize: 12, fontWeight: 500,
          }}>{f}</span>
        ))}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
