type Props = { label: string; value: string; hint?: string };

export function ScoreCard({ label, value, hint }: Props) {
  return (
    <article className="score-card">
      <p>{label}</p>
      <strong>{value}</strong>
      {hint && <span>{hint}</span>}
    </article>
  );
}
