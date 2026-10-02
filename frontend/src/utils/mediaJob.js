export const isVideoJobPending = (job) =>
  Boolean(job && ["queued", "processing"].includes(job.status));

export const getVideoJobErrorMessage = (job) => {
  const raw = String(job?.error_message || "").toLowerCase();
  if (raw.includes("429") || raw.includes("quota") || raw.includes("resource_exhausted")) {
    return "Dịch vụ video AI đang bị giới hạn quota hoặc rate limit. Hãy kiểm tra quota, usage tier và billing rồi thử lại sau.";
  }
  if (raw.includes("timeout") || raw.includes("timed out")) {
    return "Provider video không phản hồi kịp thời. Bạn có thể thử lại sau.";
  }
  if (raw.includes("download") || raw.includes("validation") || raw.includes("container")) {
    return "Video tạo ra không thể tải xuống hoặc không vượt qua kiểm tra output.";
  }
  if (raw.includes("unavailable") || raw.includes("chưa được cấu hình")) {
    return "Provider video hiện chưa khả dụng. Vui lòng kiểm tra cấu hình hệ thống.";
  }
  return "Không thể tạo video AI. Vui lòng thử lại sau.";
};

export const pollVideoJob = async ({
  initialJob,
  fetchJob,
  onUpdate,
  wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds)),
  isCancelled = () => false,
  maxAttempts = 30,
}) => {
  let job = initialJob;
  onUpdate?.(job);
  for (let attempt = 0; attempt < maxAttempts && isVideoJobPending(job); attempt += 1) {
    await wait(1500);
    if (isCancelled()) return job;
    job = await fetchJob(job.id);
    onUpdate?.(job);
  }
  return job;
};
