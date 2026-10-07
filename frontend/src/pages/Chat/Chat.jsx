import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import "./Chat.css";

import ChatLayout from "../../layouts/ChatLayout/ChatLayout";

import Sidebar from "../../components/chat/Sidebar";
import Header from "../../components/chat/Header";
import MessageList from "../../components/chat/MessageList";
import MessageBubble from "../../components/chat/MessageBubble";
import TypingIndicator from "../../components/chat/TypingIndicator";
import ChatInput from "../../components/chat/ChatInput";
import EmptyState from "../../components/chat/EmptyState";
import MobileSidebar from "../../components/chat/MobileSidebar";
import ConversationHeaderMenu from "../../components/chat/Header/ConversationHeaderMenu";
import SavedContentPanel from "../../components/chat/SavedContentPanel";
import TrendReportPanel from "../../components/chat/TrendReportPanel/TrendReportPanel";
import ContentScorePanel from "../../components/chat/ContentScorePanel";
import VariantGeneratorModal from "../../components/chat/VariantGeneratorModal";
import BrandConsistencyPanel from "../../components/brand/BrandConsistencyPanel/BrandConsistencyPanel";
import VoiceoverModal from "../../components/chat/VoiceoverModal/VoiceoverModal";
import MediaStudio from "../../components/chat/MediaStudio/MediaStudio";

import { getMe } from "../../services/api/authApi";
import useChat from "../../hooks/useChat";
import useSavedContents from "../../hooks/useSavedContents";
import useContentTools from "../../hooks/useContentTools";
import useBrands from "../../hooks/useBrands";
import { checkBrandContent } from "../../services/api/brandApi";
import useToast from "../../components/ui/Toast/useToast";
import { getUserErrorMessage } from "../../utils/apiError";
import { createContentDocument } from "../../services/api/contentEditorApi";
import { getConversationDisplayTitle } from "../../utils/conversationTitle";
import { exportConversation } from "../../utils/exportConversation";
import { getPreferences } from "../../utils/settingsStorage";

