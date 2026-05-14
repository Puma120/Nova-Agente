import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../lib/api";
import { useApp } from "../context/AppContext";
import MessageBubble from "./MessageBubble";
import Composer from "./Composer";
import PresetGrid from "./PresetGrid";
import NovaFace from "./NovaFace";

const uid = () => crypto.randomUUID();

function OnboardingWelcome({ onStart }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center">
      <div className="glow-violet rounded-full">
        <NovaFace size={104} mood="excited" />
      </div>
      <h2 className="text-3xl font-bold mt-6">
        ¡Hola! Soy <span className="gradient-text">Nova</span>
      </h2>
      <p className="text-muted mt-3 max-w-md">
        Voy a ser tu asistente personal — tu gemelo digital. Antes de empezar,
        deja que te conozca un poco. Será una charla rápida y natural.
      </p>
      <button onClick={onStart}
        className="btn-gradient text-white font-semibold px-6 py-3 rounded-xl mt-7">
        Empezar a conocernos →
      </button>
    </div>
  );
}

export default function ChatView() {
  const { token, user, updateUser, activeConvId, setActiveConvId, loadConversations } = useApp();
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef();
  const composerRef = useRef();
  const skipLoadRef = useRef(false);

  useEffect(() => {
    if (!activeConvId) { setMessages([]); return; }
    if (skipLoadRef.current) { skipLoadRef.current = false; return; }
    (async () => {
      try {
        const data = await api.getConversation(token, activeConvId);
        setMessages((data.messages || []).map((m) => ({
          id: m.id, role: m.role, content: m.content, image_url: m.image_url,
        })));
      } catch {
        setMessages([]);
      }
    })();
  }, [activeConvId, token]);

  useEffect(() => {
    // Scroll the messages container itself — never scrollIntoView, which can
    // shift ancestor scroll containers / the whole page.
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async ({ text, imageBase64 }) => {
    if (streaming) return;
    const assistantId = uid();
    let stepSeq = 0;

    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: text, image_url: imageBase64 ? "[image]" : null },
      { id: assistantId, role: "assistant", content: "", steps: [], sources: [], emotion: "thinking", streaming: true },
    ]);
    setStreaming(true);

    const patch = (fn) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)));

    if (!activeConvId) skipLoadRef.current = true;

    try {
      await api.streamChat(token, { message: text, conversationId: activeConvId, imageBase64 }, (ev) => {
        switch (ev.type) {
          case "conversation":
            if (!activeConvId) setActiveConvId(ev.conversation_id);
            break;
          case "emotion":
            patch((m) => ({ ...m, emotion: ev.value }));
            break;
          case "step":
            if (ev.status === "running") {
              patch((m) => ({
                ...m,
                steps: [...m.steps, { id: stepSeq++, name: ev.name, label: ev.label, detail: ev.detail, status: "running" }],
              }));
              if (ev.name === "finalizar_onboarding") updateUser({ is_onboarded: true });
            } else {
              patch((m) => {
                const steps = [...m.steps];
                const idx = steps.findIndex((s) => s.name === ev.name && s.status === "running");
                if (idx >= 0) steps[idx] = { ...steps[idx], status: "done" };
                return { ...m, steps };
              });
            }
            break;
          case "token":
            patch((m) => ({ ...m, content: m.content + ev.text }));
            break;
          case "sources":
            patch((m) => ({ ...m, sources: ev.value }));
            break;
          case "done":
            patch((m) => ({ ...m, content: ev.text || m.content, emotion: ev.emotion, streaming: false }));
            break;
          case "error":
            patch((m) => ({ ...m, content: "⚠️ " + ev.message, emotion: "sad", streaming: false }));
            break;
          default:
            break;
        }
      });
    } catch (err) {
      patch((m) => ({ ...m, content: "⚠️ " + err.message, emotion: "sad", streaming: false }));
    } finally {
      setStreaming(false);
      loadConversations();
    }
  }, [streaming, activeConvId, token, setActiveConvId, updateUser, loadConversations]);

  const sendDocument = useCallback(async ({ file, text }) => {
    if (streaming) return;
    const assistantId = uid();
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: text || `Subiendo: ${file.name}`, doc_name: file.name },
      { id: assistantId, role: "assistant", content: "", steps: [], sources: [], emotion: "thinking", streaming: true },
    ]);
    setStreaming(true);
    if (!activeConvId) skipLoadRef.current = true;
    try {
      const data = await api.sendChatWithDocument(token, file, text, activeConvId);
      if (!activeConvId) setActiveConvId(data.conversation_id);
      setMessages((prev) => prev.map((m) => (m.id === assistantId
        ? { ...m, content: data.response, sources: data.sources || [], emotion: data.emotion || "neutral", streaming: false }
        : m)));
    } catch (err) {
      setMessages((prev) => prev.map((m) => (m.id === assistantId
        ? { ...m, content: "⚠️ " + err.message, emotion: "sad", streaming: false }
        : m)));
    } finally {
      setStreaming(false);
      loadConversations();
    }
  }, [streaming, activeConvId, token, setActiveConvId, loadConversations]);

  const pickPreset = (prompt) => {
    if (prompt.trimEnd().endsWith(":")) {
      composerRef.current?.setText(prompt);
    } else {
      send({ text: prompt, imageBase64: null });
    }
  };

  const empty = messages.length === 0 && !activeConvId;
  const needsOnboarding = empty && user && !user.is_onboarded;

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto">
        {empty ? (
          needsOnboarding ? (
            <OnboardingWelcome onStart={() =>
              send({ text: "¡Hola Nova! Soy nuevo por aquí, me gustaría que me conozcas.", imageBase64: null })
            } />
          ) : (
            <PresetGrid userName={user?.name} onPick={pickPreset} />
          )
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
            {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
          </div>
        )}
      </div>
      <Composer ref={composerRef} onSend={send} onSendDocument={sendDocument} disabled={streaming} />
    </div>
  );
}
