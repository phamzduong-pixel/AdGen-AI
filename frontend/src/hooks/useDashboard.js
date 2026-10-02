import { useCallback, useEffect, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  getDashboardActivity,
  getDashboardPlatformUsage,
  getDashboardSummary,
} from "../services/api/dashboardApi";
import { getUserErrorMessage } from "../utils/apiError";

function useDashboard() {
  const toast = useToast();
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState([]);
  const [platforms, setPlatforms] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, activityData, platformData] = await Promise.all([
        getDashboardSummary(),
        getDashboardActivity(),
        getDashboardPlatformUsage(),
      ]);
      setSummary(summaryData);
      setActivity(activityData?.days || []);
      setPlatforms(platformData?.platforms || []);
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể tải dữ liệu Dashboard."),
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    // Synchronize aggregated dashboard data on page entry.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadDashboard();
  }, [loadDashboard]);

  return { summary, activity, platforms, loading, reload: loadDashboard };
}

export default useDashboard;
