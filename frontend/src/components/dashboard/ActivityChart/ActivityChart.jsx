function ActivityChart({ days }) {
  const maximum = Math.max(1, ...days.map((item) => item.count));
  const width = 600;
  const height = 140;
  const points = days
    .map((item, index) => {
      const x = days.length > 1 ? (index / (days.length - 1)) * width : 0;
      const y = height - (item.count / maximum) * (height - 18) - 8;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <article className="dashboard-chart-card">
      <header>
        <div>
          <h2>Nội dung tạo theo ngày</h2>
          <p>30 ngày gần nhất</p>
        </div>
        <span>Cao nhất: {maximum === 1 && !days.some((day) => day.count) ? 0 : maximum}</span>
      </header>
      <div className="activity-chart">
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Biểu đồ hoạt động">
          <defs>
            <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity=".28" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <polyline className="activity-chart__area" points={`0,${height} ${points} ${width},${height}`} />
          <polyline className="activity-chart__line" points={points} />
        </svg>
        <div className="activity-chart__labels">
          {days.filter((_, index) => index % 7 === 0 || index === days.length - 1).map((item) => (
            <span key={item.date}>
              {new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit" }).format(new Date(`${item.date}T00:00:00`))}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}

export default ActivityChart;
