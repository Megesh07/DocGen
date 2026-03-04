const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8001/api/v1";

export interface ScanFunction {
  file: string;
  function: string;
  lineno: number;
  signature: string;
  docstring: string;
  generation_type: string;
  skipped: boolean;
  skip_reason?: string;
}

export interface UploadResponse {
  session_id: string;
  session_dir: string;
  functions: ScanFunction[];
}

export interface RescanResponse {
  session_id: string;
  session_dir?: string;
  functions: ScanFunction[];
}

export interface CoverageResponse {
  coverage_before: number;
  coverage_after: number;
  total_functions: number;
  total_files: number;
  added: number;
  improved: number;
}

export const apiClient = {
  async uploadProject(files: FileList | File[], style: string = 'google'): Promise<UploadResponse> {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const path = (file as any)._path || (file as any).webkitRelativePath || file.name;
      formData.append('files', file, path);
    }
    formData.append('style', style);
    const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async generateAll(
    sessionId: string,
    provider: 'local' | 'gemini' = 'local',
    style: string = 'google'
  ): Promise<{ quality_score: number; warnings: number; errors: number; total_generated: number }> {
    const res = await fetch(`${API_BASE}/generate/all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, llm_provider: provider, style }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    return {
      quality_score: data.quality_score ?? 100,
      warnings: data.warnings ?? 0,
      errors: data.errors ?? 0,
      total_generated: data.total_generated ?? 0,
    };
  },

  async rescan(sessionId: string, style: string = 'google'): Promise<RescanResponse> {
    const res = await fetch(`${API_BASE}/rescan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, style }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async previewFile(sessionId: string, filePath: string): Promise<{ file: string; content: string }> {
    const res = await fetch(`${API_BASE}/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, file_path: filePath }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getFileSource(sessionId: string, filePath: string): Promise<{ file: string; content: string }> {
    const res = await fetch(
      `${API_BASE}/file?session_id=${encodeURIComponent(sessionId)}&path=${encodeURIComponent(filePath)}`
    );
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getCoverage(sessionDir: string, sessionId?: string): Promise<CoverageResponse> {
    let url = `${API_BASE}/coverage?path=${encodeURIComponent(sessionDir)}`;
    if (sessionId) url += `&session_id=${encodeURIComponent(sessionId)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async downloadProject(sessionId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/download/${encodeURIComponent(sessionId)}`);
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `documented_project_${sessionId}.zip`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};
