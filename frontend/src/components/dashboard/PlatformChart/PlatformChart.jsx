const LABELS = {
  facebook: "Facebook",
  google_ads: "Google Ads",
  landing_page: "Landing Page",
  instagram: "Instagram",
  tiktok: "TikTok",
  email: "Email Marketing",
};

function PlatformChart({ platforms }) {
  return (
    <article className="dashboard-chart-card platform-chart">
      <header>
        <div>
          <h2>Tỷ lệ nền tảng</h2>
          <p>Mức sử dụng và điểm trung bình</p>
        </div>
      </header>
      <div className="platform-chart__list">
        {platforms.map((item) => (
          <div className="platform-chart__item" key={item.platform}>
            <div>
              <strong>{LABELS[item.platform] || item.platform}</strong>
              <span>
                {item.count} nội dung · {item.percentage}%
                {item.average_score != null && ` · ${item.average_score} điểm`}
              </span>
            </div>
            <progress max="100" value={item.percentage} />
          </div>
        ))}
      </div>
    </article>
  );
}

export default PlatformChart;
