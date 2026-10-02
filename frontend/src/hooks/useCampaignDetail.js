import { useCallback, useEffect, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  addCampaignContent,
  getCampaign,
  removeCampaignContent,
  setCampaignPrimaryContent,
  updateCampaign,
} from "../services/api/campaignApi";
import { getUserErrorMessage } from "../utils/apiError";

function useCampaignDetail(campaignId) {
  const toast = useToast();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setCampaign(await getCampaign(campaignId));
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải chiến dịch."));
    } finally {
      setLoading(false);
    }
  }, [campaignId, toast]);

  useEffect(() => {
    // Load the selected campaign and its owned content links.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const mutate = async (operation, successMessage) => {
    setPending(true);
    try {
      const updated = await operation();
      setCampaign(updated);
      if (successMessage) toast.success(successMessage);
      return updated;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật chiến dịch."));
      return null;
    } finally {
      setPending(false);
    }
  };

  return {
    campaign,
    loading,
    pending,
    addContent: (savedContentId) =>
      mutate(
        () => addCampaignContent(campaignId, savedContentId),
        "Đã thêm nội dung vào chiến dịch.",
      ),
    removeContent: (savedContentId) =>
      mutate(
        () => removeCampaignContent(campaignId, savedContentId),
        "Đã xóa liên kết nội dung khỏi chiến dịch.",
      ),
    setPrimary: async (savedContentId) => {
      const previous = campaign;
      setCampaign((current) =>
        current
          ? {
              ...current,
              contents: current.contents.map((item) => ({
                ...item,
                is_primary: item.saved_content.id === savedContentId,
              })),
            }
          : current,
      );
      setPending(true);
      try {
        const updated = await setCampaignPrimaryContent(
          campaignId,
          savedContentId,
        );
        setCampaign(updated);
        toast.success("Đã chọn phiên bản chính.");
        return updated;
      } catch (error) {
        setCampaign(previous);
        toast.error(
          getUserErrorMessage(error, "Không thể chọn phiên bản chính."),
        );
        return null;
      } finally {
        setPending(false);
      }
    },
    updateDetails: async (data) => {
      setPending(true);
      try {
        const updated = await updateCampaign(campaignId, data);
        if (updated) {
          setCampaign((current) => ({ ...current, ...updated }));
          toast.success("Đã cập nhật chiến dịch.");
        }
        return updated;
      } catch (error) {
        toast.error(
          getUserErrorMessage(error, "Không thể cập nhật chiến dịch."),
        );
        return null;
      } finally {
        setPending(false);
      }
    },
    reload: load,
  };
}

export default useCampaignDetail;
