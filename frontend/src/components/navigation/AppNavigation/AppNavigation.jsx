import { NavLink } from "react-router-dom";

import { NAVIGATION_ITEMS } from "./navigationItems";
import "./AppNavigation.css";

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
