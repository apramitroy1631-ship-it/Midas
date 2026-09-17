import { Mail, Newspaper, Share2 } from "lucide-react";

/** lucide-react dropped brand marks a while back, so LinkedIn gets a small
 * hand-drawn glyph instead of a generic fallback — the whole point here is
 * telling channels apart at a glance. */
function LinkedInGlyph({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="1" y="1" width="22" height="22" rx="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="7.2" cy="7.7" r="1.6" />
      <rect x="6" y="10.3" width="2.4" height="8" />
      <path d="M11.3 10.3h2.3v1.3c.5-.8 1.4-1.5 3-1.5 2.4 0 3.4 1.6 3.4 4v4.9h-2.4v-4.5c0-1.2-.4-2-1.6-2-1 0-1.6.7-1.8 1.4-.1.2-.1.5-.1.8v4.3h-2.4c0-.1.03-7.7.03-8.7Z" />
    </svg>
  );
}

export function ChannelIcon({ channel, size = 14 }: { channel: string; size?: number }) {
  const c = channel.toLowerCase();
  if (c === "email" || c === "outlook") return <Mail size={size} />;
  if (c === "blog") return <Newspaper size={size} />;
  if (c === "linkedin") return <LinkedInGlyph size={size} />;
  return <Share2 size={size} />;
}
