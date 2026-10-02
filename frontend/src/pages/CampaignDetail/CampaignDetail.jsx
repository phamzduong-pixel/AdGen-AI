import { useMemo, useState } from "react";
import { FiArrowLeft, FiEdit2, FiPlus } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate, useParams } from "react-router-dom";

import CampaignContentCard from "../../components/campaign/CampaignContentCard/CampaignContentCard";
import CampaignFormModal from "../../components/campaign/CampaignFormModal/CampaignFormModal";
import LibraryPickerModal from "../../components/campaign/LibraryPickerModal/LibraryPickerModal";
import ContentScorePanel from "../../components/chat/ContentScorePanel";
import VariantGeneratorModal from "../../components/chat/VariantGeneratorModal";
import Modal from "../../components/ui/Modal/Modal";
import useToast from "../../components/ui/Toast/useToast";
import useCampaignDetail from "../../hooks/useCampaignDetail";
import useContentTools from "../../hooks/useContentTools";
import useSavedContents from "../../hooks/useSavedContents";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { recordContentActivity } from "../../services/api/savedContentApi";
import { exportSavedContent } from "../../utils/exportSavedContent";
import "./CampaignDetail.css";

const PLATFORM = {
  facebook: "Facebook",
  google_ads: "Google Ads",
  landing_page: "Landing Page",
  instagram: "Instagram",
  tiktok: "TikTok",
  email: "Email Marketing",
};

function CampaignDetail() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const {
    campaign,
    loading,
    pending,
    addContent,
    removeContent,
    setPrimary,
    updateDetails,
    reload,
  } = useCampaignDetail(campaignId);
  const {
    savedContents,
    isLoading: libraryLoading,
    saveGeneratedContent,
  } = useSavedContents();
  const contentTools = useContentTools();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [viewContent, setViewContent] = useState(null);

  const existingIds = useMemo(
    () => new Set((campaign?.contents || []).map((item) => item.saved_content.id)),
    [campaign],
  );

  const copyContent = async (content) => {
    try {
      await navigator.clipboard.writeText(content.content);
      toast.success("Đã sao chép nội dung.");
      recordContentActivity(content.id, "copy")
        .then(reload)
        .catch(() => {});
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  const exportContent = async (content) => {
    exportSavedContent(content);
    try {
      await recordContentActivity(content.id, "export");
      reload();
    } catch {
      toast.warning("Đã xuất tệp nhưng chưa thể ghi nhận thống kê.");
    }
  };

  return (
    <WorkspaceLayout
      title={campaign?.name || "Chi tiết chiến dịch"}
      subtitle={campaign ? `${PLATFORM[campaign.platform] || campaign.platform || "Nội dung chung"} · ${campaign.contents_count} nội dung` : "Đang tải..."}
      actions={
        <>
          <button type="button" className="campaign-detail__back" onClick={() => navigate("/campaigns")}><FiArrowLeft /> Danh sách</button>
          <button type="button" className="campaign-detail__edit" onClick={() => setEditOpen(true)} disabled={!campaign}><FiEdit2 /> Chỉnh sửa</button>
        </>
      }
    >
      {loading ? (
        <div className="campaign-detail__loading">Đang tải chiến dịch...</div>
      ) : campaign ? (
        <>
          <section className="campaign-detail__overview">
            <div>
              <span>Thông tin chiến dịch</span>
              <h2>{campaign.product_name || campaign.name}</h2>
              <p>{campaign.description || "Chưa có mô tả."}</p>
            </div>
            <dl>
              <div><dt>Trạng thái</dt><dd>
                <select
                  value={campaign.status}
                  onChange={(event) => updateDetails({ status: event.target.value })}
                  disabled={pending}
                >
                  <option value="draft">Bản nháp</option>
                  <option value="active">Đang chạy</option>
                  <option value="completed">Hoàn thành</option>
                  <option value="archived">Lưu trữ</option>
                </select>
              </dd></div>
              <div><dt>Mục tiêu</dt><dd>{campaign.objective || "—"}</dd></div>
              <div><dt>Khách hàng</dt><dd>{campaign.target_audience || "—"}</dd></div>
              <div><dt>Ngày tạo</dt><dd>{new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(`${campaign.created_at}Z`))}</dd></div>
            </dl>
            {campaign.notes && <aside><strong>Ghi chú</strong><p>{campaign.notes}</p></aside>}
          </section>

          <section className="campaign-detail__contents">
            <header>
              <div><h2>Nội dung quảng cáo</h2><p>Chọn một nội dung làm phiên bản chính của chiến dịch.</p></div>
              <button type="button" onClick={() => setPickerOpen(true)}><FiPlus /> Thêm từ Thư viện</button>
            </header>
            {campaign.contents.length ? (
              <div className="campaign-detail__content-grid">
                {campaign.contents.map((item) => (
                  <CampaignContentCard
                    key={item.id}
                    item={item}
                    pending={pending}
                    onView={() => setViewContent(item.saved_content)}
                    onCopy={() => copyContent(item.saved_content)}
                    onEvaluate={() =>
                      contentTools
                        .openEvaluation(item.saved_content, { savedContentId: item.saved_content.id })
                        .then(reload)
                    }
                    onVariants={() =>
                      contentTools
                        .openVariants(item.saved_content, { savedContentId: item.saved_content.id })
                        .then(reload)
                    }
                    onExport={() => exportContent(item.saved_content)}
                    onPrimary={() => setPrimary(item.saved_content.id)}
                    onRemove={() => removeContent(item.saved_content.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="campaign-detail__empty">
                Chưa có nội dung. Hãy thêm một mục từ Thư viện nội dung.
              </div>
            )}
          </section>
        </>
      ) : null}

      <LibraryPickerModal
        open={pickerOpen}
        items={savedContents}
        existingIds={existingIds}
        pending={pending || libraryLoading}
        onClose={() => setPickerOpen(false)}
        onAdd={addContent}
      />
      <CampaignFormModal
        key={`${campaign?.id || "loading"}-${editOpen}`}
        open={editOpen}
        campaign={campaign}
        pending={pending}
        onClose={() => setEditOpen(false)}
        onSubmit={updateDetails}
      />
      <Modal open={Boolean(viewContent)} title={viewContent?.title} onClose={() => setViewContent(null)} size="lg">
        <div className="campaign-detail__markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewContent?.content || ""}</ReactMarkdown>
        </div>
      </Modal>
      <ContentScorePanel
        open={contentTools.mode === "evaluation"}
        result={contentTools.evaluation}
        loading={contentTools.isLoading}
        onClose={contentTools.close}
      />
      <VariantGeneratorModal
        open={contentTools.mode === "variants"}
        variants={contentTools.variants}
        evaluations={contentTools.variantEvaluations}
        selectedLabels={contentTools.selectedLabels}
        primaryLabel={contentTools.primaryLabel}
        loading={contentTools.isLoading}
        evaluatingLabels={contentTools.evaluatingLabels}
        onClose={contentTools.close}
        onEvaluate={contentTools.evaluateVariant}
        onEvaluateSelected={contentTools.evaluateSelected}
        onToggleComparison={contentTools.toggleComparison}
        onSelectPrimary={contentTools.setPrimaryLabel}
        onSave={(variant, content) =>
          saveGeneratedContent({
            conversationId: contentTools.activeMessage?.conversation_id,
            title: `Phiên bản ${variant.label} – ${variant.title || variant.strategy}`,
            content,
            platform: contentTools.activeMessage?.platform,
          })
        }
      />
    </WorkspaceLayout>
  );
}

export default CampaignDetail;
