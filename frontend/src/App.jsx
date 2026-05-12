import { useState, useEffect, useRef } from 'react';
import { marked } from 'marked';
import * as api from './api';

marked.setOptions({ breaks: true, gfm: true });

/* ── Markdown renderer ──────────────────────────────────────────────────── */
function Md({ text }) {
  return (
    <div
      className="prose prose-sm max-w-none prose-invert prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-headings:my-2"
      dangerouslySetInnerHTML={{ __html: marked.parse(text || '') }}
    />
  );
}

/* ── Nova Face SVG — 8 moods ────────────────────────────────────────────── */
function NovaFace({ size = 40, mood = 'neutral' }) {
  const gradients = {
    neutral:   ['#6366f1', '#a855f7'],
    happy:     ['#6366f1', '#a855f7'],
    talking:   ['#4f46e5', '#7c3aed'],
    thinking:  ['#3730a3', '#6d28d9'],
    sad:       ['#1e1b4b', '#4338ca'],
    angry:     ['#7f1d1d', '#7c3aed'],
    surprised: ['#6366f1', '#ec4899'],
    excited:   ['#7c3aed', '#d97706'],
  };
  const [c1, c2] = gradients[mood] || gradients.neutral;
  const id = `ng-${mood}-${size}`;

  const wrapClass = {
    neutral:   'nova-idle',
    thinking:  'nova-thinking',
    happy:     'nova-bounce',
    talking:   '',
    sad:       'nova-idle',
    angry:     'nova-shake',
    surprised: '',
    excited:   'nova-bounce',
  }[mood] || 'nova-idle';

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none"
      xmlns="http://www.w3.org/2000/svg" className={wrapClass} style={{ display:'inline-block' }}>
      <defs>
        <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={c1} />
          <stop offset="100%" stopColor={c2} />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="46" fill={`url(#${id})`} />
      <circle cx="50" cy="50" r="40" fill="#1e1b4b" />

      {/* Antenna — all except angry */}
      {mood !== 'angry' && <>
        <line x1="50" y1="10" x2="50" y2="4" stroke="#a855f7" strokeWidth="2.5" />
        <circle cx="50" cy="3" r="3" fill="#c084fc" className="nova-glow" />
      </>}

      {/* ── NEUTRAL ── */}
      {mood === 'neutral' && <>
        <ellipse cx="36" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <ellipse cx="64" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <circle cx="38" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <circle cx="66" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <path d="M34 60 Q50 70 66 60" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <circle cx="18" cy="24" r="2" fill="#c084fc" opacity="0.6" />
        <circle cx="82" cy="20" r="1.5" fill="#a5b4fc" opacity="0.5" />
      </>}

      {/* ── THINKING ── */}
      {mood === 'thinking' && <>
        <ellipse cx="36" cy="42" rx="6" ry="5" fill="#a5b4fc" />
        <ellipse cx="64" cy="42" rx="6" ry="5" fill="#a5b4fc" />
        <circle cx="38" cy="40" r="2" fill="#fff" />
        <circle cx="65" cy="40" r="2" fill="#fff" />
        {/* raised eyebrow */}
        <path d="M30 34 Q36 30 42 33" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M58 33 Q64 30 70 34" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" />
        {/* hmm mouth */}
        <path d="M38 62 Q50 66 62 62" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        {/* thought dots */}
        <circle cx="68" cy="22" r="3.5" fill="#c084fc" className="nova-dot-1" />
        <circle cx="76" cy="14" r="2.5" fill="#a5b4fc" className="nova-dot-2" />
        <circle cx="82" cy="8"  r="2"   fill="#818cf8" className="nova-dot-3" />
      </>}

      {/* ── HAPPY ── */}
      {mood === 'happy' && <>
        {/* squinting happy eyes */}
        <path d="M30 44 Q36 38 42 44" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M58 44 Q64 38 70 44" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* big smile */}
        <path d="M28 58 Q50 76 72 58" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* cheeks */}
        <ellipse cx="28" cy="58" rx="7" ry="4" fill="#a855f7" opacity="0.35" />
        <ellipse cx="72" cy="58" rx="7" ry="4" fill="#a855f7" opacity="0.35" />
        {/* sparkles */}
        <path d="M16 20 L18 14 L20 20 L14 17 L22 17Z" fill="#c084fc" className="nova-sparkle-1" />
        <path d="M80 18 L82 12 L84 18 L78 15 L86 15Z" fill="#a5b4fc" className="nova-sparkle-2" />
        <path d="M14 68 L16 62 L18 68 L12 65 L20 65Z" fill="#818cf8" className="nova-sparkle-3" />
      </>}

      {/* ── TALKING ── */}
      {mood === 'talking' && <>
        <ellipse cx="36" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <ellipse cx="64" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <circle cx="38" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <circle cx="66" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        {/* animated open mouth */}
        <ellipse cx="50" cy="64" rx="10" ry="6" fill="#6366f1" className="nova-talk-mouth" />
        <ellipse cx="50" cy="64" rx="10" ry="6" stroke="#a5b4fc" strokeWidth="2" fill="none" />
        {/* sound wave lines */}
        <path d="M78 48 Q82 50 78 52" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.7" />
        <path d="M82 44 Q88 50 82 56" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.5" />
      </>}

      {/* ── SAD ── */}
      {mood === 'sad' && <>
        {/* eyebrows angled UP in the middle — classic sadness */}
        <path d="M29 40 Q36 33 43 38" stroke="#818cf8" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M57 38 Q64 33 71 40" stroke="#818cf8" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        {/* downcast watery eyes — looking slightly down */}
        <ellipse cx="36" cy="49" rx="5.5" ry="5" fill="#818cf8" />
        <ellipse cx="64" cy="49" rx="5.5" ry="5" fill="#818cf8" />
        {/* pupils look down */}
        <circle cx="36" cy="50" r="2" fill="#fff" />
        <circle cx="64" cy="50" r="2" fill="#fff" />
        {/* lower eyelid droop — puffy look */}
        <path d="M30.5 52 Q36 55 41.5 52" stroke="#6366f1" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <path d="M58.5 52 Q64 55 69.5 52" stroke="#6366f1" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        {/* deep frown */}
        <path d="M32 67 Q50 54 68 67" stroke="#818cf8" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* two tears — one falling */}
        <ellipse cx="35" cy="55" rx="2" ry="2.5" fill="#a5b4fc" opacity="0.9" className="nova-tear" />
        <ellipse cx="65" cy="57" rx="2" ry="2.5" fill="#a5b4fc" opacity="0.7" className="nova-tear" style={{animationDelay:'0.8s'}} />
      </>}

      {/* ── ANGRY ── */}
      {mood === 'angry' && <>
        {/* no antenna, red accent instead */}
        <circle cx="50" cy="5" r="4" fill="#ef4444" className="nova-glow" />
        {/* angry brows */}
        <path d="M28 36 L42 43" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M72 36 L58 43" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* narrowed eyes */}
        <ellipse cx="36" cy="47" rx="6" ry="4" fill="#fca5a5" />
        <ellipse cx="64" cy="47" rx="6" ry="4" fill="#fca5a5" />
        <circle cx="37" cy="46" r="1.8" fill="#7f1d1d" />
        <circle cx="65" cy="46" r="1.8" fill="#7f1d1d" />
        {/* tight frown */}
        <path d="M34 64 Q50 56 66 64" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* steam */}
        <path d="M16 30 Q14 24 16 18" stroke="#ef4444" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.8" />
        <path d="M84 30 Q86 24 84 18" stroke="#ef4444" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.8" />
        <path d="M12 33 Q10 26 12 20" stroke="#ef4444" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.5" />
        <path d="M88 33 Q90 26 88 20" stroke="#ef4444" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.5" />
      </>}

      {/* ── SURPRISED ── */}
      {mood === 'surprised' && <>
        {/* raised brows */}
        <path d="M29 34 Q36 28 43 32" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M57 32 Q64 28 71 34" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        {/* wide eyes */}
        <circle cx="36" cy="44" r="8" fill="#a5b4fc" />
        <circle cx="64" cy="44" r="8" fill="#a5b4fc" />
        <circle cx="38" cy="42" r="3.5" fill="#fff" />
        <circle cx="66" cy="42" r="3.5" fill="#fff" />
        <circle cx="39" cy="43" r="1.5" fill="#312e81" />
        <circle cx="67" cy="43" r="1.5" fill="#312e81" />
        {/* O mouth */}
        <ellipse cx="50" cy="65" rx="9" ry="8" fill="#6366f1" />
        <ellipse cx="50" cy="65" rx="9" ry="8" stroke="#a5b4fc" strokeWidth="2.5" fill="none" />
        {/* lines of shock */}
        <line x1="14" y1="18" x2="10" y2="12" stroke="#c084fc" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
        <line x1="86" y1="18" x2="90" y2="12" stroke="#c084fc" strokeWidth="2" strokeLinecap="round" opacity="0.7" />
      </>}

      {/* ── EXCITED ── */}
      {mood === 'excited' && <>
        {/* star eyes */}
        <path d="M36 38 L37.5 42 L42 44 L37.5 46 L36 50 L34.5 46 L30 44 L34.5 42Z" fill="#fbbf24" />
        <path d="M64 38 L65.5 42 L70 44 L65.5 46 L64 50 L62.5 46 L58 44 L62.5 42Z" fill="#fbbf24" />
        {/* huge smile */}
        <path d="M24 58 Q50 80 76 58" stroke="#a5b4fc" strokeWidth="3.5" fill="none" strokeLinecap="round" />
        {/* cheeks */}
        <ellipse cx="24" cy="60" rx="8" ry="5" fill="#a855f7" opacity="0.4" />
        <ellipse cx="76" cy="60" rx="8" ry="5" fill="#a855f7" opacity="0.4" />
        {/* sparkles × 3 */}
        <path d="M12 22 L14 16 L16 22 L10 19 L18 19Z" fill="#fbbf24" className="nova-sparkle-1" />
        <path d="M84 16 L86 10 L88 16 L82 13 L90 13Z" fill="#c084fc" className="nova-sparkle-2" />
        <path d="M50 6  L51.5 2 L53 6 L49 4 L55 4Z" fill="#a5b4fc" className="nova-sparkle-3" />
        <path d="M16 72 L18 66 L20 72 L14 69 L22 69Z" fill="#818cf8" className="nova-sparkle-1" />
      </>}
    </svg>
  );
}

