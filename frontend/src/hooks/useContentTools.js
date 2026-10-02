import { useCallback, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  evaluateContent,
  generateContentVariants,
} from "../services/api/contentToolsApi";
import { getUserErrorMessage } from "../utils/apiError";

const numericMessageId = (message) => {
  const id = Number(message?.id);
  return Number.isInteger(id) && id > 0 ? id : null;
};

function useContentTools() {
  const toast = useToast();
  const [activeMessage, setActiveMessage] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [variants, setVariants] = useState([]);
  const [variantEvaluations, setVariantEvaluations] = useState({});
  const [selectedLabels, setSelectedLabels] = useState([]);
  const [primaryLabel, setPrimaryLabel] = useState("");
  const [mode, setMode] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluatingLabels, setEvaluatingLabels] = useState([]);

  const close = useCallback(() => {
    if (isLoading || evaluatingLabels.length) return;
    setMode(null);
  }, [isLoading, evaluatingLabels.length]);

  const openEvaluation = async (message, options = {}) => {
    const messageId = options.savedContentId ? null : numericMessageId(message);
    const savedContentId = Number(options.savedContentId) || null;
    if ((!messageId && !savedContentId) || isLoading) {
      if (!messageId && !savedContentId) {
        toast.warning("Hãy chờ phản hồi được đồng bộ trước khi đánh giá.");
      }
      return;
    }

    setActiveMessage(message);
    setMode("evaluation");
    setEvaluation(null);
    setIsLoading(true);
    try {
      setEvaluation(await evaluateContent({ messageId, savedContentId }));
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể đánh giá nội dung lúc này."),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const openVariants = async (message, options = {}) => {
    const messageId = options.savedContentId ? null : numericMessageId(message);
    const savedContentId = Number(options.savedContentId) || null;
    if ((!messageId && !savedContentId) || isLoading) {
      if (!messageId && !savedContentId) {
        toast.warning("Hãy chờ phản hồi được đồng bộ trước khi tạo A/B.");
      }
      return;
    }

    setActiveMessage(message);
    setMode("variants");
    setVariants([]);
    setVariantEvaluations({});
    setSelectedLabels([]);
    setPrimaryLabel("");
    setIsLoading(true);
    try {
      const data = await generateContentVariants({ messageId, savedContentId });
      setVariants(Array.isArray(data?.variants) ? data.variants : []);
    } catch (error) {
      toast.error(
        getUserErrorMessage(error, "Không thể tạo phiên bản A/B lúc này."),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const evaluateVariant = async (variant) => {
    if (variantEvaluations[variant.label] || evaluatingLabels.includes(variant.label)) {
      return variantEvaluations[variant.label];
    }

    setEvaluatingLabels((current) => [...current, variant.label]);
    try {
      const result = await evaluateContent({
        content: [variant.title, variant.content, `CTA: ${variant.cta}`]
          .filter(Boolean)
          .join("\n\n"),
      });
      setVariantEvaluations((current) => ({
        ...current,
        [variant.label]: result,
      }));
      return result;
    } catch (error) {
      toast.error(
        getUserErrorMessage(
          error,
          `Không thể đánh giá phiên bản ${variant.label}.`,
        ),
      );
      return null;
    } finally {
      setEvaluatingLabels((current) =>
        current.filter((label) => label !== variant.label),
      );
    }
  };

  const evaluateSelected = async () => {
    const chosen = variants.filter((variant) =>
      selectedLabels.includes(variant.label),
    );
    await Promise.all(chosen.map(evaluateVariant));
  };

  const toggleComparison = (label) => {
    setSelectedLabels((current) =>
      current.includes(label)
        ? current.filter((item) => item !== label)
        : current.length < 3
          ? [...current, label]
          : current,
    );
  };

  return {
    activeMessage,
    evaluation,
    variants,
    variantEvaluations,
    selectedLabels,
    primaryLabel,
    mode,
    isLoading,
    evaluatingLabels: new Set(evaluatingLabels),
    close,
    openEvaluation,
    openVariants,
    evaluateVariant,
    evaluateSelected,
    toggleComparison,
    setPrimaryLabel,
  };
}

export default useContentTools;
