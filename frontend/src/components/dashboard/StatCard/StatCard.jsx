function StatCard({ icon: Icon, label, value, detail }) {
  return (
    <article className="dashboard-stat-card">
      <span><Icon /></span>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        {detail && <small>{detail}</small>}
      </div>
    </article>
  );
}

export default StatCard;