function Chat() {
  const toast = useToast();
  const location = useLocation();
  const navigate = useNavigate();
  const preferences = getPreferences();
  const [promptType, setPromptType] = useState(
    () => getPreferences().defaultPlatform,
  );

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [currentUser, setCurrentUser] = useState(null);

  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isHeaderMenuOpen, setIsHeaderMenuOpen] = useState(false);
  const [isSavedContentOpen, setIsSavedContentOpen] = useState(false);
  const [isTrendReportsOpen, setIsTrendReportsOpen] = useState(false);
  const [isMediaStudioOpen, setIsMediaStudioOpen] = useState(false);
  const [templateRequest, setTemplateRequest] = useState(null);
  const [newConversationBrandId, setNewConversationBrandId] = useState(undefined);
  const [brandCheck, setBrandCheck] = useState({
    open: false,
    loading: false,
    result: null,
    brand: null,
  });
  const [voiceoverState, setVoiceoverState] = useState({
    open: false,
    text: "",
    messageId: null,
  });
  const [messageAudios, setMessageAudios] = useState({});

  const {
    conversations,
    selectedConversation,
    messages,
    isTyping,
    isLoadingConversations,
    isLoadingMessages,
    error,
    createConversation,
    selectConversation,
    sendMessage,
    editMessage,
    renameConversation,
    deleteConversation,
    togglePinConversation,
    clearConversationMessages,
    runMessageAction,
    stopGenerating,
    setConversationBrand,
  } = useChat();
  const { brands } = useBrands();
  const {
    savedContents,
    savedMessageIds,
    pendingMessageIds,
    isLoading: isLoadingSavedContents,
    toggleSavedMessage,
    deleteSavedContent,
    saveGeneratedContent,
    recordSavedMessageActivity,
  } = useSavedContents();
  const contentTools = useContentTools();
  const selectedConversationData = conversations.find(
    (conversation) => conversation.id === selectedConversation,
  );

  const currentConversationTitle = getConversationDisplayTitle(
    selectedConversationData,
  );
  const defaultBrand = brands.find((brand) => brand.is_default);
  const selectedBrandId = selectedConversation
    ? (selectedConversationData?.brand_id ?? null)
    : (newConversationBrandId === undefined
        ? (defaultBrand?.id ?? null)
        : newConversationBrandId);

  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const user = await getMe();

        setCurrentUser(user);
      } catch (error) {
        console.error("Không thể tải thông tin người dùng:", error);
      }
    };

    fetchCurrentUser();
  }, []);

  useEffect(() => {
    if (!location.state?.adTemplate) return;
    // Convert the router handoff into a single composer request.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTemplateRequest({
      template: location.state.adTemplate,
      id: location.state.templateRequestId || Date.now(),
    });
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const handleSend = ({
    content,
    promptType: selectedPromptType,
    platformName = "",
    attachments = [],
    adBrief = null,
    brandId = selectedBrandId,
  }) => {
    return sendMessage({
      content,
      promptType: selectedPromptType,
      platformName,
      attachments,
      adBrief,
      brandId,
    });
  };

  const handleBrandChange = async (brandId) => {
    if (selectedConversation) {
      await setConversationBrand(brandId);
      return;
    }
    setNewConversationBrandId(brandId);
  };

  const handleBrandCheck = async (message) => {
    const brandId = message.brand_id ?? selectedBrandId;
    const brand = brands.find((item) => item.id === brandId);
    if (!brand) {
      toast.error("Hãy chọn hồ sơ thương hiệu trước khi kiểm tra.");
      return;
    }
    setBrandCheck({ open: true, loading: true, result: null, brand });
    try {
      const result = await checkBrandContent(brand.id, message.content, promptType);
      setBrandCheck({ open: true, loading: false, result, brand });
    } catch (checkError) {
      toast.error(
        getUserErrorMessage(checkError, "Không thể kiểm tra nội dung thương hiệu."),
      );
      setBrandCheck((current) => ({ ...current, open: false, loading: false }));
    }
  };

  const ensureConversationForMedia = async () => {
    if (selectedConversation) return conversations.find((item) => item.id === selectedConversation);
    return createConversation();
  };

  const openContentEditor = async (message) => {
    const messageId = Number(message.id);
    if (!Number.isInteger(messageId) || messageId <= 0) {
      toast.warning("Hãy chờ phản hồi được đồng bộ trước khi chỉnh sửa.");
      return;
    }
    try {
      const contentDocument = await createContentDocument({
        source_message_id: messageId,
      });
      navigate(`/contents/${contentDocument.id}`);
    } catch (openError) {
      toast.error(
        getUserErrorMessage(openError, "Không thể mở trình soạn thảo."),
      );
    }
  };

  return (
    <>
    <ChatLayout
      sidebar={
        <>
          <Sidebar
            conversations={conversations}
            selectedConversation={selectedConversation}
            onCreateConversation={createConversation}
            onSelectConversation={selectConversation}
            collapsed={isSidebarCollapsed}
            onToggle={() => setIsSidebarCollapsed((previous) => !previous)}
            user={currentUser}
            onRenameConversation={renameConversation}
            onDeleteConversation={deleteConversation}
            onTogglePinConversation={togglePinConversation}
          />

          <MobileSidebar
            open={isMobileSidebarOpen}
            onClose={() => setIsMobileSidebarOpen(false)}
            conversations={conversations}
            selectedConversation={selectedConversation}
            onCreateConversation={async () => {
              await createConversation();
              setIsMobileSidebarOpen(false);
            }}
            onSelectConversation={(conversationId) => {
              selectConversation(conversationId);
              setIsMobileSidebarOpen(false);
            }}
            user={currentUser}
            onRenameConversation={renameConversation}
            onDeleteConversation={deleteConversation}
            onTogglePinConversation={togglePinConversation}
          />
        </>
      }
      header={
        <Header
          title={currentConversationTitle}
          onCreateConversation={createConversation}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          exportDisabled={!selectedConversation || messages.length === 0}
          onExport={(format) =>
            exportConversation(format, currentConversationTitle, messages)
          }
          onOpenConversationMenu={() =>
            selectedConversation && setIsHeaderMenuOpen(true)
          }
          onOpenSavedContents={() => setIsSavedContentOpen(true)}
          onOpenTrendReports={() => setIsTrendReportsOpen(true)}
          onOpenMedia={() => setIsMediaStudioOpen(true)}
        />
      }
      content={
        <MessageList
          isLoading={isLoadingMessages}
          autoScroll={preferences.autoScroll}
          isEmpty={!isLoadingMessages && messages.length === 0 && !error}
          scrollTrigger={`${selectedConversation || "new"}:${messages.length}`}
        >
          {error && <div className="chat-page-error">{error}</div>}

          {messages.length === 0 && !error ? (
            <EmptyState
              onTemplateSelect={(template) => {
                setTemplateRequest({
                  template,
                  id: Date.now(),
                });
              }}
            />
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  role={message.role}
                  content={message.content}
                  time={preferences.showMessageTime ? message.time : ""}
                  isStreaming={message.isStreaming}
                  attachments={message.attachments || []}
                  actionsDisabled={isTyping}
                  isSaved={savedMessageIds.has(Number(message.id))}
                  savePending={pendingMessageIds.has(Number(message.id))}
                  onToggleSave={
                    message.role === "assistant"
                      ? () => toggleSavedMessage(message)
                      : undefined
                  }
                  onEvaluate={
                    message.role === "assistant"
                      ? () => {
                          const saved = savedContents.find(
                            (item) => Number(item.message_id) === Number(message.id),
                          );
                          return contentTools.openEvaluation(
                            message,
                            saved ? { savedContentId: saved.id } : {},
                          );
                        }
                      : undefined
                  }
                  onGenerateVariants={
                    message.role === "assistant"
                      ? () => {
                          const saved = savedContents.find(
                            (item) => Number(item.message_id) === Number(message.id),
                          );
                          return contentTools.openVariants(
                            message,
                            saved ? { savedContentId: saved.id } : {},
                          );
                        }
                      : undefined
                  }
                  onCopied={
                    message.role === "assistant"
                      ? () => recordSavedMessageActivity(message.id, "copy")
                      : undefined
                  }
                  onCheckBrand={
                    message.role === "assistant" && (message.brand_id || selectedBrandId)
                      ? () => handleBrandCheck(message)
                      : undefined
                  }
                  onOpenEditor={
                    message.role === "assistant"
                      ? () => openContentEditor(message)
                      : undefined
                  }
                  onVoiceover={
                    message.role === "assistant"
                      ? () =>
                          setVoiceoverState({
                            open: true,
                            text: message.content,
                            messageId: message.id,
                          })
                      : undefined
                  }
                  audioData={messageAudios[message.id] || null}
                  onAction={
                    message.role === "assistant"
                      ? async (action) => {
                          const result = await runMessageAction(
                            message.id,
                            action,
                            promptType,
                          );
                          if (result && action === "alternative") {
                            await recordSavedMessageActivity(
                              message.id,
                              "regenerate",
                            );
                          }
                          return result;
                        }
                      : undefined
                  }
                  onEdit={
                    message.role === "user"
                      ? async (editedContent) => {
                          await editMessage({
                            messageId: message.id,
                            content: editedContent,
                            promptType: message.prompt_type || promptType,
                            platformName:
                              message.platform_name ||
                              message.ad_brief?.platform_name ||
                              "",
                          });
                        }
                      : undefined
                  }
                />
              ))}

              {isTyping && <TypingIndicator />}
            </>
          )}
        </MessageList>
      }
      footer={
        <ChatInput
          key={selectedConversation || "new-conversation"}
          conversationId={selectedConversation}
          onSend={handleSend}
          promptType={promptType}
          onPromptTypeChange={setPromptType}
          disabled={isTyping}
          isStreaming={isTyping}
          onStop={stopGenerating}
          templateRequest={
            isLoadingConversations ? null : templateRequest
          }
          onTemplateHandled={() => setTemplateRequest(null)}
          brands={brands}
          brandId={selectedBrandId}
          onBrandChange={handleBrandChange}
        />
      }
    />
    {isHeaderMenuOpen && selectedConversationData && (
      <ConversationHeaderMenu
        conversation={selectedConversationData}
        onClose={() => setIsHeaderMenuOpen(false)}
        onTogglePin={(isPinned) =>
          togglePinConversation(selectedConversation, isPinned)
        }
        onRename={(title) =>
          renameConversation(selectedConversation, title)
        }
        onExport={() =>
          exportConversation(
            preferences.defaultExportFormat || "markdown",
            currentConversationTitle,
            messages,
          )
        }
        onClearMessages={() =>
          clearConversationMessages(selectedConversation)
        }
        onDelete={() => deleteConversation(selectedConversation)}
      />
    )}
    <SavedContentPanel
      open={isSavedContentOpen}
      items={savedContents}
      isLoading={isLoadingSavedContents}
      pendingMessageIds={pendingMessageIds}
      onClose={() => setIsSavedContentOpen(false)}
      onDelete={deleteSavedContent}
      onEdit={async (item) => {
        try {
          const contentDocument = await createContentDocument({
            source_saved_content_id: item.id,
          });
          navigate(`/contents/${contentDocument.id}`);
        } catch (openError) {
          toast.error(
            getUserErrorMessage(openError, "Không thể mở trình soạn thảo."),
          );
        }
      }}
    />
    <TrendReportPanel
      open={isTrendReportsOpen}
      conversationId={selectedConversation}
      onClose={() => setIsTrendReportsOpen(false)}
    />
    <ContentScorePanel
      open={contentTools.mode === "evaluation"}
      result={contentTools.evaluation}
      loading={contentTools.isLoading}
      onClose={contentTools.close}
      onCreateImproved={async () => {
        const sourceMessage = contentTools.activeMessage;
        const result = contentTools.evaluation;
        if (!sourceMessage || !result) return;
        const customPrompt = [
          "Hãy tạo một bản cải thiện của phản hồi AI ngay trước đó.",
          `Ưu tiên khắc phục: ${result.improvements.join("; ")}.`,
          "Giữ nguyên mọi dữ kiện gốc và trả về nội dung hoàn chỉnh.",
          `Bản chỉnh sửa được đề xuất để tham khảo:\n${result.suggested_revision}`,
        ].join("\n\n").slice(0, 19_000);
        contentTools.close();
        await runMessageAction(
          sourceMessage.id,
          "improve",
          promptType,
          customPrompt,
        );
      }}
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
          conversationId: selectedConversation,
          title: `Phiên bản ${variant.label} – ${variant.title || variant.strategy}`,
          content,
          platform: promptType,
          platformName:
            messages.find((item) => item.role === "user")?.platform_name ||
            messages.find((item) => item.role === "user")?.ad_brief?.platform_name ||
            "",
          brandId: selectedBrandId,
        })
      }
    />
    <BrandConsistencyPanel
      open={brandCheck.open}
      loading={brandCheck.loading}
      result={brandCheck.result}
      brandName={brandCheck.brand?.name}
      onClose={() =>
        setBrandCheck({ open: false, loading: false, result: null, brand: null })
      }
    />
    <MediaStudio
      open={isMediaStudioOpen}
      onClose={() => setIsMediaStudioOpen(false)}
      conversationId={selectedConversation}
      onEnsureConversation={ensureConversationForMedia}
    />
    <VoiceoverModal
      isOpen={voiceoverState.open}
      initialText={voiceoverState.text}
      messageId={voiceoverState.messageId}
      onClose={() =>
        setVoiceoverState({ open: false, text: "", messageId: null })
      }
      onGenerated={(audioData) => {
        if (voiceoverState.messageId) {
          setMessageAudios((prev) => ({
            ...prev,
            [voiceoverState.messageId]: audioData,
          }));
        }
        toast.success("Đã tạo voiceover thành công!");
      }}
    />
    </>
  );
}

export default Chat;