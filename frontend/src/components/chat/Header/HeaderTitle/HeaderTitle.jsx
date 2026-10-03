import "./HeaderTitle.css";

function HeaderTitle({ title = "Cuộc trò chuyện mới" }) {
  return (
    <div className="header-title">
      <div className="header-title__content">
        <h2>{title}</h2>

        <div className="header-title__status">
          <span className="header-title__status-dot" />
          <span>AdGen AI đang sẵn sàng</span>
        </div>
      </div>
    </div>
  );
}

export default HeaderTitle;
