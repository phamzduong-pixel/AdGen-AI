import {
  FiBarChart2,
  FiBookmark,
  FiLayers,
  FiMessageSquare,
  FiStar,
  FiTrendingUp,
} from "react-icons/fi";

import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import ActivityChart from "../../components/dashboard/ActivityChart/ActivityChart";
import PlatformChart from "../../components/dashboard/PlatformChart/PlatformChart";
import StatCard from "../../components/dashboard/StatCard/StatCard";
import useDashboard from "../../hooks/useDashboard";
import "./Dashboard.css";

const PLATFORM_LABELS = {
  facebook: "Facebook",
  google_ads: "Google Ads",
  landing_page: "Landing Page",
  instagram: "Instagram",
  tiktok: "TikTok",
  email: "Email Marketing",
};

function Dashboard() {
  const { summary, activity, platforms, loading } = useDashboard();

  return (
    <WorkspaceLayout
      title="Dashboard"
      subtitle="Tổng quan hoạt động sáng tạo nội dung của bạn"
    >
      {loading ? (
        <div className="dashboard-skeleton">
          {Array.from({ length: 8 }, (_, index) => <span key={index} />)}
        </div>
      ) : summary ? (
        <>
          <section className="dashboard-stats">
            <StatCard icon={FiMessageSquare} label="Cuộc hội thoại" value={summary.total_conversations} />
            <StatCard icon={FiTrendingUp} label="Nội dung đã tạo" value={summary.total_generated_contents} detail={`${summary.contents_last_7_days} trong 7 ngày`} />
            <StatCard icon={FiBookmark} label="Nội dung đã lưu" value={summary.total_saved_contents} />
            <StatCard icon={FiStar} label="Lần đánh giá" value={summary.total_evaluations} />
            <StatCard icon={FiLayers} label="Phiên bản A/B" value={summary.total_variants} />
            <StatCard icon={FiBarChart2} label="Nền tảng phổ biến" value={PLATFORM_LABELS[summary.top_platform] || summary.top_platform || "Chưa có"} detail={`${summary.contents_last_30_days} nội dung trong 30 ngày`} />
          </section>

          {summary.total_generated_contents === 0 ? (
            <div className="dashboard-empty">
              <FiBarChart2 />
              <h2>Chưa có dữ liệu thống kê</h2>
              <p>Bắt đầu tạo nội dung trong Chat để Dashboard hiển thị hoạt động.</p>
            </div>
          ) : (
            <section className="dashboard-charts">
              <ActivityChart days={activity} />
              <PlatformChart platforms={platforms} />
            </section>
          )}
        </>
      ) : null}
    </WorkspaceLayout>
  );
}

export default Dashboard;
