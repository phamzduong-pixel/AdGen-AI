import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import {
  FiLogOut,
  FiMoon,
  FiMoreHorizontal,
  FiSettings,
  FiSun,
  FiUser,
  FiX,
} from "react-icons/fi";

import useAuth from "../../../../hooks/useAuth";
import "./SidebarFooter.css";

function SidebarFooter({ collapsed = false, user = null }) {
  const { user: contextUser, logout: logoutSession } = useAuth();
  const account = contextUser || user;
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [dark, setDark] = useState(
    () => localStorage.getItem("adgen_theme") === "dark",
  );
  const displayName = account?.username || account?.name || "Người dùng";
  const email = account?.email || "Tài khoản AdGen AI";
  const initials = displayName.trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") closeMenu();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen, closeMenu]);

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    localStorage.setItem("adgen_theme", next ? "dark" : "light");
    document.documentElement.dataset.theme = next ? "dark" : "light";
  };
  const logout = async () => {
    await logoutSession();
    navigate("/login", { replace: true });
  };

  return (
    <div className="sidebar-footer">
      <div className={`sidebar-user ${collapsed ? "sidebar-user--collapsed" : ""}`}>
        <div className="sidebar-user__avatar"><span>{initials}</span></div>
        {!collapsed && (
          <>
            <div className="sidebar-user__info"><strong>{displayName}</strong><span>{email}</span></div>
            <button type="button" className="sidebar-user__more" onClick={() => setMenuOpen((value) => !value)} aria-label="Tùy chọn tài khoản"><FiMoreHorizontal /></button>
          </>
        )}
        {collapsed && <button type="button" className="sidebar-user__more" onClick={() => setMenuOpen(true)}><FiMoreHorizontal /></button>}
      </div>

      {menuOpen && createPortal(
        <>
          <button type="button" className="account-menu__dismiss" onClick={closeMenu} aria-label="Đóng menu" />
          <div className="account-menu">
            <button type="button" onClick={() => { closeMenu(); navigate("/profile"); }}><FiUser />Xem hồ sơ</button>
            <button type="button" onClick={() => navigate("/settings")}><FiSettings />Cài đặt</button>
            <button type="button" onClick={toggleTheme}>{dark ? <FiSun /> : <FiMoon />}{dark ? "Giao diện sáng" : "Giao diện tối"}</button>
            <button type="button" className="account-menu__danger" onClick={logout}><FiLogOut />Đăng xuất</button>
          </div>
        </>, document.body,
      )}

      {profileOpen && createPortal(
        <div className="profile-modal" role="dialog" aria-modal="true">
          <button type="button" className="profile-modal__backdrop" onClick={() => setProfileOpen(false)} aria-label="Đóng" />
          <div className="profile-modal__panel">
            <button type="button" className="profile-modal__close" onClick={() => setProfileOpen(false)}><FiX /></button>
            <div className="profile-modal__avatar">{initials}</div>
            <h2>{displayName}</h2><p>{email}</p>
          </div>
        </div>, document.body,
      )}
    </div>
  );
}

export default SidebarFooter;