/* Alias pequeño para el sidebar/login donde no cambia el mood */
function NovaIcon({ size = 40 }) {
  return <NovaFace size={size} mood="neutral" />;
}

/* ── Login Screen ───────────────────────────────────────────────────────── */
function LoginScreen({ onAuth }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = isRegister
        ? await api.register(email, password, name)
        : await api.login(email, password);
      onAuth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-indigo-950 to-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-gray-900/80 backdrop-blur rounded-2xl p-8 border border-indigo-500/20 shadow-xl shadow-indigo-500/10">
        <div className="flex flex-col items-center mb-6">
          <NovaIcon size={64} />
          <h1 className="text-2xl font-bold text-white mt-3">Nova Agent</h1>
          <p className="text-indigo-300/70 text-sm">Asistente inteligente con IA</p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {isRegister && (
            <input
              className="w-full bg-gray-800 text-white rounded-lg px-4 py-2.5 border border-gray-700 focus:border-indigo-500 focus:outline-none"
              placeholder="Nombre" value={name} onChange={e => setName(e.target.value)}
            />
          )}
          <input
            className="w-full bg-gray-800 text-white rounded-lg px-4 py-2.5 border border-gray-700 focus:border-indigo-500 focus:outline-none"
            type="email" placeholder="Correo electrónico" value={email} onChange={e => setEmail(e.target.value)} required
          />
          <input
            className="w-full bg-gray-800 text-white rounded-lg px-4 py-2.5 border border-gray-700 focus:border-indigo-500 focus:outline-none"
            type="password" placeholder="Contraseña" value={password} onChange={e => setPassword(e.target.value)} required
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg transition disabled:opacity-50"
          >
            {loading ? 'Cargando...' : isRegister ? 'Crear cuenta' : 'Iniciar sesión'}
          </button>
        </form>
        <p className="text-center text-gray-400 text-sm mt-4">
          {isRegister ? '¿Ya tienes cuenta?' : '¿No tienes cuenta?'}{' '}
          <button className="text-indigo-400 hover:underline" onClick={() => { setIsRegister(!isRegister); setError(''); }}>
            {isRegister ? 'Inicia sesión' : 'Regístrate'}
          </button>
        </p>
      </div>
    </div>
  );
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
function Sidebar({ conversations, activeId, onSelect, onNew, onDelete, onDocs, onLogout, user, showDocs }) {
  return (
    <div className="w-72 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-3 mb-4">
          <NovaIcon size={32} />
          <span className="font-bold text-white text-lg">Nova</span>
        </div>
        <button onClick={onNew} className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm py-2 rounded-lg transition">
          + Nueva conversación
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        <button onClick={() => onDocs(false)} className={`flex-1 py-2 text-xs font-medium transition ${!showDocs ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-gray-500 hover:text-gray-300'}`}>
          Chats
        </button>
        <button onClick={() => onDocs(true)} className={`flex-1 py-2 text-xs font-medium transition ${showDocs ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-gray-500 hover:text-gray-300'}`}>
          Documentos
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {!showDocs && conversations.map(c => (
          <div key={c.id}
            className={`group flex items-center rounded-lg px-3 py-2 cursor-pointer transition ${c.id === activeId ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}
            onClick={() => onSelect(c.id)}
          >
            <span className={`text-xs mr-1.5 shrink-0 ${
              c.mode === 'chef' ? 'text-orange-400' : 'text-indigo-400'
            }`}>{c.mode === 'chef' ? '👨‍🍳' : '🤖'}</span>
            <span className="flex-1 truncate text-sm">{c.titulo}</span>
            <button onClick={e => { e.stopPropagation(); onDelete(c.id); }}
              className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 ml-2 text-xs"
            >✕</button>
          </div>
        ))}
      </div>

      {/* User */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center justify-between">
          <div className="truncate">
            <p className="text-white text-sm font-medium truncate">{user?.name}</p>
            <p className="text-gray-500 text-xs truncate">{user?.email}</p>
          </div>
          <button onClick={onLogout} className="text-gray-500 hover:text-red-400 text-xs transition">Salir</button>
        </div>
      </div>
    </div>
  );
}

/* ── Documents Panel ────────────────────────────────────────────────────── */
function DocsPanel({ token }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

  const load = async () => {
    const data = await api.getDocuments(token);
    setDocs(data.documents || []);
  };
  useEffect(() => { load(); }, []);

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(token, file);
      await load();
    } catch (err) { alert(err.message); }
    finally { setUploading(false); fileRef.current.value = ''; }
  };

  const del = async (id) => {
    await api.deleteDocument(token, id);
    await load();
  };

  return (
    <div className="flex-1 flex flex-col bg-gray-950 p-6">
      <h2 className="text-xl font-bold text-white mb-4">Documentos de conocimiento</h2>
      <p className="text-gray-400 text-sm mb-6">Sube archivos PDF, Markdown o TXT para ampliar el conocimiento de Nova.</p>

      <label className={`inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg cursor-pointer transition w-fit mb-6 ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
        {uploading ? 'Subiendo...' : 'Subir documento'}
        <input ref={fileRef} type="file" accept=".pdf,.md,.txt" className="hidden" onChange={upload} />
      </label>

      {docs.length === 0
        ? <p className="text-gray-600 text-sm">No hay documentos aun.</p>
        : (
          <div className="space-y-2">
            {docs.map(d => (
              <div key={d.id} className="flex items-center justify-between bg-gray-900 rounded-lg px-4 py-3 border border-gray-800">
                <div>
                  <p className="text-white text-sm font-medium">{d.filename}</p>
                  <p className="text-gray-500 text-xs">{d.chunk_count} fragmentos &middot; {new Date(d.created_at).toLocaleDateString('es-MX')}</p>
                </div>
                <button onClick={() => del(d.id)} className="text-red-400 hover:text-red-300 text-xs">Eliminar</button>
              </div>
            ))}
          </div>
        )}
    </div>
  );
}

/* ── Chat Area ──────────────────────────────────────────────────────────── */
function ChatArea({ token, conversationId, setConversationId, onConversationsChanged, mode, setMode }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageBase64, setImageBase64] = useState(null);
  const [mood, setMood] = useState('neutral');
  const [pendingDoc, setPendingDoc] = useState(null); // { file, name }
  const endRef = useRef();
  const fileRef = useRef();
  const docRef = useRef();

  // Load conversation messages
  useEffect(() => {
    if (!conversationId) { setMessages([]); return; }
    (async () => {
      try {
        const data = await api.getConversation(token, conversationId);
        setMessages(data.messages || []);
      } catch { setMessages([]); }
    })();
  }, [conversationId, token]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleImagePick = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImagePreview(reader.result);
      setImageBase64(reader.result.split(',')[1]);
    };
    reader.readAsDataURL(file);
    fileRef.current.value = '';
  };

  const handleDocPick = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingDoc({ file, name: file.name });
    docRef.current.value = '';
  };

  const sendDocumentMessage = async () => {
    if (!pendingDoc) return;
    const { file } = pendingDoc;
    const msg = input.trim();
    const userMsg = { role: 'user', content: msg || `Subiendo: ${file.name}`, doc_name: file.name };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setPendingDoc(null);
    setSending(true);
    setMood('thinking');
    try {
      const data = await api.sendChatWithDocument(token, file, msg, conversationId, mode);
      if (!conversationId) {
        setConversationId(data.conversation_id);
        onConversationsChanged();
      }
      setMood(data.emotion || 'talking');
      setMessages(prev => [...prev, { role: 'assistant', content: data.response, emotion: data.emotion || 'neutral' }]);
      setTimeout(() => setMood('neutral'), 4000);
      onConversationsChanged(); // refresh docs panel count
    } catch (err) {
      setMood('sad');
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: ' + err.message, emotion: 'sad' }]);
      setTimeout(() => setMood('neutral'), 4000);
    } finally { setSending(false); }
  };

  const sendMessage = async () => {
    const msg = input.trim();
    if (!msg && !imageBase64) return;
    const userMsg = { role: 'user', content: msg || '(imagen adjunta)', image_url: imagePreview ? '[image]' : null };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    const sentImage = imageBase64;
    setImagePreview(null);
    setImageBase64(null);
    setSending(true);
    setMood('thinking');
    try {
      const data = await api.sendChat(token, msg || 'Analiza esta imagen', conversationId, sentImage, mode);
      if (!conversationId) {
        setConversationId(data.conversation_id);
        onConversationsChanged();
      }
      setMood(data.emotion || 'talking');
      setMessages(prev => [...prev, { role: 'assistant', content: data.response, emotion: data.emotion || 'neutral' }]);
      setTimeout(() => setMood('neutral'), 4000);
    } catch (err) {
      setMood('sad');
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: ' + err.message, emotion: 'sad' }]);
      setTimeout(() => setMood('neutral'), 4000);
    } finally { setSending(false); }
  };

  return (
    <div className="flex-1 flex flex-col bg-gray-950">
      {/* Mode toggle — pill at top */}
      <div className="flex items-center justify-center gap-1 px-4 py-2 border-b border-gray-800 bg-gray-900/60">
        {(conversationId || messages.length > 0) ? (
          // Locked: show only the active mode label
          <div className={`flex items-center gap-2 px-4 py-1 text-xs font-semibold rounded-full ${
            mode === 'chef' ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30' : 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
          }`}>
            <span>{mode === 'chef' ? '👨‍🍳 Chefsito' : '🤖 Nova'}</span>
            <span className="opacity-50 text-[10px]">fijo en este chat</span>
          </div>
        ) : (
          // Free: can switch
          <>
            <button
              onClick={() => setMode('nova')}
              className={`px-4 py-1 text-xs font-semibold rounded-full transition ${
                mode === 'nova'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >🤖 Nova</button>
            <button
              onClick={() => setMode('chef')}
              className={`px-4 py-1 text-xs font-semibold rounded-full transition ${
                mode === 'chef'
                  ? 'bg-orange-500 text-white shadow'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >👨‍🍳 Chefsito</button>
          </>
        )}
      </div>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <NovaFace size={90} mood={mood} />
            {mode === 'chef' ? (
              <>
                <h2 className="text-2xl font-bold text-white mt-4">Hola, soy Chefsito</h2>
                <p className="text-gray-400 mt-2 max-w-md">Tu asistente culinario personal. Cuéntame tus recetas favoritas, dime qué ingredientes tienes y te propongo un platillo increíble.</p>
              </>
            ) : (
              <>
                <h2 className="text-2xl font-bold text-white mt-4">Hola, soy Nova</h2>
                <p className="text-gray-400 mt-2 max-w-md">Tu asistente inteligente. Preguntame lo que quieras, sube documentos para ampliar mi conocimiento, o adjunta imagenes para que las analice.</p>
              </>
            )}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} items-end gap-2`}>
            {m.role === 'assistant' && (
              <NovaFace size={44} mood={m.emotion || 'neutral'} />
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
              m.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-md'
                : 'bg-gray-800 text-gray-100 rounded-bl-md border border-gray-700'}`}
            >
      {m.role === 'user' ? <p className="text-sm whitespace-pre-wrap">{m.content}</p> : <Md text={m.content} />}
              {m.image_url && <span className="text-xs opacity-60 block mt-1">Imagen adjunta</span>}
              {m.doc_name && (
                <span className="inline-flex items-center gap-1 text-xs mt-1 bg-indigo-900/50 text-indigo-300 rounded px-2 py-0.5">
                  📄 {m.doc_name}
                </span>
              )}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start items-end gap-2">
            <NovaFace size={44} mood="thinking" />
            <div className="bg-gray-800 text-gray-400 rounded-2xl rounded-bl-md px-4 py-3 border border-gray-700">
              <span className="animate-pulse">{mode === 'chef' ? 'Chefsito está cocinando...' : 'Nova está pensando...'}</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Image preview */}
      {imagePreview && (
        <div className="px-6 pb-2">
          <div className="relative inline-block">
            <img src={imagePreview} className="h-20 rounded-lg border border-gray-700" alt="preview" />
            <button onClick={() => { setImagePreview(null); setImageBase64(null); }}
              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center">✕</button>
          </div>
        </div>
      )}

      {/* PDF preview pill */}
      {pendingDoc && (
        <div className="px-6 pb-2">
          <div className="inline-flex items-center gap-2 bg-indigo-900/50 border border-indigo-500/30 rounded-lg px-3 py-1.5">
            <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="text-indigo-300 text-xs truncate max-w-[200px]">{pendingDoc.name}</span>
            <button onClick={() => setPendingDoc(null)} className="text-red-400 hover:text-red-300 text-xs">✕</button>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-end gap-2 max-w-4xl mx-auto">
          {/* Image attach */}
          <button onClick={() => fileRef.current?.click()}
            className="p-2.5 bg-gray-800 text-gray-400 hover:text-indigo-400 rounded-lg border border-gray-700 transition"
            title="Adjuntar imagen"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImagePick} />

          {/* PDF attach */}
          <button onClick={() => docRef.current?.click()}
            className={`p-2.5 rounded-lg border transition ${
              pendingDoc
                ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50'
                : 'bg-gray-800 text-gray-400 hover:text-indigo-400 border-gray-700'
            }`}
            title="Adjuntar PDF / documento"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </button>
          <input ref={docRef} type="file" accept=".pdf,.md,.txt" className="hidden" onChange={handleDocPick} />

          <textarea
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (pendingDoc) sendDocumentMessage();
                else sendMessage();
              }
            }}
            placeholder={pendingDoc ? `Mensaje sobre "${pendingDoc.name}" (opcional)...` : 'Escribe un mensaje...'}
            rows={1}
            className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2.5 border border-gray-700 focus:border-indigo-500 focus:outline-none resize-none text-sm"
          />
          <button
            onClick={pendingDoc ? sendDocumentMessage : sendMessage}
            disabled={sending || (!input.trim() && !imageBase64 && !pendingDoc)}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition disabled:opacity-40"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── App ─────────────────────────────────────────────────────────────────── */
