import { useEffect, useMemo, useState } from "react";
import { FiGrid, FiPlus } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import TemplateCard from "../../components/templates/TemplateCard/TemplateCard";
import TemplateFilters from "../../components/templates/TemplateFilters/TemplateFilters";
import TemplateFormModal from "../../components/templates/TemplateFormModal/TemplateFormModal";
import Modal from "../../components/ui/Modal/Modal";
import useToast from "../../components/ui/Toast/useToast";
import useTemplates from "../../hooks/useTemplates";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { getSavedContents } from "../../services/api/savedContentApi";
import { getUserErrorMessage } from "../../utils/apiError";
import { filterAdTemplates } from "../../utils/adTemplate";
import "./Templates.css";

function Templates() {
  const navigate = useNavigate();
  const toast = useToast();
  const {
    templates,
    platforms,
    categories,
    isLoading,
    pendingIds,
    toggleFavorite,
    createTemplate,
    updateTemplate,
    deleteTemplate,
  } = useTemplates();
  const [filters, setFilters] = useState({
    query: "",
    platform: "",
    category: "",
    scope: "all",
  });
  const [formTemplate, setFormTemplate] = useState(undefined);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [savedContents, setSavedContents] = useState([]);

  useEffect(() => {
    getSavedContents()
      .then((data) => setSavedContents(Array.isArray(data) ? data : []))
      .catch((error) =>
        toast.error(
          getUserErrorMessage(
            error,
            "Không thể tải nội dung dùng để tạo mẫu.",
          ),
        ),
      );
  }, [toast]);

  const filtered = useMemo(() => {
    return filterAdTemplates(templates, filters);
  }, [filters, templates]);

  const hasActiveFilters =
    filters.query ||
    filters.platform ||
    filters.category ||
    filters.scope !== "all";
  const popular = templates.filter((item) => item.is_popular);
  const favorites = templates.filter((item) => item.is_favorite);

  const useTemplate = (template) => {
    navigate("/chat", {
      state: {
        adTemplate: template,
        templateRequestId: Date.now(),
      },
    });
  };

  const renderCards = (items, compact = false) => (
    <div
      className={
        compact
          ? "templates-page__horizontal"
          : "templates-page__grid"
      }
    >
      {items.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          compact={compact}
          pending={pendingIds.has(template.id)}
          onUse={useTemplate}
          onFavorite={toggleFavorite}
          onEdit={(item) => {
            setFormTemplate(item);
            setIsFormOpen(true);
          }}
          onDelete={setDeleteTarget}
          onClone={async (item) => {
            await createTemplate({
              title: `${item.title} – Bản của tôi`,
              source_template_id: item.id,
            });
          }}
        />
      ))}
    </div>
  );

  return (
    <WorkspaceLayout
      title="Mẫu quảng cáo"
      subtitle={`${templates.length} mẫu sẵn sàng để bắt đầu nhanh`}
      actions={
        <button
          type="button"
          className="templates-page__create"
          onClick={() => {
            setFormTemplate(undefined);
            setIsFormOpen(true);
          }}
        >
          <FiPlus />
          Tạo mẫu cá nhân
        </button>
      }
    >
      <TemplateFilters
        {...filters}
        platforms={platforms}
        categories={categories}
        onChange={(field, value) =>
          setFilters((current) => ({ ...current, [field]: value }))
        }
      />

      {isLoading ? (
        <div className="templates-page__loading">
          <span />
          Đang tải thư viện mẫu...
        </div>
      ) : filtered.length === 0 ? (
        <div className="templates-page__empty">
          <FiGrid />
          <h2>Không tìm thấy mẫu phù hợp</h2>
          <p>Thử thay đổi từ khóa hoặc bỏ bớt bộ lọc.</p>
          <button
            type="button"
            onClick={() =>
              setFilters({
                query: "",
                platform: "",
                category: "",
                scope: "all",
              })
            }
          >
            Xóa bộ lọc
          </button>
        </div>
      ) : hasActiveFilters ? (
        <section className="templates-page__section">
          <div className="templates-page__section-heading">
            <div>
              <h2>Kết quả</h2>
              <p>{filtered.length} mẫu phù hợp</p>
            </div>
          </div>
          {renderCards(filtered)}
        </section>
      ) : (
        <>
          <section className="templates-page__section">
            <div className="templates-page__section-heading">
              <div>
                <h2>Mẫu phổ biến</h2>
                <p>Những lựa chọn được chuẩn bị để bắt đầu nhanh</p>
              </div>
            </div>
            {renderCards(popular, true)}
          </section>

          {favorites.length > 0 && (
            <section className="templates-page__section">
              <div className="templates-page__section-heading">
                <div>
                  <h2>Đã yêu thích</h2>
                  <p>Các mẫu bạn muốn sử dụng lại</p>
                </div>
              </div>
              {renderCards(favorites, true)}
            </section>
          )}

          <section className="templates-page__section">
            <div className="templates-page__section-heading">
              <div>
                <h2>Tất cả mẫu</h2>
                <p>Mẫu hệ thống và mẫu cá nhân của bạn</p>
              </div>
            </div>
            {renderCards(filtered)}
          </section>
        </>
      )}

      <TemplateFormModal
        open={isFormOpen}
        template={formTemplate}
        savedContents={savedContents}
        onClose={() => {
          setIsFormOpen(false);
          setFormTemplate(undefined);
        }}
        onSubmit={(payload) =>
          formTemplate
            ? updateTemplate(formTemplate.id, payload)
            : createTemplate(payload)
        }
      />

      <Modal
        open={Boolean(deleteTarget)}
        title="Xóa mẫu cá nhân?"
        onClose={() => setDeleteTarget(null)}
        footer={
          <div className="templates-page__confirm-actions">
            <button type="button" onClick={() => setDeleteTarget(null)}>
              Hủy
            </button>
            <button
              type="button"
              className="is-danger"
              disabled={pendingIds.has(deleteTarget?.id)}
              onClick={async () => {
                const deleted = await deleteTemplate(deleteTarget.id);
                if (deleted) setDeleteTarget(null);
              }}
            >
              Xóa mẫu
            </button>
          </div>
        }
      >
        <p className="templates-page__confirm-copy">
          Mẫu “{deleteTarget?.title}” sẽ bị xóa khỏi tài khoản của bạn. Nội
          dung quảng cáo đã lưu không bị ảnh hưởng.
        </p>
      </Modal>
    </WorkspaceLayout>
  );
}

export default Templates;
