import {
  FiBarChart2,
  FiBookmark,
  FiFolder,
  FiMessageSquare,
  FiSettings,
  FiGrid,
  FiBriefcase,
} from "react-icons/fi";

export const NAVIGATION_ITEMS = [
  { to: "/chat", label: "Chat", icon: FiMessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: FiBarChart2 },
  { to: "/library", label: "Thư viện", icon: FiBookmark },
  { to: "/templates", label: "Mẫu quảng cáo", icon: FiGrid },
  { to: "/brands", label: "Hồ sơ thương hiệu", icon: FiBriefcase },
  { to: "/campaigns", label: "Chiến dịch", icon: FiFolder },
  { to: "/settings", label: "Cài đặt", icon: FiSettings },
];
