import { useEffect, useRef, useState } from "react";
import {
  FiDownload,
  FiEdit3,
  FiImage,
  FiLoader,
  FiMaximize2,
  FiPlus,
  FiRefreshCw,
  FiTrash2,
  FiUpload,
  FiVideo,
} from "react-icons/fi";

import Modal from "../../ui/Modal/Modal";
import useToast from "../../ui/Toast/useToast";
import { uploadFiles } from "../../../services/api/uploadApi";
import {
  createVideoGenerationJob,
  createVideoEditPlan,
  deleteMediaAsset,
  downloadMediaAsset,
  editVideo,
  executeVideoEditPlan,
  generateImage,
  getVideoGenerationJob,
  listVideoGenerationJobs,
  listMediaAssets,
  registerVideoUpload,
} from "../../../services/api/mediaApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import { buildConversationalEditRequest, getConversationalExecutionOutcome, getConversationalOperationNames, reuseIdempotencyKey } from "../../../utils/conversationalEdit";
import { getVideoJobErrorMessage, isVideoJobPending, pollVideoJob } from "../../../utils/mediaJob";
import { getImageActionLabel, getImageGenerationErrorMessage } from "../../../utils/imageGeneration";

import "./MediaStudio.css";

const IMAGE_RATIOS = [["1:1", "Vuông 1:1"], ["4:5", "Bài đăng 4:5"], ["9:16", "Story / TikTok 9:16"], ["16:9", "Ngang 16:9"], ["3:2", "Ảnh 3:2"], ["2:3", "Ảnh dọc 2:3"]];
const VIDEO_RATIOS = [["16:9", "Ngang 16:9"], ["9:16", "Dọc 9:16"], ["1:1", "Vuông 1:1"], ["4:5", "Dọc 4:5"]];
const AI_VIDEO_RATIOS = [["16:9", "Ngang 16:9"], ["9:16", "Dọc 9:16"]];
const VIDEO_OPERATIONS = [["trim", "Cắt video"], ["aspect_crop", "Đổi tỷ lệ / crop"], ["text_overlay", "Thêm text"], ["cta_overlay", "Thêm CTA"], ["subtitle", "Phụ đề"], ["volume", "Âm lượng"], ["mute", "Tắt tiếng"], ["merge", "Ghép video"]];

