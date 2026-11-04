type ParameterMetricProps = {
  label: string;
  value: string;
  note?: string;
  emphasis?: boolean;
};

export function ParameterMetric({
  label,
  value,
  note,
  emphasis = false,
}: ParameterMetricProps) {
  return (
    <article className={`three-left-metric ${emphasis ? "is-emphasis" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

