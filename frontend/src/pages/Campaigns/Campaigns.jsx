import { useMemo, useState } from "react";
import { FiFolder, FiPlus } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import CampaignCard from "../../components/campaign/CampaignCard/CampaignCard";
import CampaignFilters from "../../components/campaign/CampaignFilters/CampaignFilters";
import CampaignFormModal from "../../components/campaign/CampaignFormModal/CampaignFormModal";
import Modal from "../../components/ui/Modal/Modal";
import useCampaigns from "../../hooks/useCampaigns";
import useBrands from "../../hooks/useBrands";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import "./Campaigns.css";

function Campaigns() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState({ query: "", status: "", platform: "" });
  const stableFilters = useMemo(
    () => filters,
    [filters],
  );
  const {
    campaigns,
    loading,
    pending,
    createCampaign,
    updateCampaign,
    deleteCampaign,
  } = useCampaigns(stableFilters);
  const { brands } = useBrands();
  const [formCampaign, setFormCampaign] = useState(undefined);
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  return (
    <WorkspaceLayout
      title="Chiến dịch"
      subtitle="Tổ chức nội dung quảng cáo theo mục tiêu và nền tảng"
      actions={
        <button
          type="button"
          className="campaign-page__create"
          onClick={() => { setFormCampaign(undefined); setFormOpen(true); }}
        >
          <FiPlus /> Tạo chiến dịch
        </button>
      }
    >
      <CampaignFilters filters={filters} onChange={setFilters} />
      {loading ? (
        <div className="campaign-page__skeleton">
          {Array.from({ length: 6 }, (_, index) => <span key={index} />)}
        </div>
      ) : campaigns.length ? (
        <div className="campaign-page__grid">
          {campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              onView={() => navigate(`/campaigns/${campaign.id}`)}
              onEdit={() => { setFormCampaign(campaign); setFormOpen(true); }}
              onDelete={() => setDeleteTarget(campaign)}
            />
          ))}
        </div>
      ) : (
        <div className="campaign-page__empty">
          <FiFolder />
          <h2>Chưa có chiến dịch phù hợp</h2>
          <p>Tạo chiến dịch mới hoặc thay đổi bộ lọc tìm kiếm.</p>
        </div>
      )}

      <CampaignFormModal
        key={`${formCampaign?.id || "new"}-${formOpen}`}
        open={formOpen}
        campaign={formCampaign}
        brands={brands}
        pending={pending}
        onClose={() => setFormOpen(false)}
        onSubmit={(data) =>
          formCampaign
            ? updateCampaign(formCampaign.id, data)
            : createCampaign(data)
        }
      />
      <Modal
        open={Boolean(deleteTarget)}
        title="Xóa chiến dịch?"
        onClose={() => setDeleteTarget(null)}
        closeDisabled={pending}
        size="sm"
        footer={
          <>
            <button type="button" className="campaign-confirm__cancel" onClick={() => setDeleteTarget(null)}>Hủy</button>
            <button
              type="button"
              className="campaign-confirm__delete"
              disabled={pending}
              onClick={async () => {
                if (await deleteCampaign(deleteTarget.id)) setDeleteTarget(null);
              }}
            >
              Xóa chiến dịch
            </button>
          </>
        }
      >
        <p className="campaign-confirm__text">
          Chỉ liên kết với chiến dịch <strong>{deleteTarget?.name}</strong> bị
          xóa. Nội dung trong Thư viện vẫn được giữ nguyên.
        </p>
      </Modal>
    </WorkspaceLayout>
  );
}

export default Campaigns;
