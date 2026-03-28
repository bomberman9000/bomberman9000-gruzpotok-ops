import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function CaseEntry() {
  const nav = useNavigate();
  const [kind, setKind] = useState("claim");
  const [entityId, setEntityId] = useState("");

  const go = () => {
    const id = entityId.trim();
    if (!id) return;
    nav(`/panels/${kind}/${encodeURIComponent(id)}`);
  };

  return (
    <div>
      <h1>Панель кейса</h1>
      <p className="muted">Открыть агрегированную панель по сущности (данные из ai_calls)</p>
      <div className="row stack" style={{ maxWidth: 400 }}>
        <label className="stack">
          Тип
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="claim">Претензия (claim)</option>
            <option value="freight">Перевозка (freight)</option>
            <option value="document">Документ</option>
            <option value="request">По request_id</option>
          </select>
        </label>
        <label className="stack">
          ID
          <input value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="идентификатор" />
        </label>
        <button type="button" className="primary" onClick={go}>
          Открыть
        </button>
      </div>
    </div>
  );
}
