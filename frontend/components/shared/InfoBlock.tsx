export default function InfoBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="status-card">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}
