import { useState } from "react";
import * as api from "../lib/api";
import { useApp } from "../context/AppContext";
import NovaFace from "./NovaFace";

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
    <div className="aurora min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm glass-strong rounded-3xl p-8 animate-rise text-center">
        <div className="flex flex-col items-center mb-7">
          <div className="glow-violet rounded-full">
            <NovaFace size={76} mood="happy" />
          </div>
          <h1 className="text-3xl font-bold mt-4 gradient-text">Nova</h1>
          <p className="text-muted text-sm mt-1">
            Tu asistente personal con agentes inteligentes
          </p>
        </div>

        <button onClick={signIn} disabled={loading}
          className="glass-strong hover:glow-violet w-full flex items-center justify-center gap-3
                     py-3 rounded-xl font-semibold transition disabled:opacity-50">
          <GoogleGlyph />
          {loading ? "Conectando…" : "Continuar con Google"}
        </button>

        <p className="text-muted/70 text-xs mt-4 leading-relaxed">
          Al iniciar sesión, Nova podrá ver tu perfil y gestionar tu Google Calendar.
        </p>

        {(error || authError) && (
          <p className="text-nova-pink text-sm mt-4">{error || authError}</p>
        )}
      </div>
    </div>
  );
}
