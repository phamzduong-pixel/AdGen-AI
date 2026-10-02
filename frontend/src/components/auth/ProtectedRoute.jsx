import { Navigate, useLocation } from "react-router-dom";

import tokenStorage from "../../services/storage/tokenStorage";

function ProtectedRoute({ children }) {
  const location = useLocation();
  if (!tokenStorage.hasAccessToken()) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export default ProtectedRoute;