export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('nova_token'));
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('nova_user')); } catch { return null; }
  });
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [showDocs, setShowDocs] = useState(false);
  const [mode, setMode] = useState('nova'); // persists across section changes

  const loadConversations = async () => {
    if (!token) return;
    const data = await api.getConversations(token);
    setConversations(data);
  };

  useEffect(() => { if (token) loadConversations(); }, [token]);

  const handleAuth = (data) => {
    setToken(data.access_token);
    const u = { name: data.name, email: data.email, id: data.user_id };
    setUser(u);
    localStorage.setItem('nova_token', data.access_token);
    localStorage.setItem('nova_user', JSON.stringify(u));
  };

  const logout = () => {
    setToken(null); setUser(null); setConversations([]); setActiveConvId(null);
    localStorage.removeItem('nova_token');
    localStorage.removeItem('nova_user');
  };

  // Auto-logout on any 401 from any component
  useEffect(() => { api.setUnauthorizedHandler(logout); }, []);

  const deleteConv = async (id) => {
    await api.deleteConversation(token, id);
    if (activeConvId === id) setActiveConvId(null);
    loadConversations();
  };

  if (!token || !user) return <LoginScreen onAuth={handleAuth} />;

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      <Sidebar
        conversations={conversations} activeId={activeConvId}
        onSelect={(id) => {
          setActiveConvId(id);
          setShowDocs(false);
          const conv = conversations.find(c => c.id === id);
          if (conv?.mode) setMode(conv.mode);
        }}
        onNew={() => { setActiveConvId(null); setShowDocs(false); }}
        onDelete={deleteConv} onDocs={setShowDocs} onLogout={logout}
        user={user} showDocs={showDocs}
      />
      {showDocs
        ? <DocsPanel token={token} />
        : <ChatArea token={token} conversationId={activeConvId}
            setConversationId={(id) => { setActiveConvId(id); }}
            onConversationsChanged={loadConversations}
            mode={mode} setMode={setMode}
          />
      }
    </div>
  );
}
