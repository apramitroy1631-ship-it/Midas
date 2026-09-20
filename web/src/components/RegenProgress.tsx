import { useEffect, useState } from "react";

/**
 * What a regenerate is doing, shown while the (single, non-streaming) request
 * is in flight. The server doesn't report stages, so these are honest
 * estimates keyed to elapsed time and labelled as such - the point is that a
 * 30-90s wait (write, review, and revise if the review flags anything)
 * reads as visible work instead of a frozen button.
 */
const STAGES = [
  { label: "Reading your feedback", from: 0 },
  { label: "Rewriting the draft", from: 3 },
  { label: "Reviewing it against your brand rules", from: 18 },
  { label: "Revising if the review flags anything", from: 36 },
  { label: "Re-reviewing the revision", from: 55 },
];

export function RegenProgress() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const id = setInterval(() => setElapsed((Date.now() - started) / 1000), 250);
    return () => clearInterval(id);
  }, []);

  const active = STAGES.reduce((acc, s, i) => (elapsed >= s.from ? i : acc), 0);
  // Eases toward ~92% and never claims to be finished before the server says so.
  const percent = 92 * (1 - Math.exp(-elapsed / 40));
  const slow = elapsed > 100;

  return (
    <div className="regen-progress" role="status" aria-live="polite">
      <div className="regen-bar">
        <div className="regen-bar-fill" style={{ width: percent + "%" }} />
      </div>
      <ul className="regen-steps">
        {STAGES.map((s, i) => (
          <li key={s.label} className={i < active ? "done" : i === active ? "active" : ""}>
            <span className="regen-step-mark">
              {i < active ? "✓" : i === active ? <span className="dot pulse" style={{ background: "currentColor" }} /> : "○"}
            </span>
            {s.label}
          </li>
        ))}
      </ul>
      <div className="dim" style={{ fontSize: 11 }}>
        {Math.floor(elapsed)}s ·{" "}
        {slow ? "Taking longer than usual — the AI service may be busy. Still working." : "usually 20–90 seconds; it repeats review and revise if needed (stages are estimates)"}
      </div>
    </div>
  );
}
