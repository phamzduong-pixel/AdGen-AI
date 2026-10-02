import { useCallback, useEffect, useState } from "react";
import { FiLogOut, FiMonitor, FiRefreshCw, FiShield } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import useAuth from "../../../hooks/useAuth";
import {
  getSessions,
  logoutAllSessions,
  revokeSession,
} from "../../../services/api/authApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import Modal from "../../ui/Modal/Modal";
import useToast from "../../ui/Toast/useToast";

import "./ActiveSessions.css";

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatDate(value) {
  return dateFormatter.format(new Date(value));
}

function ActiveSessions() {
  const navigate = useNavigate();
  const toast = useToast();
  const { logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState("");
  const [showLogoutAll, setShowLogoutAll] = useState(false);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      setSessions(await getSessions());
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể tải danh sách thiết bị."),
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    let active = true;
    getSessions()
      .then((data) => {
        if (active) setSessions(data);
      })
      .catch((error) => {
        if (active) {
          toast.error(
            getUserErrorMessage(error, "Không thể tải danh sách thiết bị."),
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [toast]);

  const handleRevoke = async (session) => {
    if (pendingId) return;
    setPendingId(session.id);
    try {
      await revokeSession(session.id);
      if (session.is_current) {
        await logout({ revoke: false });
        navigate("/login", { replace: true });
        return;
      }
      setSessions((current) =>
        current.filter((item) => item.id !== session.id),
      );
      toast.success("Đã đăng xuất khỏi thiết bị.");
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể thu hồi phiên đăng nhập."),
      );
    } finally {
      setPendingId("");
    }
  };

  const handleLogoutAll = async () => {
    if (pendingId) return;
    setPendingId("all");
    try {
      await logoutAllSessions();
      await logout({ revoke: false });
      setShowLogoutAll(false);
      sessionStorage.setItem(
        "adgen_auth_message",
        "Bạn đã đăng xuất khỏi tất cả thiết bị.",
      );
      navigate("/login", { replace: true });
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể đăng xuất tất cả thiết bị."),
      );
    } finally {
      setPendingId("");
    }
  };

  return (
    <>
      <section className="settings-section active-sessions">
        <header>
          <FiShield />
          <div>
            <h2>Thiết bị đã đăng nhập</h2>
            <p>Kiểm tra và thu hồi các phiên đang truy cập tài khoản.</p>
          </div>
          <button
            type="button"
            className="active-sessions__refresh"
            onClick={loadSessions}
            disabled={loading}
            aria-label="Tải lại danh sách thiết bị"
          >
            <FiRefreshCw />
          </button>
        </header>

        {loading ? (
          <p className="active-sessions__status">Đang tải thiết bị...</p>
        ) : sessions.length === 0 ? (
          <p className="active-sessions__status">
            Không có phiên đăng nhập đang hoạt động.
          </p>
        ) : (
          <div className="active-sessions__list">
            {sessions.map((session) => (
              <article className="active-session" key={session.id}>
                <span className="active-session__icon"><FiMonitor /></span>
                <div className="active-session__content">
                  <div className="active-session__title">
                    <strong>{session.device_name}</strong>
                    {session.is_current && <span>Thiết bị hiện tại</span>}
                  </div>
                  <p>{session.browser}{session.ip_address ? ` · ${session.ip_address}` : ""}</p>
                  <small>
                    Đăng nhập {formatDate(session.created_at)} · Hoạt động gần nhất{" "}
                    {formatDate(session.last_active_at)}
                  </small>
                </div>
                <button
                  type="button"
                  onClick={() => handleRevoke(session)}
                  disabled={Boolean(pendingId)}
                >
                  <FiLogOut />
                  {pendingId === session.id ? "Đang đăng xuất..." : "Đăng xuất"}
                </button>
              </article>
            ))}
          </div>
        )}

        <button
          type="button"
          className="active-sessions__logout-all"
          onClick={() => setShowLogoutAll(true)}
          disabled={loading || sessions.length === 0 || Boolean(pendingId)}
        >
          <FiLogOut />
          Đăng xuất khỏi tất cả thiết bị
        </button>
      </section>

      <Modal
        open={showLogoutAll}
        title="Đăng xuất tất cả thiết bị?"
        onClose={() => setShowLogoutAll(false)}
        closeDisabled={pendingId === "all"}
        footer={
          <div className="active-sessions__modal-actions">
            <button
              type="button"
              onClick={() => setShowLogoutAll(false)}
              disabled={pendingId === "all"}
            >
              Hủy
            </button>
            <button
              type="button"
              className="is-danger"
              onClick={handleLogoutAll}
              disabled={pendingId === "all"}
            >
              {pendingId === "all" ? "Đang đăng xuất..." : "Đăng xuất tất cả"}
            </button>
          </div>
        }
      >
        <p>
          Tất cả phiên, bao gồm thiết bị hiện tại, sẽ bị thu hồi và cần đăng
          nhập lại.
        </p>
      </Modal>
    </>
  );
}

export default ActiveSessions;