const numberValue = (value, fallback) => {
  const parsed = value === "" ? fallback : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

function MediaStudio({ open, onClose, conversationId, onEnsureConversation }) {
  const toast = useToast();
  const imageInputRef = useRef(null);
  const videoInputRef = useRef(null);
  const objectUrlsRef = useRef(new Map());
  const pollingRef = useRef(new Map());
  const [mode, setMode] = useState("image");
  const [prompt, setPrompt] = useState("");
  const [imageRatio, setImageRatio] = useState("1:1");
  const [referenceFile, setReferenceFile] = useState(null);
  const [sourceAssetId, setSourceAssetId] = useState(null);
  const [imageGenerationState, setImageGenerationState] = useState("idle");
  const [imageGenerationError, setImageGenerationError] = useState("");
  const [latestImageAssetId, setLatestImageAssetId] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [videoSourceAssetId, setVideoSourceAssetId] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [videoOperation, setVideoOperation] = useState("trim");
  const [videoRatio, setVideoRatio] = useState("16:9");
  const [videoGenerationPrompt, setVideoGenerationPrompt] = useState("");
  const [videoGenerationRatio, setVideoGenerationRatio] = useState("16:9");
  const [videoGenerationDuration] = useState("8");
  const [videoGenerationReferenceId, setVideoGenerationReferenceId] = useState("");
  const [, setVideoGenerationJob] = useState(null);
  const [videoGenerationJobs, setVideoGenerationJobs] = useState([]);
  const [start, setStart] = useState("0");
  const [end, setEnd] = useState("15");
  const [overlayText, setOverlayText] = useState("");
  const [position, setPosition] = useState("bottom");
  const [fontSize, setFontSize] = useState("48");
  const [textColor, setTextColor] = useState("white");
  const [volume, setVolume] = useState("1");
  const [subtitleEntries, setSubtitleEntries] = useState([{ text: "", start: "0", end: "3" }]);
  const [mergeSelection, setMergeSelection] = useState([]);
  const [conversationalInstruction, setConversationalInstruction] = useState("");
  const [conversationalPlan, setConversationalPlan] = useState(null);
  const [conversationalExecution, setConversationalExecution] = useState(null);
  const [conversationalRequestKey, setConversationalRequestKey] = useState(null);
  const [assets, setAssets] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  const releaseObjectUrl = (assetId) => {
    const url = objectUrlsRef.current.get(assetId);
    if (url) { URL.revokeObjectURL(url); objectUrlsRef.current.delete(assetId); }
  };

  const loadAssets = async (id = conversationId) => {
    if (!id) { setAssets([]); return true; }
    setIsLoading(true);
    try {
      const nextAssets = await listMediaAssets(id);
      const mediaAssets = nextAssets.filter((asset) => ["image", "video"].includes(asset.kind));
      const hydrated = await Promise.all(mediaAssets.map(async (asset) => {
        if (asset.status !== "completed") return asset;
        try {
          releaseObjectUrl(asset.id);
          const blob = await downloadMediaAsset(asset.id);
          const objectUrl = URL.createObjectURL(blob);
          objectUrlsRef.current.set(asset.id, objectUrl);
          return { ...asset, objectUrl, previewError: false };
        } catch {
          return { ...asset, objectUrl: null, previewError: true };
        }
      }));
      setAssets(hydrated);
      return true;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải thư viện media."));
      return false;
    } finally { setIsLoading(false); }
  };
  const updateVideoJob = (job) => {
    setVideoGenerationJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
    setVideoGenerationJob((current) => (current?.id === job.id ? job : current));
  };

  const startVideoJobPolling = async (initialJob, activeId) => {
    if (!isVideoJobPending(initialJob)) {
      updateVideoJob(initialJob);
      return initialJob;
    }
    if (pollingRef.current.has(initialJob.id)) return initialJob;
    const control = { cancelled: false };
    pollingRef.current.set(initialJob.id, control);
    try {
      const job = await pollVideoJob({
        initialJob,
        fetchJob: getVideoGenerationJob,
        onUpdate: updateVideoJob,
        isCancelled: () => control.cancelled,
      });
      if (job.status === "completed" && job.output_asset_id) {
        setVideoSourceAssetId(job.output_asset_id);
        await loadAssets(activeId);
      }
      return job;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật trạng thái video AI."));
      return initialJob;
    } finally {
      pollingRef.current.delete(initialJob.id);
    }
  };

  const loadVideoJobs = async (id = conversationId) => {
    if (!id) { setVideoGenerationJobs([]); return; }
    try {
      const jobs = await listVideoGenerationJobs(id);
      setVideoGenerationJobs(jobs);
      setVideoGenerationJob((current) => current || jobs[0] || null);
      jobs.filter(isVideoJobPending).forEach((job) => { void startVideoJobPolling(job, id); });
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể khôi phục trạng thái video AI."));
    }
  };

  const stopVideoPolling = () => {
    pollingRef.current.forEach((control) => { control.cancelled = true; });
    pollingRef.current.clear();
  };

  useEffect(() => {
    if (!open) return undefined;
    const refreshId = window.setTimeout(() => {
      setSourceAssetId(null);
      setReferenceFile(null);
      setImageGenerationState("idle");
      setImageGenerationError("");
      setLatestImageAssetId(null);
      setVideoSourceAssetId(null);
      setVideoFile(null);
      setMergeSelection([]);
      setConversationalInstruction("");
      setConversationalPlan(null);
      setConversationalExecution(null);
      setConversationalRequestKey(null);
      void loadAssets();
      void loadVideoJobs();
    }, 0);
    return () => {
      window.clearTimeout(refreshId);
      stopVideoPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, conversationId]);

  useEffect(() => () => {
    objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    objectUrlsRef.current.clear();
  }, []);

  const ensureConversation = async () => conversationId || (await onEnsureConversation())?.id;

  const handleGenerateImage = async () => {
    if (!prompt.trim() || isBusy) return;
    setIsBusy(true);
    setImageGenerationState("processing");
    setImageGenerationError("");
    try {
      const activeId = await ensureConversation();
      const selectedSourceId = assets.some((asset) => (
        asset.id === sourceAssetId && asset.kind === "image" && asset.status === "completed"
      )) ? sourceAssetId : null;
      let referenceFileId;
      if (referenceFile) {
        referenceFileId = (await uploadFiles(activeId, [referenceFile]))[0]?.id;
        if (!referenceFileId) throw new Error("Không thể tải ảnh tham chiếu lên.");
      }
      const createdAsset = await generateImage(activeId, {
        prompt,
        aspect_ratio: imageRatio,
        ...(referenceFileId ? { reference_file_id: referenceFileId } : {}),
        ...(selectedSourceId && !referenceFileId ? { source_asset_id: selectedSourceId } : {}),
      });
      setLatestImageAssetId(createdAsset.id);
      setImageGenerationState("completed");
      setPrompt(""); setReferenceFile(null); setSourceAssetId(null);
      if (imageInputRef.current) imageInputRef.current.value = "";
      await loadAssets(activeId);
      toast.success(selectedSourceId || referenceFileId ? "Đã tạo phiên bản ảnh chỉnh sửa." : "Đã tạo ảnh quảng cáo.");
    } catch (error) {
      const message = getImageGenerationErrorMessage(error);
      setImageGenerationState("failed");
      setImageGenerationError(message);
      toast.error(message);
    } finally { setIsBusy(false); }
  };

  const handleVideoEdit = async () => {
    if (isBusy) return;
    setIsBusy(true);
    try {
      const activeId = await ensureConversation();
      let selectedId = videoSourceAssetId;
      if (videoFile) {
        const uploaded = (await uploadFiles(activeId, [videoFile]))[0];
        if (!uploaded?.id) throw new Error("Không thể tải video lên.");
        selectedId = (await registerVideoUpload(activeId, uploaded.id)).id;
      }
      if (!selectedId) throw new Error("Hãy chọn hoặc tải lên một video trước.");
      let payload;
      if (videoOperation === "trim") payload = { operation: "trim", start: numberValue(start, 0), end: numberValue(end, 15) };
      if (videoOperation === "aspect_crop") payload = { operation: "aspect_crop", aspect_ratio: videoRatio };
      if (["text_overlay", "cta_overlay"].includes(videoOperation)) payload = { operation: videoOperation, text: overlayText.trim(), start: numberValue(start, 0), end: numberValue(end, 3), position, font_size: numberValue(fontSize, 48), text_color: textColor, background: true };
      if (videoOperation === "subtitle") payload = { operation: "subtitle", position, entries: subtitleEntries.map((entry) => ({ text: entry.text.trim(), start: numberValue(entry.start, 0), end: numberValue(entry.end, 3) })) };
      if (videoOperation === "volume") payload = { operation: "volume", volume: numberValue(volume, 1) };
      if (videoOperation === "mute") payload = { operation: "mute" };
      if (videoOperation === "merge") payload = { operation: "merge", source_asset_ids: [...new Set([selectedId, ...mergeSelection])] };
      if (payload.operation === "merge" && payload.source_asset_ids.length < 2) throw new Error("Hãy chọn ít nhất hai video để ghép.");
      const createdAsset = await editVideo(activeId, selectedId, payload);
      setVideoSourceAssetId(createdAsset.id); setVideoFile(null); setMergeSelection([]);
      if (videoInputRef.current) videoInputRef.current.value = "";
      await loadAssets(activeId);
      toast.success("Đã tạo version video mới.");
    } catch (error) { toast.error(getUserErrorMessage(error, "Không thể xử lý video.")); }
    finally { setIsBusy(false); }
  };

  const handleCreateVideoEditPlan = async () => {
    if (!videoSourceAssetId || !conversationalInstruction.trim() || isBusy) return;
    setIsBusy(true);
    try {
      const activeId = await ensureConversation();
      const plan = await createVideoEditPlan(activeId, videoSourceAssetId, {
        ...buildConversationalEditRequest(conversationalInstruction, mergeSelection),
      });
      setConversationalPlan(plan);
      setConversationalExecution(null);
      toast.success("Đã phân tích yêu cầu thành kế hoạch chỉnh sửa.");
    } catch (error) { toast.error(getUserErrorMessage(error, "Không thể phân tích yêu cầu chỉnh sửa video.")); }
    finally { setIsBusy(false); }
  };

  const handleExecuteVideoEditPlan = async () => {
    if (!videoSourceAssetId || !conversationalPlan || isBusy) return;
    setIsBusy(true);
    const requestKey = reuseIdempotencyKey(conversationalRequestKey);
    setConversationalRequestKey(requestKey);
    try {
      const activeId = await ensureConversation();
      const result = await executeVideoEditPlan(activeId, videoSourceAssetId, {
        source_asset_id: conversationalPlan.source_asset_id,
        operations: conversationalPlan.operations,
      }, requestKey);
      const outcome = getConversationalExecutionOutcome(result);
      if (outcome.status !== "processing") {
        setConversationalPlan(null);
        setConversationalRequestKey(null);
      }
      if (outcome.latestAssetId) setVideoSourceAssetId(outcome.latestAssetId);
      const libraryLoaded = await loadAssets(activeId);
      const finalOutcome = { ...outcome, libraryReloadFailed: !libraryLoaded };
      setConversationalExecution(finalOutcome);
      if (finalOutcome.status === "completed") toast.success(finalOutcome.message);
      else if (finalOutcome.status === "partial") toast.warning(finalOutcome.message);
      else if (finalOutcome.status === "processing") toast.warning("Request is still processing. Check again with the same request.");
      else toast.error(finalOutcome.message);
    } catch (error) { toast.error(getUserErrorMessage(error, "\u004b\u0068\u00f4\u006e\u0067 \u0074\u0068\u1ec3 \u0074\u0068\u1ef1\u0063 \u0074\u0068\u0069 \u006b\u1ebf \u0068\u006f\u1ea1\u0063\u0068 \u0063\u0068\u1ec9\u006e\u0068 \u0073\u1eeda \u0076\u0069\u0064\u0065\u006f.")); }
    finally { setIsBusy(false); }
  };
  const handleGenerateVideo = async () => {
    if (!videoGenerationPrompt.trim() || isBusy) return;
    setIsBusy(true);
    try {
      const activeId = await ensureConversation();
      const createdJob = await createVideoGenerationJob(activeId, {
        prompt: videoGenerationPrompt.trim(),
        aspect_ratio: videoGenerationRatio,
        duration_seconds: 8,
        ...(videoGenerationReferenceId ? { reference_asset_ids: [Number(videoGenerationReferenceId)] } : {}),
      });
      setVideoGenerationJob(createdJob);
      updateVideoJob(createdJob);
      const job = await startVideoJobPolling(createdJob, activeId);
      if (job.status === "completed") {
        setVideoGenerationPrompt("");
        toast.success("Đã tạo video AI.");
      } else if (job.status === "failed") {
        toast.error(getVideoJobErrorMessage(job));
      }
    } catch (error) { toast.error(getUserErrorMessage(error, "Không thể tạo video AI.")); }
    finally { setIsBusy(false); }
  };
  const handleDownload = async (asset) => {
    try {
      const blob = await downloadMediaAsset(asset.id);
      const url = URL.createObjectURL(blob); const link = document.createElement("a");
      link.href = url; link.download = asset.filename || `adgen-media-${asset.id}`; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { toast.error(getUserErrorMessage(error, "Không thể tải media xuống.")); }
  };

  const handlePreviewAsset = async (asset) => {
    if (!asset?.id || asset.status !== "completed") return;
    try {
      const blob = await downloadMediaAsset(asset.id);
      const url = URL.createObjectURL(blob);
      const preview = window.open(url, "_blank", "noopener,noreferrer");
      if (!preview) {
        URL.revokeObjectURL(url);
        toast.warning("Không thể mở bản xem trước. Hãy tải file xuống.");
        return;
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (error) { toast.error(getUserErrorMessage(error, "Không thể xem asset đã tạo.")); }
  };
  const handleDeleteImage = (asset) => {
    if (!asset?.id || isBusy || !conversationId) return;
    setDeleteCandidate(asset);
  };

  const confirmDeleteImage = async () => {
    const asset = deleteCandidate;
    if (!asset?.id || isBusy || !conversationId) return;
    setIsBusy(true);
    try {
      await deleteMediaAsset(conversationId, asset.id);
      releaseObjectUrl(asset.id);
      if (sourceAssetId === asset.id) setSourceAssetId(null);
      if (latestImageAssetId === asset.id) setLatestImageAssetId(null);
      await loadAssets(conversationId);
      toast.success("Đã xoá ảnh khỏi conversation.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể xoá ảnh lúc này."));
    } finally {
      setIsBusy(false);
      setDeleteCandidate(null);
    }
  };
  const videoAssets = assets.filter((asset) => asset.kind === "video");
  const imageAssets = assets.filter((asset) => asset.kind === "image");
  const selectedVideo = videoAssets.find((asset) => asset.id === videoSourceAssetId);
  const selectedImage = imageAssets.find((asset) => asset.id === sourceAssetId && asset.status === "completed");
  const imageActionLabel = getImageActionLabel({ referenceFile, sourceAsset: selectedImage });

  return (
    <>
      <Modal open={open} onClose={isBusy ? undefined : onClose} closeDisabled={isBusy} title="Media Studio" size="xl" footer={null}>
      <div className="media-studio">
        <section className="media-studio__form">
          <div className="media-studio__tabs">
            <button type="button" className={mode === "image" ? "is-active" : ""} onClick={() => setMode("image")}><FiImage /> Ảnh</button>
            <button type="button" className={mode === "video" ? "is-active" : ""} onClick={() => setMode("video")}><FiVideo /> Video</button>
          </div>
          {mode === "image" ? <>
            <div className="media-studio__eyebrow"><FiImage /> Tạo ảnh quảng cáo</div>
            <p className="media-studio__hint">Mô tả sản phẩm, bối cảnh, phong cách và thông điệp cần xuất hiện trong ảnh.</p>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Mô tả ảnh quảng cáo..." rows={5} maxLength={10000} disabled={isBusy} />
            <div className="media-studio__controls"><label>Tỷ lệ<select value={imageRatio} onChange={(event) => setImageRatio(event.target.value)} disabled={isBusy}>{IMAGE_RATIOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label className="media-studio__upload"><span><FiUpload /> {referenceFile ? referenceFile.name : "Ảnh tham chiếu"}</span><input ref={imageInputRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { setReferenceFile(event.target.files?.[0] || null); setSourceAssetId(null); }} disabled={isBusy} /></label></div>
                        <button type="button" className="media-studio__generate" onClick={handleGenerateImage} disabled={!prompt.trim() || isBusy}>
              {isBusy ? <FiLoader className="spin" /> : <FiImage />}
              {isBusy ? "Đang tạo ảnh..." : imageActionLabel}
            </button>
            {imageGenerationState !== "idle" && <div className={`media-studio__image-status is-${imageGenerationState}`} role="status" aria-live="polite">
              {imageGenerationState === "processing" && "Đang tạo ảnh quảng cáo..."}
              {imageGenerationState === "completed" && `Đã tạo ảnh${latestImageAssetId ? ` #${latestImageAssetId}` : ""}. Ảnh mới đã được thêm vào thư viện.`}
              {imageGenerationState === "failed" && imageGenerationError}
            </div>}          </> : <>
            <div className="media-studio__ai-generation">
              <div className="media-studio__eyebrow"><FiVideo /> Tạo video bằng AI</div>
              <p className="media-studio__hint">Provider video thật sẽ quyết định trạng thái và thời gian xử lý; hệ thống không giả lập output.</p>
              <textarea value={videoGenerationPrompt} onChange={(event) => setVideoGenerationPrompt(event.target.value)} placeholder="Mô tả video cần tạo..." rows={3} maxLength={10000} disabled={isBusy} />
              <div className="media-studio__controls">
                <label>Tỷ lệ<select value={videoGenerationRatio} onChange={(event) => setVideoGenerationRatio(event.target.value)} disabled={isBusy}>{AI_VIDEO_RATIOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
                <label>Thời lượng<select value={videoGenerationDuration} disabled><option value="8">8 giây</option></select></label>
                <label>Ảnh tham chiếu<select value={videoGenerationReferenceId} onChange={(event) => setVideoGenerationReferenceId(event.target.value)} disabled={isBusy}><option value="">Không dùng</option>{imageAssets.filter((asset) => asset.status === "completed").map((asset) => <option key={asset.id} value={asset.id}>V{asset.version_number} · {asset.filename || "Ảnh"}</option>)}</select></label>
              </div>
              <button type="button" className="media-studio__generate" onClick={handleGenerateVideo} disabled={!videoGenerationPrompt.trim() || isBusy}>{isBusy ? <FiLoader className="spin" /> : <FiVideo />} {isBusy ? "Đang tạo video..." : "Tạo video AI"}</button>
              {videoGenerationJobs.slice(0, 3).map((job) => <div className="media-studio__status" key={job.id}>Job #{job.id}: {job.status}{job.status === "failed" ? ` · ${getVideoJobErrorMessage(job)}` : ""}</div>)}
            </div>
            
 <div className="media-studio__technical-editor">
 <VideoEditorForm isBusy={isBusy} videoFile={videoFile} setVideoFile={setVideoFile} videoInputRef={videoInputRef} operation={videoOperation} setOperation={setVideoOperation} ratio={videoRatio} setRatio={setVideoRatio} start={start} setStart={setStart} end={end} setEnd={setEnd} text={overlayText} setText={setOverlayText} position={position} setPosition={setPosition} fontSize={fontSize} setFontSize={setFontSize} textColor={textColor} setTextColor={setTextColor} volume={volume} setVolume={setVolume} entries={subtitleEntries} setEntries={setSubtitleEntries} selectedVideo={selectedVideo} videoAssets={videoAssets} sourceAssetId={videoSourceAssetId} mergeSelection={mergeSelection} setMergeSelection={setMergeSelection} onExecute={handleVideoEdit} />
 </div>
             <ConversationalEditor isBusy={isBusy} selectedVideo={selectedVideo} instruction={conversationalInstruction} setInstruction={setConversationalInstruction} plan={conversationalPlan} execution={conversationalExecution} onPlan={handleCreateVideoEditPlan} onExecute={handleExecuteVideoEditPlan} onPreviewAsset={handlePreviewAsset} onDownloadAsset={handleDownload} />
           </>}
        </section>
        <section className="media-studio__library">
          <div className="media-studio__library-header"><div><h3>{mode === "video" ? "Video trong conversation" : "Ảnh trong conversation"}</h3><span>{mode === "video" ? videoAssets.length : imageAssets.length} asset</span></div><button type="button" onClick={() => loadAssets()} disabled={isLoading} title="Làm mới"><FiRefreshCw className={isLoading ? "spin" : ""} /></button></div>
          <div className="media-studio__grid">
            {(mode === "video" ? videoAssets : imageAssets).map((asset) => (
              <article className={`media-studio__asset ${(mode === "video" ? videoSourceAssetId : sourceAssetId) === asset.id ? "is-selected" : ""} ${mode === "image" && latestImageAssetId === asset.id ? "is-latest" : ""}`} key={asset.id}>
                {asset.status === "completed" && asset.objectUrl ? (asset.kind === "video" ? <video src={asset.objectUrl} controls preload="metadata" /> : <img src={asset.objectUrl} alt={asset.prompt} />) : <div className="media-studio__status">{asset.status === "failed" ? "X\u1eed l\u00fd th\u1ea5t b\u1ea1i" : asset.previewError ? "Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c b\u1ea3n xem tr\u01b0\u1edbc" : "\u0110ang x\u1eed l\u00fd..."}</div>}
                <div>
                  <span>V{asset.version_number} \u00b7 {asset.operation} \u00b7 {asset.status}</span>
                  <div className="media-studio__asset-actions">
                    {asset.status === "completed" && <>
                      <button type="button" onClick={() => (mode === "video" ? setVideoSourceAssetId(asset.id) : setSourceAssetId(asset.id))} title="Ch?n source"><FiEdit3 /></button>
                      <button type="button" onClick={() => handleDownload(asset)} title="T?i xu?ng"><FiDownload /></button>
                      {asset.kind === "image" && asset.objectUrl && <a href={asset.objectUrl} target="_blank" rel="noreferrer" title="Xem ?nh l?n"><FiMaximize2 /></a>}
                    </>}
                    {mode === "image" && <button type="button" onClick={() => handleDeleteImage(asset)} className="media-studio__asset-delete" title="X\u00f3a \u1ea3nh" aria-label="X\u00f3a \u1ea3nh"><FiTrash2 /></button>}
                  </div>
                </div>
              </article>
            ))}
          </div>
          {mode === "video" && videoAssets.length === 0 && !isLoading && <div className="media-studio__empty">Tải video lên để bắt đầu chỉnh sửa.</div>}
          {mode === "image" && imageAssets.length === 0 && !isLoading && <div className="media-studio__empty">Chưa có ảnh nào trong conversation này.</div>}
        </section>
      </div>
    </Modal>
      <Modal
        open={Boolean(deleteCandidate)}
        onClose={isBusy ? undefined : () => setDeleteCandidate(null)}
        closeDisabled={isBusy}
        title="Xoá ảnh"
        size="sm"
        footer={
          <div className="media-studio__delete-confirm-actions">
            <button type="button" className="media-studio__delete-cancel" onClick={() => setDeleteCandidate(null)} disabled={isBusy}>Huỷ</button>
            <button type="button" className="media-studio__delete-confirm" onClick={confirmDeleteImage} disabled={isBusy}>{isBusy ? "Đang xoá..." : "Xoá ảnh"}</button>
          </div>
        }
      >
        <div className="media-studio__delete-confirm-content">
          <div className="media-studio__delete-confirm-icon"><FiTrash2 /></div>
          <div>
            <p>Bạn có chắc muốn xoá ảnh này?</p>
            <span>Ảnh sẽ được xoá khỏi conversation và không thể khôi phục.</span>
          </div>
        </div>
      </Modal>
    </>  );
}

function VideoEditorForm({ isBusy, videoFile, setVideoFile, videoInputRef, operation, setOperation, ratio, setRatio, start, setStart, end, setEnd, text, setText, position, setPosition, fontSize, setFontSize, textColor, setTextColor, volume, setVolume, entries, setEntries, selectedVideo, videoAssets, sourceAssetId, mergeSelection, setMergeSelection, onExecute }) {
  const needsTiming = ["trim", "text_overlay", "cta_overlay"].includes(operation);
  const addEntry = () => setEntries([...entries, { text: "", start: "0", end: "3" }]);
  return <>
    <div className="media-studio__eyebrow"><FiVideo /> Chỉnh sửa video kỹ thuật</div>
    <p className="media-studio__hint">Chọn video trong thư viện hoặc tải video mới lên, rồi chọn operation có kiểm soát.</p>
    <label className="media-studio__upload"><span><FiUpload /> {videoFile ? videoFile.name : selectedVideo ? `Đang chọn V${selectedVideo.version_number}` : "Tải video lên"}</span><input ref={videoInputRef} type="file" accept="video/mp4,video/quicktime,video/webm" onChange={(event) => { setVideoFile(event.target.files?.[0] || null); }} disabled={isBusy} /></label>
    <label className="media-studio__field">Operation<select value={operation} onChange={(event) => setOperation(event.target.value)} disabled={isBusy}>{VIDEO_OPERATIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    {needsTiming && <div className="media-studio__inline-fields"><label>Start<input type="number" min="0" step="0.1" value={start} onChange={(event) => setStart(event.target.value)} /></label><label>End<input type="number" min="0.1" step="0.1" value={end} onChange={(event) => setEnd(event.target.value)} /></label></div>}
    {operation === "aspect_crop" && <label className="media-studio__field">Tỷ lệ<select value={ratio} onChange={(event) => setRatio(event.target.value)}>{VIDEO_RATIOS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
    {["text_overlay", "cta_overlay"].includes(operation) && <><label className="media-studio__field">Text<textarea value={text} onChange={(event) => setText(event.target.value)} rows={3} maxLength={500} /></label><div className="media-studio__inline-fields"><label>Vị trí<select value={position} onChange={(event) => setPosition(event.target.value)}><option value="top">Trên</option><option value="center">Giữa</option><option value="bottom">Dưới</option></select></label><label>Cỡ chữ<input type="number" min="12" max="160" value={fontSize} onChange={(event) => setFontSize(event.target.value)} /></label><label>Màu<select value={textColor} onChange={(event) => setTextColor(event.target.value)}><option value="white">Trắng</option><option value="black">Đen</option><option value="yellow">Vàng</option></select></label></div></>}
    {operation === "subtitle" && <div className="media-studio__subtitle-list">{entries.map((entry, index) => <div className="media-studio__subtitle-row" key={`${index}-${entry.start}`}><textarea placeholder="Nội dung subtitle" value={entry.text} onChange={(event) => setEntries(entries.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} /><input type="number" min="0" step="0.1" value={entry.start} onChange={(event) => setEntries(entries.map((item, itemIndex) => itemIndex === index ? { ...item, start: event.target.value } : item))} /><input type="number" min="0.1" step="0.1" value={entry.end} onChange={(event) => setEntries(entries.map((item, itemIndex) => itemIndex === index ? { ...item, end: event.target.value } : item))} />{entries.length > 1 && <button type="button" onClick={() => setEntries(entries.filter((_, itemIndex) => itemIndex !== index))}><FiTrash2 /></button>}</div>)}<button type="button" className="media-studio__secondary" onClick={addEntry}><FiPlus /> Thêm subtitle</button></div>}
    {operation === "merge" && <div className="media-studio__merge-list"><span>Chọn video để ghép cùng source:</span>{videoAssets.filter((asset) => asset.status === "completed" && asset.id !== sourceAssetId).map((asset) => <label key={asset.id}><input type="checkbox" checked={mergeSelection.includes(asset.id)} onChange={(event) => setMergeSelection(event.target.checked ? [...mergeSelection, asset.id] : mergeSelection.filter((id) => id !== asset.id))} /> V{asset.version_number} · {asset.filename}</label>)}</div>}    {operation === "volume" && <label className="media-studio__field">Âm lượng (0–4)<input type="number" min="0" max="4" step="0.1" value={volume} onChange={(event) => setVolume(event.target.value)} /></label>}
    <button type="button" className="media-studio__generate" onClick={onExecute} disabled={isBusy || (!videoFile && !selectedVideo)}>{isBusy ? <FiLoader className="spin" /> : <FiVideo />} {isBusy ? "Đang xử lý video..." : "Tạo version video"}</button>
  </>;
}

function ConversationalEditor({ isBusy, selectedVideo, instruction, setInstruction, plan, execution, onPlan, onExecute, onPreviewAsset, onDownloadAsset }) {
  return <div className="media-studio__ai-generation media-studio__conversation-editor">
    <div className="media-studio__eyebrow"><FiEdit3 /> Chỉnh sửa video bằng hội thoại</div>
    <p className="media-studio__hint">Chọn source trong thư viện, mô tả yêu cầu, xem kế hoạch có cấu trúc rồi mới thực thi.</p>
    <textarea value={instruction} onChange={(event) => setInstruction(event.target.value)} placeholder="Ví dụ: cắt video còn 15 giây, đổi sang 9:16, thêm CTA..." rows={4} maxLength={2000} disabled={isBusy} />
    <button type="button" className="media-studio__secondary" onClick={onPlan} disabled={!selectedVideo || !instruction.trim() || isBusy}>{isBusy ? <FiLoader className="spin" /> : <FiEdit3 />} Phân tích kế hoạch</button>
    {plan && <div className="media-studio__status">
      <strong>Kế hoạch cho V{selectedVideo?.version_number}:</strong>
      <ol>{getConversationalOperationNames(plan).map((operation, index) => <li key={`${operation}-${index}`}>{operation}</li>)}</ol>
      <button type="button" className="media-studio__generate" onClick={onExecute} disabled={isBusy}>{isBusy ? <FiLoader className="spin" /> : <FiVideo />} {execution?.status === "processing" ? "Kiểm tra trạng thái" : "Thực thi kế hoạch"}</button>
    </div>}
    {execution && <div className="media-studio__status">
      <strong>{execution.status === "completed" ? "Hoàn tất" : execution.status === "partial" ? "Hoàn tất một phần" : "Thất bại"}</strong>
      {execution.failedOperation && <p className="media-studio__execution-failure">Thao tác thất bại: {execution.failedOperation}{Number.isInteger(execution.failedOperationIndex) ? " (bước " + (execution.failedOperationIndex + 1) + ")" : ""}</p>}
      <p>{execution.message}</p>
      {execution.createdAssetCount > 0 && <span>{execution.createdAssetCount} version đã tạo vẫn có thể preview/tải xuống.</span>}
      {execution.libraryReloadFailed && <span>Không thể tải lại thư viện; các version hoàn tất vẫn được giữ lại bên dưới.</span>}
      {execution.createdAssets?.filter((asset) => asset?.status === "completed").map((asset) => <div className="media-studio__recovery-asset" key={asset.id}>
        <span>V{asset.version_number} · {asset.operation}</span>
        <div className="media-studio__asset-actions">
          <button type="button" onClick={() => onPreviewAsset(asset)} title="Xem asset"><FiMaximize2 /></button>
          <button type="button" onClick={() => onDownloadAsset(asset)} title="Tải xuống"><FiDownload /></button>
        </div>
      </div>)}
    </div>}
  </div>;
}
export default MediaStudio;
