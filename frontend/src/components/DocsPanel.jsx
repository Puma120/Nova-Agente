import { useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import { useApp } from "../context/AppContext";
import Icon from "./Icon";

export default function DocsPanel() {
  const { token } = useApp();
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef();

  const load = async () => {
    const data = await api.getDocuments(token);
    setDocs(data.documents || []);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadDocument(token, file);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      fileRef.current.value = "";
    }
  };

  const remove = async (id) => {
    await api.deleteDocument(token, id);
    await load();
  };

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold">Base de conocimiento</h2>
        <p className="text-muted text-sm mt-1 mb-6">
          Sube PDF, Markdown o TXT. Nova los indexa y los consulta cuando le preguntas — es su memoria de largo plazo.
        </p>

        <label className={`btn-gradient inline-flex items-center gap-2 text-white text-sm font-semibold px-4 py-2.5 rounded-xl cursor-pointer ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          {uploading ? "Subiendo…" : "Subir documento"}
          <input ref={fileRef} type="file" accept=".pdf,.md,.txt" className="hidden" onChange={upload} />
        </label>

        {error && <p className="text-nova-pink text-sm mt-3">{error}</p>}

        <div className="mt-6 space-y-2">
          {docs.length === 0 && (
            <p className="text-muted/60 text-sm">Aún no has subido documentos.</p>
          )}
          {docs.map((d) => (
            <div key={d.id} className="glass rounded-2xl px-4 py-3 flex items-center justify-between">
              <div className="min-w-0 flex items-center gap-2.5">
                <Icon name="document" className="w-4 h-4 text-nova-violet shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{d.filename}</p>
                  <p className="text-muted text-xs">
                    {d.chunk_count} fragmentos · {new Date(d.created_at).toLocaleDateString("es-MX")}
                  </p>
                </div>
              </div>
              <button onClick={() => remove(d.id)}
                className="text-muted hover:text-nova-pink text-xs transition shrink-0 ml-3">
                Eliminar
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
