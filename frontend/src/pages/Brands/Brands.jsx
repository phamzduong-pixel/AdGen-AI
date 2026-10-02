import { useEffect, useState } from "react";
import {
  FiBriefcase,
  FiEdit2,
  FiExternalLink,
  FiFile,
  FiPlus,
  FiSearch,
  FiStar,
  FiTrash2,
  FiUpload,
} from "react-icons/fi";

import BrandFormModal from "../../components/brand/BrandFormModal/BrandFormModal";
import Modal from "../../components/ui/Modal/Modal";
import useToast from "../../components/ui/Toast/useToast";
import useBrands from "../../hooks/useBrands";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import {
  deleteBrandAsset,
  downloadBrandAsset,
  getBrandStatistics,
  uploadBrandAsset,
} from "../../services/api/brandApi";
import { getUserErrorMessage } from "../../utils/apiError";
import "./Brands.css";

function Brands() {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const {
    brands,
    loading,
    pending,
    reload,
    createBrand,
    updateBrand,
    deleteBrand,
    setDefaultBrand,
  } = useBrands(query);
  const [formBrand, setFormBrand] = useState(undefined);
  const [formOpen, setFormOpen] = useState(false);
  const [detailBrandId, setDetailBrandId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [assetPending, setAssetPending] = useState(false);
  const detailBrand = brands.find((brand) => brand.id === detailBrandId) || null;

  useEffect(() => {
    if (!detailBrandId) return;
    getBrandStatistics(detailBrandId)
      .then(setStatistics)
      .catch((error) =>
        toast.error(getUserErrorMessage(error, "Không thể tải thống kê thương hiệu.")),
      );
  }, [detailBrandId, toast]);

  const handleAssetUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !detailBrand || assetPending) return;
    setAssetPending(true);
    try {
      await uploadBrandAsset(detailBrand.id, file);
      await reload();
      toast.success("Đã tải tài sản thương hiệu lên.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải tài sản lên."));
    } finally {
      setAssetPending(false);
    }
  };

  return (
    <WorkspaceLayout
      title="Hồ sơ thương hiệu"
      subtitle="Quản lý giọng điệu, nhận diện và quy chuẩn để AI viết nhất quán."
      actions={
        <button
          type="button"
          className="brands-page__primary"
          onClick={() => {
            setFormBrand(undefined);
            setFormOpen(true);
          }}
        >
          <FiPlus /> Tạo hồ sơ
        </button>
      }
    >
      <div className="brands-page__toolbar">
        <FiSearch />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Tìm theo tên thương hiệu..."
          aria-label="Tìm thương hiệu"
        />
      </div>

      {loading ? (
        <div className="brands-page__state">Đang tải hồ sơ thương hiệu...</div>
      ) : brands.length === 0 ? (
        <div className="brands-page__empty">
          <FiBriefcase />
          <h2>{query ? "Không tìm thấy thương hiệu" : "Tạo hồ sơ thương hiệu đầu tiên"}</h2>
          <p>AI sẽ dùng hồ sơ để giữ đúng giọng điệu, từ khóa và quy chuẩn nội dung.</p>
          {!query && (
            <button type="button" onClick={() => setFormOpen(true)}>Tạo hồ sơ</button>
          )}
        </div>
      ) : (
        <div className="brands-page__grid">
          {brands.map((brand) => (
            <article key={brand.id} className="brand-card">
              <header>
                <div className="brand-card__mark">
                  {brand.name.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <h2>{brand.name}</h2>
                  <p>{brand.industry || "Chưa chọn ngành nghề"}</p>
                </div>
                {brand.is_default && <span className="brand-card__default"><FiStar /> Mặc định</span>}
              </header>
              <p className="brand-card__description">
                {brand.description || brand.slogan || "Chưa có mô tả thương hiệu."}
              </p>
              <div className="brand-card__meta">
                <span>{brand.default_tone || "Chưa đặt giọng điệu"}</span>
                <span>{brand.assets?.length || 0} tài sản</span>
              </div>
              <footer>
                <button type="button" onClick={() => {
                  setStatistics(null);
                  setDetailBrandId(brand.id);
                }}>Chi tiết</button>
                {!brand.is_default && (
                  <button type="button" onClick={() => setDefaultBrand(brand.id)} title="Đặt mặc định">
                    <FiStar />
                  </button>
                )}
                <button type="button" onClick={() => {
                  setFormBrand(brand);
                  setFormOpen(true);
                }} title="Chỉnh sửa"><FiEdit2 /></button>
                <button type="button" className="is-danger" onClick={() => setDeleteTarget(brand)} title="Xóa"><FiTrash2 /></button>
              </footer>
            </article>
          ))}
        </div>
      )}

      <BrandFormModal
        open={formOpen}
        brand={formBrand}
        pending={pending}
        onClose={() => {
          setFormOpen(false);
          setFormBrand(undefined);
        }}
        onSubmit={(payload) =>
          formBrand ? updateBrand(formBrand.id, payload) : createBrand(payload)
        }
      />

      <Modal
        open={Boolean(detailBrand)}
        title={detailBrand?.name || "Chi tiết thương hiệu"}
        size="lg"
        onClose={() => {
          setDetailBrandId(null);
          setStatistics(null);
        }}
      >
        {detailBrand && (
          <div className="brand-detail">
            <section className="brand-detail__summary">
              <div><small>Slogan</small><strong>{detailBrand.slogan || "—"}</strong></div>
              <div><small>Giọng điệu</small><strong>{detailBrand.default_tone || "—"}</strong></div>
              <div><small>Ngôn ngữ</small><strong>{detailBrand.default_language || "—"}</strong></div>
              <div><small>Website</small>
                {detailBrand.website ? (
                  <a href={detailBrand.website} target="_blank" rel="noreferrer">
                    Mở website <FiExternalLink />
                  </a>
                ) : <strong>—</strong>}
              </div>
            </section>
            <section>
              <h3>Thống kê sử dụng</h3>
              <div className="brand-detail__stats">
                <div><strong>{statistics?.campaigns_count ?? "—"}</strong><span>Chiến dịch</span></div>
                <div><strong>{statistics?.saved_contents_count ?? "—"}</strong><span>Nội dung đã lưu</span></div>
                <div><strong>{statistics?.average_consistency_score ?? "—"}</strong><span>Điểm nhất quán TB</span></div>
                <div><strong>{statistics?.top_platform || "—"}</strong><span>Nền tảng nổi bật</span></div>
              </div>
            </section>
            <section>
              <div className="brand-detail__heading">
                <div>
                  <h3>Tài sản thương hiệu</h3>
                  <p>Logo, ảnh và tài liệu tham chiếu. Tối đa 10 MB mỗi tệp.</p>
                </div>
                <label className="brand-detail__upload">
                  <FiUpload /> {assetPending ? "Đang tải..." : "Tải tệp"}
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.txt"
                    disabled={assetPending}
                    onChange={handleAssetUpload}
                  />
                </label>
              </div>
              <div className="brand-detail__assets">
                {detailBrand.assets?.length ? detailBrand.assets.map((asset) => (
                  <div key={asset.id}>
                    <FiFile />
                    <button
                      type="button"
                      className="brand-detail__asset-name"
                      onClick={() => downloadBrandAsset(detailBrand.id, asset)}
                    >
                      {asset.file_name}
                    </button>
                    <button
                      type="button"
                      aria-label={`Xóa ${asset.file_name}`}
                      onClick={async () => {
                        setAssetPending(true);
                        try {
                          await deleteBrandAsset(detailBrand.id, asset.id);
                          await reload();
                          toast.success("Đã xóa tài sản.");
                        } catch (error) {
                          toast.error(getUserErrorMessage(error, "Không thể xóa tài sản."));
                        } finally {
                          setAssetPending(false);
                        }
                      }}
                    >
                      <FiTrash2 />
                    </button>
                  </div>
                )) : <p>Chưa có tài sản nào.</p>}
              </div>
            </section>
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(deleteTarget)}
        title="Xóa hồ sơ thương hiệu?"
        onClose={() => setDeleteTarget(null)}
        footer={
          <div className="brands-page__confirm">
            <button type="button" onClick={() => setDeleteTarget(null)}>Hủy</button>
            <button
              type="button"
              className="is-danger"
              disabled={pending}
              onClick={async () => {
                const result = await deleteBrand(deleteTarget.id);
                if (result) setDeleteTarget(null);
              }}
            >
              Xóa hồ sơ
            </button>
          </div>
        }
      >
        <p>Hồ sơ “{deleteTarget?.name}” sẽ bị xóa. Hội thoại, chiến dịch và nội dung đã lưu vẫn được giữ lại nhưng không còn liên kết thương hiệu.</p>
      </Modal>
    </WorkspaceLayout>
  );
}

export default Brands;
