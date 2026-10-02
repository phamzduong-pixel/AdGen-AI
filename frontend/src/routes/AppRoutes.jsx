import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import Login from "../pages/Login";
import Register from "../pages/Register";
import NotFound from "../pages/NotFound";
import ProtectedRoute from "../components/auth/ProtectedRoute";

const Chat = lazy(() => import("../pages/Chat"));
const Settings = lazy(() => import("../pages/Settings"));
const Dashboard = lazy(() => import("../pages/Dashboard"));
const Campaigns = lazy(() => import("../pages/Campaigns"));
const CampaignDetail = lazy(() => import("../pages/CampaignDetail"));
const Library = lazy(() => import("../pages/Library"));
const Profile = lazy(() => import("../pages/Profile"));
const Templates = lazy(() => import("../pages/Templates"));
const ForgotPassword = lazy(() => import("../pages/ForgotPassword"));
const VerifyResetCode = lazy(() => import("../pages/VerifyResetCode"));
const ResetPassword = lazy(() => import("../pages/ResetPassword"));
const VerifyEmail = lazy(() => import("../pages/VerifyEmail"));
const Brands = lazy(() => import("../pages/Brands"));
const ContentEditor = lazy(() => import("../pages/ContentEditor"));

function ProtectedLazyPage({ children }) {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="route-loading">Đang tải...</div>}>
        {children}
      </Suspense>
    </ProtectedRoute>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route path="/login" element={<Login />} />

      <Route path="/register" element={<Register />} />
      <Route
        path="/verify-email"
        element={
          <Suspense fallback={<div className="route-loading">Đang tải...</div>}>
            <VerifyEmail />
          </Suspense>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <Suspense fallback={<div className="route-loading">Đang tải...</div>}>
            <ForgotPassword />
          </Suspense>
        }
      />
      <Route
        path="/verify-reset-code"
        element={
          <Suspense fallback={<div className="route-loading">Đang tải...</div>}>
            <VerifyResetCode />
          </Suspense>
        }
      />
      <Route
        path="/reset-password"
        element={
          <Suspense fallback={<div className="route-loading">Đang tải...</div>}>
            <ResetPassword />
          </Suspense>
        }
      />

      <Route path="/chat" element={<ProtectedLazyPage><Chat /></ProtectedLazyPage>} />
      <Route path="/settings" element={<ProtectedLazyPage><Settings /></ProtectedLazyPage>} />
      <Route path="/profile" element={<ProtectedLazyPage><Profile /></ProtectedLazyPage>} />
      <Route path="/dashboard" element={<ProtectedLazyPage><Dashboard /></ProtectedLazyPage>} />
      <Route path="/library" element={<ProtectedLazyPage><Library /></ProtectedLazyPage>} />
      <Route path="/brands" element={<ProtectedLazyPage><Brands /></ProtectedLazyPage>} />
      <Route path="/contents/:contentId" element={<ProtectedLazyPage><ContentEditor /></ProtectedLazyPage>} />
      <Route
        path="/templates"
        element={
          <ProtectedLazyPage>
            <Templates />
          </ProtectedLazyPage>
        }
      />
      <Route path="/campaigns" element={<ProtectedLazyPage><Campaigns /></ProtectedLazyPage>} />
      <Route path="/campaigns/:campaignId" element={<ProtectedLazyPage><CampaignDetail /></ProtectedLazyPage>} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default AppRoutes;
