import NovaFace from "./NovaFace";
import Markdown from "./Markdown";
import AgentSteps from "./AgentSteps";
import Icon from "./Icon";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-rise">
        <div className="max-w-[78%] btn-gradient text-white rounded-2xl rounded-br-md px-4 py-2.5">
          <p className="text-[15px] whitespace-pre-wrap leading-relaxed">{message.content}</p>
          {message.image_url && (
            <span className="flex items-center gap-1 text-xs text-white/70 mt-1">
              <Icon name="image" className="w-3.5 h-3.5" /> Imagen adjunta
            </span>
          )}
          {message.doc_name && (
            <span className="inline-flex items-center gap-1 text-xs mt-1.5 bg-white/15 rounded-md px-2 py-0.5">
              <Icon name="document" className="w-3.5 h-3.5" /> {message.doc_name}
            </span>
          )}
        </div>
      </div>
    );
  }

  const streaming = message.streaming;
  const empty = !message.content && (!message.steps || message.steps.length === 0);

  return (
    <div className="flex items-start gap-3 animate-rise">
      <div className="shrink-0 mt-0.5">
        <NovaFace size={40} mood={message.emotion || "neutral"} />
      </div>
      <div className="max-w-[80%] min-w-0">
        <AgentSteps steps={message.steps} active={streaming} />

        {empty && streaming && (
          <div className="glass rounded-2xl rounded-tl-md px-4 py-2.5 text-muted text-sm">
            <span className="pulse-dot inline-block">Nova está pensando…</span>
          </div>
        )}

        {message.content && (
          <div className="glass-strong rounded-2xl rounded-tl-md px-4 py-2.5">
            <div className={streaming ? "stream-caret" : ""}>
              <Markdown text={message.content} />
            </div>
          </div>
        )}

        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.sources.map((s) => (
              <span key={s}
                className="inline-flex items-center gap-1 text-[11px] text-nova-cyan/90 glass rounded-md px-2 py-0.5">
                <Icon name="paperclip" className="w-3 h-3" /> {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
