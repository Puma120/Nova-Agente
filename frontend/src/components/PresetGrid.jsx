import { PRESETS } from "../lib/presets";
import NovaFace from "./NovaFace";
import Icon from "./Icon";

export default function PresetGrid({ userName, onPick }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center">
      <NovaFace size={96} mood="happy" />
      <h2 className="text-3xl font-bold mt-5 flex items-center gap-2">
        Hola{userName ? `, ${userName}` : ""}
        <Icon name="sparkles" className="w-7 h-7 text-nova-cyan" />
      </h2>
      <p className="text-muted mt-2 max-w-md">
        Soy Nova, tu asistente personal. Pregúntame lo que quieras o empieza con una de estas ideas.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-8 w-full max-w-3xl">
        {PRESETS.map((p) => (
          <button key={p.title} onClick={() => onPick(p.prompt)}
            className="glass hover:glass-strong hover:glow-violet rounded-2xl p-4 text-left transition group">
            <div className="w-9 h-9 rounded-lg glass-strong flex items-center justify-center text-nova-violet mb-2.5">
              <Icon name={p.icon} />
            </div>
            <div className="text-sm font-semibold group-hover:gradient-text transition">{p.title}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
