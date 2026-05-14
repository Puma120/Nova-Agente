import { useState } from "react";
import * as api from "../lib/api";
import { useApp } from "../context/AppContext";
import NovaFace from "./NovaFace";
import Icon from "./Icon";

function GoogleGlyph() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8a12 12 0 110-24c3 0 5.8 1.1 7.9 3l5.7-5.7A20 20 0 1024 44a20 20 0 0019.6-23.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8A12 12 0 0124 12c3 0 5.8 1.1 7.9 3l5.7-5.7A20 20 0 006.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2A12 12 0 0112.7 28l-6.6 5.1A20 20 0 0024 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3a12 12 0 01-4.1 5.6l6.2 5.2c-.4.4 6.6-4.8 6.6-14.8 0-1.3-.1-2.3-.4-3.5z" />
    </svg>
  );
}

const FEATURES = [
  { icon: "memory", title: "Memoria que te conoce", desc: "Gestiona tu gemelo digital" },
  { icon: "document", title: "RAG sobre tus documentos", desc: "Responde con tu propia información" },
  { icon: "bolt", title: "Razona a la vista", desc: "Ves cada paso que da el agente" },
  { icon: "calendar", title: "Actúa por ti", desc: "Integrado con Google Calendar" },
];

export default function AuthScreen() {
  const { authError } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const signIn = async () => {
    setLoading(true);
    setError("");
    try {
      const { auth_url } = await api.getGoogleLoginUrl();
      window.location.href = auth_url;
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="aurora h-screen overflow-hidden flex flex-col">
      {/* Brand bar */}
      <header className="flex items-center gap-2.5 px-6 py-4 shrink-0">
        <NovaFace size={30} mood="neutral" />
        <span className="font-bold gradient-text text-lg">Nova</span>
      </header>

      {/* Hero */}
      <main className="flex-1 min-h-0 overflow-y-auto flex flex-col items-center justify-center px-6 text-center">
        <div className="glow-violet rounded-full animate-rise">
          <NovaFace size={104} mood="happy" />
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold mt-5 gradient-text animate-rise">Nova</h1>
        <p className="text-lg sm:text-xl font-medium mt-3 animate-rise">
          Tu asistente personal con agentes inteligentes
        </p>
        <p className="text-muted mt-2.5 max-w-xl animate-rise">
          No es un chat más: es tu gemelo digital. Gestiona tu memoria, razona a la
          vista y actúa por ti con herramientas reales.
        </p>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-7 w-full max-w-3xl">
          {FEATURES.map(({ icon, title, desc }) => (
            <div key={title} className="glass rounded-2xl p-4 text-left">
              <div className="w-10 h-10 rounded-xl glass-strong flex items-center justify-center text-nova-violet">
                <Icon name={icon} />
              </div>
              <div className="text-sm font-semibold mt-2.5">{title}</div>
              <div className="text-xs text-muted mt-0.5">{desc}</div>
            </div>
          ))}
        </div>

        <button onClick={signIn} disabled={loading}
          className="glass-strong hover:glow-violet flex items-center justify-center gap-3
                     px-6 py-3 rounded-xl font-semibold transition disabled:opacity-50 mt-8">
          <GoogleGlyph />
          {loading ? "Conectando…" : "Continuar con Google"}
        </button>
        <p className="text-muted/70 text-xs mt-3 max-w-sm">
          Al iniciar sesión, Nova podrá ver tu perfil y gestionar tu Google Calendar.
        </p>
        {(error || authError) && (
          <p className="text-nova-pink text-sm mt-3">{error || authError}</p>
        )}
      </main>

      {/* Lab + authors */}
      <footer className="glass border-t border-white/5 px-6 py-4 text-center shrink-0">
        <p className="text-sm font-medium">
          Laboratorio de Inteligencia Artificial y Realidad Extendida
        </p>
        <p className="text-muted text-xs mt-0.5">IBERO Puebla</p>
        <p className="text-muted/70 text-xs mt-1.5">
          Autores: Pablo Urbina Macip · Rafael Pérez Aguirre
        </p>
      </footer>
    </div>
  );
}
