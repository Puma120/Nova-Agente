import { useEffect, useState } from "react";
import * as api from "../lib/api";
import { useApp } from "../context/AppContext";

export default function IntegrationsPanel() {
  const { token } = useApp();
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.getGoogleStatus(token).then(setStatus);
  }, [token]);

  const connected = status?.connected;

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold">Integraciones</h2>
        <p className="text-muted text-sm mt-1 mb-6">
          Servicios que Nova puede usar para actuar por ti.
        </p>

        <div className="glass-strong rounded-2xl p-5">
          <div className="flex items-start gap-4">
            <div className="text-3xl">🗓️</div>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold">Google Calendar</h3>
                {status && (
                  <span className={`text-xs ${connected ? "text-nova-cyan" : "text-muted"}`}>
                    {connected ? "● Conectado" : "○ Sin conexión"}
                  </span>
                )}
              </div>
              <p className="text-muted text-sm mt-1">
                Se conecta automáticamente al iniciar sesión con Google. Nova puede
                consultar tu agenda y crear eventos durante la conversación.
              </p>
              {status && !status.configured && (
                <p className="text-amber-300/90 text-xs mt-3">
                  El servidor no tiene configuradas las credenciales de Google OAuth.
                </p>
              )}
              {status && status.configured && !connected && (
                <p className="text-amber-300/90 text-xs mt-3">
                  No hay credenciales guardadas. Cierra sesión y vuelve a entrar con
                  Google para reconectar el calendario.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
