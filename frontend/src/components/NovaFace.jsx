/* Nova Face SVG — 8 expressive moods, animations live in index.css. */
export default function NovaFace({ size = 40, mood = "neutral" }) {
  const gradients = {
    neutral:   ["#6366f1", "#a855f7"],
    happy:     ["#6366f1", "#a855f7"],
    talking:   ["#4f46e5", "#7c3aed"],
    thinking:  ["#3730a3", "#6d28d9"],
    sad:       ["#1e1b4b", "#4338ca"],
    angry:     ["#7f1d1d", "#7c3aed"],
    surprised: ["#6366f1", "#ec4899"],
    excited:   ["#7c3aed", "#d97706"],
  };
  const [c1, c2] = gradients[mood] || gradients.neutral;
  const id = `ng-${mood}-${size}`;

  const wrapClass = {
    neutral:   "nova-idle",
    thinking:  "nova-thinking",
    happy:     "nova-bounce",
    talking:   "",
    sad:       "nova-idle",
    angry:     "nova-shake",
    surprised: "",
    excited:   "nova-bounce",
  }[mood] || "nova-idle";

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none"
      xmlns="http://www.w3.org/2000/svg" className={wrapClass} style={{ display: "inline-block" }}>
      <defs>
        <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={c1} />
          <stop offset="100%" stopColor={c2} />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="46" fill={`url(#${id})`} />
      <circle cx="50" cy="50" r="40" fill="#1e1b4b" />

      {mood !== "angry" && <>
        <line x1="50" y1="10" x2="50" y2="4" stroke="#a855f7" strokeWidth="2.5" />
        <circle cx="50" cy="3" r="3" fill="#c084fc" className="nova-glow" />
      </>}

      {mood === "neutral" && <>
        <ellipse cx="36" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <ellipse cx="64" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <circle cx="38" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <circle cx="66" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <path d="M34 60 Q50 70 66 60" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <circle cx="18" cy="24" r="2" fill="#c084fc" opacity="0.6" />
        <circle cx="82" cy="20" r="1.5" fill="#a5b4fc" opacity="0.5" />
      </>}

      {mood === "thinking" && <>
        <ellipse cx="36" cy="42" rx="6" ry="5" fill="#a5b4fc" />
        <ellipse cx="64" cy="42" rx="6" ry="5" fill="#a5b4fc" />
        <circle cx="38" cy="40" r="2" fill="#fff" />
        <circle cx="65" cy="40" r="2" fill="#fff" />
        <path d="M30 34 Q36 30 42 33" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M58 33 Q64 30 70 34" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M38 62 Q50 66 62 62" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <circle cx="68" cy="22" r="3.5" fill="#c084fc" className="nova-dot-1" />
        <circle cx="76" cy="14" r="2.5" fill="#a5b4fc" className="nova-dot-2" />
        <circle cx="82" cy="8"  r="2"   fill="#818cf8" className="nova-dot-3" />
      </>}

      {mood === "happy" && <>
        <path d="M30 44 Q36 38 42 44" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M58 44 Q64 38 70 44" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M28 58 Q50 76 72 58" stroke="#a5b4fc" strokeWidth="3" fill="none" strokeLinecap="round" />
        <ellipse cx="28" cy="58" rx="7" ry="4" fill="#a855f7" opacity="0.35" />
        <ellipse cx="72" cy="58" rx="7" ry="4" fill="#a855f7" opacity="0.35" />
        <path d="M16 20 L18 14 L20 20 L14 17 L22 17Z" fill="#c084fc" className="nova-sparkle-1" />
        <path d="M80 18 L82 12 L84 18 L78 15 L86 15Z" fill="#a5b4fc" className="nova-sparkle-2" />
        <path d="M14 68 L16 62 L18 68 L12 65 L20 65Z" fill="#818cf8" className="nova-sparkle-3" />
      </>}

      {mood === "talking" && <>
        <ellipse cx="36" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <ellipse cx="64" cy="44" rx="6" ry="7" fill="#a5b4fc" className="nova-blink" />
        <circle cx="38" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <circle cx="66" cy="42" r="2.5" fill="#fff" className="nova-blink" />
        <ellipse cx="50" cy="64" rx="10" ry="6" fill="#6366f1" />
        <ellipse cx="50" cy="64" rx="10" ry="6" stroke="#a5b4fc" strokeWidth="2" fill="none" />
        <path d="M78 48 Q82 50 78 52" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.7" />
        <path d="M82 44 Q88 50 82 56" stroke="#a5b4fc" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.5" />
      </>}

      {mood === "sad" && <>
        <path d="M29 40 Q36 33 43 38" stroke="#818cf8" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M57 38 Q64 33 71 40" stroke="#818cf8" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <ellipse cx="36" cy="49" rx="5.5" ry="5" fill="#818cf8" />
        <ellipse cx="64" cy="49" rx="5.5" ry="5" fill="#818cf8" />
        <circle cx="36" cy="50" r="2" fill="#fff" />
        <circle cx="64" cy="50" r="2" fill="#fff" />
        <path d="M32 67 Q50 54 68 67" stroke="#818cf8" strokeWidth="3" fill="none" strokeLinecap="round" />
        <ellipse cx="35" cy="55" rx="2" ry="2.5" fill="#a5b4fc" opacity="0.9" className="nova-tear" />
        <ellipse cx="65" cy="57" rx="2" ry="2.5" fill="#a5b4fc" opacity="0.7" className="nova-tear" style={{ animationDelay: "0.8s" }} />
      </>}

      {mood === "angry" && <>
        <circle cx="50" cy="5" r="4" fill="#ef4444" className="nova-glow" />
        <path d="M28 36 L42 43" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M72 36 L58 43" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        <ellipse cx="36" cy="47" rx="6" ry="4" fill="#fca5a5" />
        <ellipse cx="64" cy="47" rx="6" ry="4" fill="#fca5a5" />
        <circle cx="37" cy="46" r="1.8" fill="#7f1d1d" />
        <circle cx="65" cy="46" r="1.8" fill="#7f1d1d" />
        <path d="M34 64 Q50 56 66 64" stroke="#fca5a5" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M16 30 Q14 24 16 18" stroke="#ef4444" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.8" />
        <path d="M84 30 Q86 24 84 18" stroke="#ef4444" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.8" />
      </>}

      {mood === "surprised" && <>
        <path d="M29 34 Q36 28 43 32" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <path d="M57 32 Q64 28 71 34" stroke="#a5b4fc" strokeWidth="2.5" fill="none" strokeLinecap="round" />
        <circle cx="36" cy="44" r="8" fill="#a5b4fc" />
        <circle cx="64" cy="44" r="8" fill="#a5b4fc" />
        <circle cx="38" cy="42" r="3.5" fill="#fff" />
        <circle cx="66" cy="42" r="3.5" fill="#fff" />
        <ellipse cx="50" cy="65" rx="9" ry="8" fill="#6366f1" />
        <ellipse cx="50" cy="65" rx="9" ry="8" stroke="#a5b4fc" strokeWidth="2.5" fill="none" />
      </>}

      {mood === "excited" && <>
        <path d="M36 38 L37.5 42 L42 44 L37.5 46 L36 50 L34.5 46 L30 44 L34.5 42Z" fill="#fbbf24" />
        <path d="M64 38 L65.5 42 L70 44 L65.5 46 L64 50 L62.5 46 L58 44 L62.5 42Z" fill="#fbbf24" />
        <path d="M24 58 Q50 80 76 58" stroke="#a5b4fc" strokeWidth="3.5" fill="none" strokeLinecap="round" />
        <ellipse cx="24" cy="60" rx="8" ry="5" fill="#a855f7" opacity="0.4" />
        <ellipse cx="76" cy="60" rx="8" ry="5" fill="#a855f7" opacity="0.4" />
        <path d="M12 22 L14 16 L16 22 L10 19 L18 19Z" fill="#fbbf24" className="nova-sparkle-1" />
        <path d="M84 16 L86 10 L88 16 L82 13 L90 13Z" fill="#c084fc" className="nova-sparkle-2" />
        <path d="M50 6 L51.5 2 L53 6 L49 4 L55 4Z" fill="#a5b4fc" className="nova-sparkle-3" />
      </>}
    </svg>
  );
}
