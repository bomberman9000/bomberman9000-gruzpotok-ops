export function StatusBadge({ value }: { value: string }) {
  const v = value.toLowerCase();
  let cls = "";
  if (v.includes("ok") || v.includes("accepted")) cls = "ok";
  else if (v.includes("insufficient") || v.includes("pending") || v.includes("review")) cls = "warn";
  else if (v.includes("error") || v.includes("reject") || v.includes("unavailable")) cls = "danger";
  return <span className={`badge ${cls}`}>{value}</span>;
}
