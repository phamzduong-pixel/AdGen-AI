import {
  FiBarChart2,
  FiBookmark,
  FiFolder,
  FiMessageSquare,
  FiSettings,
  FiGrid,
  FiBriefcase,
} from "react-icons/fi";
import { NavLink } from "react-router-dom";

import "./AppNavigation.css";

export const NAVIGATION_ITEMS = [
  { to: "/chat", label: "Chat", icon: FiMessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: FiBarChart2 },
  { to: "/library", label: "Thư viện", icon: FiBookmark },
  { to: "/templates", label: "Mẫu quảng cáo", icon: FiGrid },
  { to: "/brands", label: "Hồ sơ thương hiệu", icon: FiBriefcase },
  { to: "/campaigns", label: "Chiến dịch", icon: FiFolder },
  { to: "/settings", label: "Cài đặt", icon: FiSettings },
];

function AppNavigation({ compact = false, items = NAVIGATION_ITEMS }) {
  return (
    <nav className={`app-navigation ${compact ? "app-navigation--compact" : ""}`}>
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `app-navigation__item ${isActive ? "is-active" : ""}`
          }
          title={label}
        >
          <Icon />
          {!compact && <span>{label}</span>}
        </NavLink>
      ))}
    </nav>
  );
}

export default AppNavigation;
