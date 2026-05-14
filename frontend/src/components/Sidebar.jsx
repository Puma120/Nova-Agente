import { useApp } from "../context/AppContext";
import NovaFace from "./NovaFace";

function NavButton({ active, onClick, icon, label }) {
  return (
    <button onClick={onClick}
      className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-sm transition ${
        active
          ? "glass-strong text-ink glow-violet"
          : "text-muted hover:text-ink hover:bg-white/5"
      }`}>
      <span className="text-base">{icon}</span>
      {label}
    </button>
  );
}

export default function Sidebar({ view, setView, onNewChat }) {
  const { user, logout, conversations, activeConvId, setActiveConvId, deleteConversation } = useApp();

  const openConversation = (id) => {
    setActiveConvId(id);
    setView("chat");
  };

  return (
    <aside className="w-72 shrink-0 glass border-r border-white/5 flex flex-col h-full">
      <div className="p-4">
        <div className="flex items-center gap-2.5 mb-4">
          <NovaFace size={34} mood="neutral" />
          <span className="text-xl font-bold gradient-text">Nova</span>
        </div>
        <button onClick={onNewChat}
          className="btn-gradient w-full text-white text-sm font-semibold py-2.5 rounded-xl">
          + Nueva conversación
        </button>
      </div>

      <nav className="px-3 space-y-1">
        <NavButton active={view === "docs"} onClick={() => setView("docs")}
          icon="📚" label="Documentos" />
        <NavButton active={view === "integrations"} onClick={() => setView("integrations")}
          icon="🔌" label="Integraciones" />
      </nav>

      <div className="px-4 pt-4 pb-1 text-[11px] uppercase tracking-wider text-muted/60">
        Conversaciones
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-muted/50 text-xs px-3 py-2">Aún no hay conversaciones.</p>
        )}
        {conversations.map((c) => (
          <div key={c.id}
            onClick={() => openConversation(c.id)}
            className={`group flex items-center rounded-xl px-3 py-2 cursor-pointer transition ${
              c.id === activeConvId && view === "chat"
                ? "glass-strong text-ink"
                : "text-muted hover:text-ink hover:bg-white/5"
            }`}>
            <span className="flex-1 truncate text-sm">{c.titulo}</span>
            <button
              onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}
              className="opacity-0 group-hover:opacity-100 text-muted hover:text-nova-pink ml-2 text-xs transition">
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-2.5 glass rounded-xl px-3 py-2">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded-full btn-gradient shrink-0 flex items-center justify-center text-sm font-bold text-white">
              {(user?.name || "?").charAt(0).toUpperCase()}
            </div>
          )}
          <div className="truncate flex-1">
            <p className="text-sm font-medium truncate">{user?.name}</p>
            <p className="text-muted text-xs truncate">{user?.email}</p>
          </div>
          <button onClick={logout} className="text-muted hover:text-nova-pink text-xs transition shrink-0">
            Salir
          </button>
        </div>
      </div>
    </aside>
  );
}
