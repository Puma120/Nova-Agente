import { useState } from "react";

function StepRow({ step }) {
  const running = step.status === "running";
  return (
    <div className="flex items-center gap-2.5 py-1">
      {running ? (
        <span className="w-2 h-2 rounded-full bg-nova-cyan pulse-dot shrink-0" />
      ) : (
        <span className="w-3.5 h-3.5 rounded-full bg-nova-violet/20 flex items-center justify-center shrink-0">
          <svg className="w-2.5 h-2.5 text-nova-violet" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 011.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z" clipRule="evenodd" />
          </svg>
        </span>
      )}
      <span className={`text-[13px] ${running ? "text-ink" : "text-muted"}`}>
        {step.label}
        {step.detail && <span className="text-muted/70"> · {step.detail}</span>}
      </span>
    </div>
  );
}

export default function AgentSteps({ steps, active }) {
  const [open, setOpen] = useState(true);
  if (!steps || steps.length === 0) return null;

  return (
    <div className="glass rounded-xl px-3 py-2 mb-2 max-w-md">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left">
        <span className={`text-[13px] font-medium ${active ? "gradient-text" : "text-muted"}`}>
          {active ? "Nova está trabajando…" : `Razonamiento · ${steps.length} ${steps.length === 1 ? "paso" : "pasos"}`}
        </span>
        <svg className={`w-3.5 h-3.5 text-muted ml-auto transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.3 7.3a1 1 0 011.4 0L10 10.6l3.3-3.3a1 1 0 111.4 1.4l-4 4a1 1 0 01-1.4 0l-4-4a1 1 0 010-1.4z" clipRule="evenodd" />
        </svg>
      </button>
      {open && (
        <div className="mt-1.5 border-t border-white/5 pt-1.5">
          {steps.map((s) => <StepRow key={s.id} step={s} />)}
        </div>
      )}
    </div>
  );
}
