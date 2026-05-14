import { useRef, useState, useImperativeHandle, forwardRef } from "react";

const Composer = forwardRef(function Composer({ onSend, onSendDocument, disabled }, ref) {
  const [input, setInput] = useState("");
  const [imagePreview, setImagePreview] = useState(null);
  const [imageBase64, setImageBase64] = useState(null);
  const [pendingDoc, setPendingDoc] = useState(null);
  const imageRef = useRef();
  const docRef = useRef();

  // Lets parent prefill the input (used by presets / onboarding).
  useImperativeHandle(ref, () => ({
    setText: (t) => setInput(t),
  }));

  const pickImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImagePreview(reader.result);
      setImageBase64(reader.result.split(",")[1]);
    };
    reader.readAsDataURL(file);
    imageRef.current.value = "";
  };

  const pickDoc = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingDoc(file);
    docRef.current.value = "";
  };

  const submit = () => {
    const text = input.trim();
    if (disabled) return;
    if (pendingDoc) {
      onSendDocument({ file: pendingDoc, text });
      setPendingDoc(null);
      setInput("");
      return;
    }
    if (!text && !imageBase64) return;
    onSend({ text: text || "Analiza esta imagen", imageBase64 });
    setInput("");
    setImagePreview(null);
    setImageBase64(null);
  };

  const iconBtn = "glass rounded-xl p-2.5 text-muted hover:text-nova-violet transition";

  return (
    <div className="px-4 pb-4">
      <div className="max-w-3xl mx-auto">
        {(imagePreview || pendingDoc) && (
          <div className="flex gap-2 mb-2">
            {imagePreview && (
              <div className="relative">
                <img src={imagePreview} alt="preview" className="h-16 rounded-lg border border-white/10" />
                <button onClick={() => { setImagePreview(null); setImageBase64(null); }}
                  className="absolute -top-2 -right-2 bg-nova-pink text-white rounded-full w-5 h-5 text-xs">✕</button>
              </div>
            )}
            {pendingDoc && (
              <div className="glass inline-flex items-center gap-2 rounded-lg px-3 py-1.5">
                <span className="text-nova-cyan text-sm">📄</span>
                <span className="text-sm truncate max-w-[200px]">{pendingDoc.name}</span>
                <button onClick={() => setPendingDoc(null)} className="text-muted hover:text-nova-pink text-xs">✕</button>
              </div>
            )}
          </div>
        )}

        <div className="glass-strong rounded-2xl p-2 flex items-end gap-2 focus-within:glow-violet transition">
          <button onClick={() => imageRef.current?.click()} className={iconBtn} title="Adjuntar imagen">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>
          <input ref={imageRef} type="file" accept="image/*" className="hidden" onChange={pickImage} />

          <button onClick={() => docRef.current?.click()} className={iconBtn} title="Adjuntar documento">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <input ref={docRef} type="file" accept=".pdf,.md,.txt" className="hidden" onChange={pickDoc} />

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
            }}
            placeholder={pendingDoc ? `Mensaje sobre "${pendingDoc.name}" (opcional)…` : "Escribe un mensaje…"}
            rows={1}
            className="flex-1 bg-transparent outline-none resize-none text-[15px] py-2 max-h-40 placeholder:text-muted/70"
          />

          <button onClick={submit} disabled={disabled}
            className="btn-gradient text-white rounded-xl p-2.5 disabled:opacity-40">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
});

export default Composer;
