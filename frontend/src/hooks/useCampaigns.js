import { useCallback, useEffect, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  createCampaign as createCampaignApi,
  deleteCampaign as deleteCampaignApi,
  getCampaigns,
  updateCampaign as updateCampaignApi,
} from "../services/api/campaignApi";
import { getUserErrorMessage } from "../utils/apiError";

function useCampaigns(filters) {
  const toast = useToast();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getCampaigns(filters);
      setCampaigns(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể tải danh sách chiến dịch."),
      );
    } finally {
      setLoading(false);
    }
  }, [filters, toast]);

  useEffect(() => {
    const timer = window.setTimeout(loadCampaigns, 180);
    return () => window.clearTimeout(timer);
  }, [loadCampaigns]);

  const createCampaign = async (data) => {
    setPending(true);
    try {
      const created = await createCampaignApi(data);
      setCampaigns((current) => [created, ...current]);
      toast.success("Đã tạo chiến dịch.");
      return created;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tạo chiến dịch."));
      return null;
    } finally {
      setPending(false);
    }
  };

  const updateCampaign = async (campaignId, data) => {
    setPending(true);
    try {
      const updated = await updateCampaignApi(campaignId, data);
      setCampaigns((current) =>
        current.map((item) => (item.id === campaignId ? updated : item)),
      );
      toast.success("Đã cập nhật chiến dịch.");
      return updated;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật chiến dịch."));
      return null;
    } finally {
      setPending(false);
    }
  };

  const deleteCampaign = async (campaignId) => {
    setPending(true);
    try {
      await deleteCampaignApi(campaignId);
      setCampaigns((current) =>
        current.filter((item) => item.id !== campaignId),
      );
      toast.info("Đã xóa chiến dịch. Nội dung thư viện vẫn được giữ nguyên.");
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể xóa chiến dịch."));
      return false;
    } finally {
      setPending(false);
    }
  };

  return {
    campaigns,
    loading,
    pending,
    createCampaign,
    updateCampaign,
    deleteCampaign,
    reload: loadCampaigns,
  };
}

export default useCampaigns;
