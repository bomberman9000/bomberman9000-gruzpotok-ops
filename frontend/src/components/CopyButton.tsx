import { useState } from "react";

export function CopyButton({ text, label = "Копировать" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  const onClick = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setOk(true);
      setTimeout(() => setOk(false), 1500);
    } catch {
      window.prompt("Скопируйте вручную:", text);
    }
  };
  return (
    <button type="button" className={ok ? "primary" : undefined} onClick={onClick} style={{ fontSize: "0.85rem" }}>
      {ok ? "✓" : label}
    </button>
  );
}
