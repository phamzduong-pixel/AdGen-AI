# Project Tree

Cây thư mục source của dự án AdGen AI, được đồng bộ từ filesystem sau cleanup ngày 30/09/2026.

> Phạm vi gồm mã nguồn, tài liệu, migration, test và file cấu hình cần thiết.
> Loại khỏi cây chính: `.git`, `.agents`, cache, `node_modules`, `dist`, `venv`, `uploads` và database/runtime local.
> Các file `.env` không được liệt kê để tránh đưa thông tin môi trường vào tài liệu.
> `frontend/node_modules/` và `backend/venv/` còn một số binary bị Windows khóa nhưng vẫn được loại khỏi cây runtime.

```text
AdGenAI/
    ├── backend/
    │   ├── alembic/
    │   │   ├── versions/
    │   │   │   ├── 20260727_0001_initial_schema.py
    │   │   │   ├── 20260727_0002_ad_templates.py
    │   │   │   ├── 20260727_0003_google_auth.py
    │   │   │   ├── 20260727_0004_password_reset.py
    │   │   │   ├── 20260727_0005_email_verification_sessions.py
    │   │   │   ├── 20260727_0006_brand_profiles.py
    │   │   │   ├── 20260727_0007_content_editor_versions.py
    │   │   │   ├── 20260727_0008_campaign_primary_index.py
    │   │   │   ├── 20260727_0009_platform_names.py
    │   │   │   ├── 20260727_0010_default_platform_name.py
    │   │   │   └── 20260727_0011_campaign_platform_name.py
    │   │   ├── env.py
    │   │   └── script.py.mako
    │   ├── app/
    │   │   ├── api/
    │   │   │   ├── auth.py
    │   │   │   ├── brand.py
    │   │   │   ├── campaign.py
    │   │   │   ├── content.py
    │   │   │   ├── content_document.py
    │   │   │   ├── conversation.py
    │   │   │   ├── dashboard.py
    │   │   │   ├── message.py
    │   │   │   ├── saved_content.py
    │   │   │   ├── template.py
    │   │   │   ├── upload.py
    │   │   │   ├── user.py
    │   │   │   └── voiceover.py
    │   │   ├── core/
    │   │   │   ├── config.py
    │   │   │   ├── datetime_utils.py
    │   │   │   ├── platforms.py
    │   │   │   └── security.py
    │   │   ├── data/
    │   │   │   ├── __init__.py
    │   │   │   └── system_templates.py
    │   │   ├── database/
    │   │   │   └── database.py
    │   │   ├── models/
    │   │   │   ├── __init__.py
    │   │   │   ├── ad_template.py
    │   │   │   ├── brand.py
    │   │   │   ├── campaign.py
    │   │   │   ├── content_activity.py
    │   │   │   ├── content_document.py
    │   │   │   ├── conversation.py
    │   │   │   ├── email_verification.py
    │   │   │   ├── message.py
    │   │   │   ├── password_reset.py
    │   │   │   ├── saved_content.py
    │   │   │   ├── uploaded_file.py
    │   │   │   ├── user.py
    │   │   │   ├── user_session.py
    │   │   │   └── user_settings.py
    │   │   ├── prompts/
    │   │   │   ├── ad_brief.py
    │   │   │   ├── email.py
    │   │   │   ├── facebook.py
    │   │   │   ├── google_ads.py
    │   │   │   ├── instagram.py
    │   │   │   ├── landing_page.py
    │   │   │   ├── rewrite.py
    │   │   │   ├── seo.py
    │   │   │   ├── shopee.py
    │   │   │   ├── slogan.py
    │   │   │   ├── summarize.py
    │   │   │   ├── system_prompt.py
    │   │   │   ├── tiktok.py
    │   │   │   └── youtube.py
    │   │   ├── schemas/
    │   │   │   ├── ad_template.py
    │   │   │   ├── brand.py
    │   │   │   ├── campaign.py
    │   │   │   ├── content_activity.py
    │   │   │   ├── content_document.py
    │   │   │   ├── content_tools.py
    │   │   │   ├── conversation.py
    │   │   │   ├── dashboard.py
    │   │   │   ├── email_verification.py
    │   │   │   ├── message.py
    │   │   │   ├── password_reset.py
    │   │   │   ├── saved_content.py
    │   │   │   ├── session.py
    │   │   │   ├── token.py
    │   │   │   ├── user.py
    │   │   │   └── voiceover.py
    │   │   ├── services/
    │   │   │   ├── context_engine/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── context_pruner.py
    │   │   │   │   ├── intent_resolver.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── knowledge_base/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── learning_dataset/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── interfaces.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── multimodal/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── interfaces.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── output_validator/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── models.py
    │   │   │   │   ├── rules.py
    │   │   │   │   └── service.py
    │   │   │   ├── platform_intelligence/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── models.py
    │   │   │   │   ├── registry.py
    │   │   │   │   └── service.py
    │   │   │   ├── product_aware/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── trend_intelligence/
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── interfaces.py
    │   │   │   │   ├── models.py
    │   │   │   │   └── service.py
    │   │   │   ├── voiceover/
    │   │   │   │   ├── providers/
    │   │   │   │   │   ├── base.py
    │   │   │   │   │   ├── edge_tts_provider.py
    │   │   │   │   │   └── mock_provider.py
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── extractor.py
    │   │   │   │   ├── script_cleaner.py
    │   │   │   │   └── voiceover_service.py
    │   │   │   ├── ai_service.py
    │   │   │   ├── auth_service.py
    │   │   │   ├── brand_prompt.py
    │   │   │   ├── brand_service.py
    │   │   │   ├── campaign_service.py
    │   │   │   ├── content_activity_service.py
    │   │   │   ├── content_document_service.py
    │   │   │   ├── content_evaluation_service.py
    │   │   │   ├── content_tool_utils.py
    │   │   │   ├── content_variant_service.py
    │   │   │   ├── conversation_service.py
    │   │   │   ├── dashboard_service.py
    │   │   │   ├── email_service.py
    │   │   │   ├── email_verification_service.py
    │   │   │   ├── file_storage.py
    │   │   │   ├── google_auth_service.py
    │   │   │   ├── message_service.py
    │   │   │   ├── password_reset_service.py
    │   │   │   ├── prompt_service.py
    │   │   │   ├── saved_content_service.py
    │   │   │   ├── session_service.py
    │   │   │   ├── template_service.py
    │   │   │   ├── upload_service.py
    │   │   │   └── user_service.py
    │   │   ├── __init__.py
    │   │   └── main.py
    │   ├── tests/
    │   │   ├── test_auth_user.py
    │   │   ├── test_brands.py
    │   │   ├── test_campaign_dashboard.py
    │   │   ├── test_content_editor.py
    │   │   ├── test_content_tools.py
    │   │   ├── test_context_engine.py
    │   │   ├── test_conversation_management.py
    │   │   ├── test_dataset_classification.py
    │   │   ├── test_email_verification_sessions.py
    │   │   ├── test_extraction_suite.py
    │   │   ├── test_full_ai_quality_pipeline.py
    │   │   ├── test_knowledge_base.py
    │   │   ├── test_learning_dataset.py
    │   │   ├── test_multi_platform_differentiation.py
    │   │   ├── test_multimodal_architecture.py
    │   │   ├── test_multimodal_edit_commands.py
    │   │   ├── test_output_validator.py
    │   │   ├── test_password_reset.py
    │   │   ├── test_platform_intelligence.py
    │   │   ├── test_product_aware_differentiation.py
    │   │   ├── test_product_aware_engine.py
    │   │   ├── test_templates.py
    │   │   ├── test_trend_intelligence.py
    │   │   ├── test_trend_normalization.py
    │   │   ├── test_video_upload.py
    │   │   ├── test_voiceover_flow.py
    │   │   └── test_youtube_prompt.py
    │   ├── .dockerignore
    │   ├── .env.example
    │   ├── .gitignore
    │   ├── alembic.ini
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── docs/
    │   ├── 01-AdGen_AI_system.md
    │   ├── 02-chuc-nang-he-thong.md
    │   ├── 03-luong-xu-ly-ai.md
    │   ├── 04-co-so-du-lieu.md
    │   ├── 05-api-va-frontend.md
    │   ├── 06-trien-khai-va-van-hanh.md
    │   ├── 07-quy-uoc-dong-bo-tai-lieu.md
    │   ├── 09-ke-hoach-tao-anh-video.md
    │   ├── PROJECT_TREE.md
    │   └── README.md
    ├── frontend/
    │   ├── public/
    │   │   ├── _redirects
    │   │   ├── favicon.svg
    │   │   └── icons.svg
    │   ├── src/
    │   │   ├── assets/
    │   │   │   ├── hero.png
    │   │   │   ├── react.svg
    │   │   │   └── vite.svg
    │   │   ├── components/
    │   │   │   ├── auth/
    │   │   │   │   ├── GoogleLoginButton/
    │   │   │   │   │   ├── GoogleLoginButton.css
    │   │   │   │   │   └── GoogleLoginButton.jsx
    │   │   │   │   ├── OtpInput/
    │   │   │   │   │   ├── OtpInput.css
    │   │   │   │   │   └── OtpInput.jsx
    │   │   │   │   ├── PasswordInput/
    │   │   │   │   │   ├── PasswordInput.css
    │   │   │   │   │   └── PasswordInput.jsx
    │   │   │   │   ├── RecoveryLayout/
    │   │   │   │   │   ├── RecoveryLayout.css
    │   │   │   │   │   └── RecoveryLayout.jsx
    │   │   │   │   └── ProtectedRoute.jsx
    │   │   │   ├── brand/
    │   │   │   │   ├── BrandConsistencyPanel/
    │   │   │   │   │   ├── BrandConsistencyPanel.css
    │   │   │   │   │   └── BrandConsistencyPanel.jsx
    │   │   │   │   ├── BrandFormModal/
    │   │   │   │   │   ├── BrandFormModal.css
    │   │   │   │   │   └── BrandFormModal.jsx
    │   │   │   │   └── BrandSelector/
    │   │   │   │       ├── BrandSelector.css
    │   │   │   │       ├── BrandSelector.jsx
    │   │   │   │       └── index.js
    │   │   │   ├── campaign/
    │   │   │   │   ├── CampaignCard/
    │   │   │   │   │   ├── CampaignCard.css
    │   │   │   │   │   └── CampaignCard.jsx
    │   │   │   │   ├── CampaignContentCard/
    │   │   │   │   │   ├── CampaignContentCard.css
    │   │   │   │   │   └── CampaignContentCard.jsx
    │   │   │   │   ├── CampaignFilters/
    │   │   │   │   │   ├── CampaignFilters.css
    │   │   │   │   │   └── CampaignFilters.jsx
    │   │   │   │   ├── CampaignFormModal/
    │   │   │   │   │   ├── CampaignFormModal.css
    │   │   │   │   │   └── CampaignFormModal.jsx
    │   │   │   │   └── LibraryPickerModal/
    │   │   │   │       ├── LibraryPickerModal.css
    │   │   │   │       └── LibraryPickerModal.jsx
    │   │   │   ├── chat/
    │   │   │   │   ├── AdBriefForm/
    │   │   │   │   │   ├── AdBriefForm.css
    │   │   │   │   │   ├── AdBriefForm.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── ChatInput/
    │   │   │   │   │   ├── AttachmentPreview.jsx
    │   │   │   │   │   ├── ChatInput.css
    │   │   │   │   │   ├── ChatInput.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── ContentScorePanel/
    │   │   │   │   │   ├── ContentScorePanel.css
    │   │   │   │   │   ├── ContentScorePanel.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── EmptyState/
    │   │   │   │   │   ├── EmptyState.css
    │   │   │   │   │   ├── EmptyState.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── HamburgerButton/
    │   │   │   │   │   ├── HamburgerButton.css
    │   │   │   │   │   ├── HamburgerButton.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── Header/
    │   │   │   │   │   ├── HeaderActions/
    │   │   │   │   │   │   ├── HeaderActions.css
    │   │   │   │   │   │   ├── HeaderActions.jsx
    │   │   │   │   │   │   └── index.js
    │   │   │   │   │   ├── HeaderTitle/
    │   │   │   │   │   │   ├── HeaderTitle.css
    │   │   │   │   │   │   ├── HeaderTitle.jsx
    │   │   │   │   │   │   └── index.js
    │   │   │   │   │   ├── ConversationHeaderMenu.jsx
    │   │   │   │   │   ├── ExportMenu.jsx
    │   │   │   │   │   ├── Header.css
    │   │   │   │   │   ├── Header.jsx
    │   │   │   │   │   └── index.js
    │   │   │   │   ├── MessageActions/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── MessageActions.css
    │   │   │   │   │   └── MessageActions.jsx
    │   │   │   │   ├── MessageBubble/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── MessageAttachments.jsx
    │   │   │   │   │   ├── MessageBubble.css
    │   │   │   │   │   └── MessageBubble.jsx
    │   │   │   │   ├── MessageList/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── MessageList.css
    │   │   │   │   │   └── MessageList.jsx
    │   │   │   │   ├── MobileSidebar/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── MobileSidebar.css
    │   │   │   │   │   └── MobileSidebar.jsx
    │   │   │   │   ├── PromptSelector/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── PromptSelector.css
    │   │   │   │   │   └── PromptSelector.jsx
    │   │   │   │   ├── SavedContentPanel/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── SavedContentCard.jsx
    │   │   │   │   │   ├── SavedContentPanel.css
    │   │   │   │   │   └── SavedContentPanel.jsx
    │   │   │   │   ├── Sidebar/
    │   │   │   │   │   ├── ConversationItem/
    │   │   │   │   │   │   ├── ConversationItem.css
    │   │   │   │   │   │   ├── ConversationItem.jsx
    │   │   │   │   │   │   └── index.js
    │   │   │   │   │   ├── ConversationList/
    │   │   │   │   │   │   ├── ConversationList.css
    │   │   │   │   │   │   ├── ConversationList.jsx
    │   │   │   │   │   │   └── index.js
    │   │   │   │   │   ├── SidebarFooter/
    │   │   │   │   │   │   ├── index.js
    │   │   │   │   │   │   ├── SidebarFooter.css
    │   │   │   │   │   │   └── SidebarFooter.jsx
    │   │   │   │   │   ├── SidebarHeader/
    │   │   │   │   │   │   ├── index.js
    │   │   │   │   │   │   ├── SidebarHeader.css
    │   │   │   │   │   │   └── SidebarHeader.jsx
    │   │   │   │   │   ├── ConversationItem.css
    │   │   │   │   │   ├── ConversationItem.jsx
    │   │   │   │   │   ├── ConversationMenu.css
    │   │   │   │   │   ├── ConversationMenu.jsx
    │   │   │   │   │   ├── ConversationSearch.css
    │   │   │   │   │   ├── ConversationSearch.jsx
    │   │   │   │   │   ├── DeleteConversationModal.css
    │   │   │   │   │   ├── DeleteConversationModal.jsx
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── RenameConversation.jsx
    │   │   │   │   │   ├── Sidebar.css
    │   │   │   │   │   └── Sidebar.jsx
    │   │   │   │   ├── SidebarDrawer/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── SidebarDrawer.css
    │   │   │   │   │   └── SidebarDrawer.jsx
    │   │   │   │   ├── TypingIndicator/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── TypingIndicator.css
    │   │   │   │   │   └── TypingIndicator.jsx
    │   │   │   │   ├── VariantGeneratorModal/
    │   │   │   │   │   ├── index.js
    │   │   │   │   │   ├── VariantCard.jsx
    │   │   │   │   │   ├── VariantComparison.jsx
    │   │   │   │   │   ├── VariantGeneratorModal.css
    │   │   │   │   │   └── VariantGeneratorModal.jsx
    │   │   │   │   └── VoiceoverModal/
    │   │   │   │       ├── AudioPlayer.jsx
    │   │   │   │       ├── VoiceoverModal.css
    │   │   │   │       └── VoiceoverModal.jsx
    │   │   │   ├── dashboard/
    │   │   │   │   ├── ActivityChart/
    │   │   │   │   │   ├── ActivityChart.css
    │   │   │   │   │   └── ActivityChart.jsx
    │   │   │   │   ├── PlatformChart/
    │   │   │   │   │   ├── PlatformChart.css
    │   │   │   │   │   └── PlatformChart.jsx
    │   │   │   │   └── StatCard/
    │   │   │   │       ├── StatCard.css
    │   │   │   │       └── StatCard.jsx
    │   │   │   ├── editor/
    │   │   │   │   ├── AiRewritePanel/
    │   │   │   │   │   ├── AiRewritePanel.css
    │   │   │   │   │   └── AiRewritePanel.jsx
    │   │   │   │   ├── ContentEditorHeader/
    │   │   │   │   │   ├── ContentEditorHeader.css
    │   │   │   │   │   └── ContentEditorHeader.jsx
    │   │   │   │   ├── EditorToolbar/
    │   │   │   │   │   ├── EditorToolbar.css
    │   │   │   │   │   └── EditorToolbar.jsx
    │   │   │   │   ├── VersionCompareModal/
    │   │   │   │   │   ├── VersionCompareModal.css
    │   │   │   │   │   └── VersionCompareModal.jsx
    │   │   │   │   └── VersionHistoryPanel/
    │   │   │   │       ├── VersionHistoryPanel.css
    │   │   │   │       └── VersionHistoryPanel.jsx
    │   │   │   ├── navigation/
    │   │   │   │   └── AppNavigation/
    │   │   │   │       ├── AppNavigation.css
    │   │   │   │       ├── AppNavigation.jsx
    │   │   │   │       └── index.js
    │   │   │   ├── settings/
    │   │   │   │   ├── ActiveSessions/
    │   │   │   │   │   ├── ActiveSessions.css
    │   │   │   │   │   └── ActiveSessions.jsx
    │   │   │   │   └── ChangePasswordForm/
    │   │   │   │       ├── ChangePasswordForm.css
    │   │   │   │       └── ChangePasswordForm.jsx
    │   │   │   ├── templates/
    │   │   │   │   ├── TemplateCard/
    │   │   │   │   │   ├── TemplateCard.css
    │   │   │   │   │   └── TemplateCard.jsx
    │   │   │   │   ├── TemplateFilters/
    │   │   │   │   │   ├── TemplateFilters.css
    │   │   │   │   │   └── TemplateFilters.jsx
    │   │   │   │   ├── TemplateFormModal/
    │   │   │   │   │   ├── TemplateFormModal.css
    │   │   │   │   │   └── TemplateFormModal.jsx
    │   │   │   │   └── TemplateQuickStart/
    │   │   │   │       ├── TemplateQuickStart.css
    │   │   │   │       └── TemplateQuickStart.jsx
    │   │   │   └── ui/
    │   │   │       ├── Avatar/
    │   │   │       │   ├── Avatar.css
    │   │   │       │   └── Avatar.jsx
    │   │   │       ├── Button/
    │   │   │       │   ├── Button.css
    │   │   │       │   └── Button.jsx
    │   │   │       ├── Card/
    │   │   │       │   ├── Card.css
    │   │   │       │   └── Card.jsx
    │   │   │       ├── Divider/
    │   │   │       │   ├── Divider.css
    │   │   │       │   └── Divider.jsx
    │   │   │       ├── ErrorBoundary/
    │   │   │       │   ├── ErrorBoundary.css
    │   │   │       │   └── ErrorBoundary.jsx
    │   │   │       ├── IconButton/
    │   │   │       │   ├── IconButton.css
    │   │   │       │   └── IconButton.jsx
    │   │   │       ├── Input/
    │   │   │       │   ├── Input.css
    │   │   │       │   └── Input.jsx
    │   │   │       ├── Modal/
    │   │   │       │   ├── Modal.css
    │   │   │       │   └── Modal.jsx
    │   │   │       ├── Spinner/
    │   │   │       │   ├── Spinner.css
    │   │   │       │   └── Spinner.jsx
    │   │   │       ├── Textarea/
    │   │   │       │   ├── Textarea.css
    │   │   │       │   └── Textarea.jsx
    │   │   │       ├── Toast/
    │   │   │       │   ├── Toast.css
    │   │   │       │   ├── ToastContainer.jsx
    │   │   │       │   ├── ToastContext.js
    │   │   │       │   ├── ToastProvider.jsx
    │   │   │       │   └── useToast.js
    │   │   │       └── index.js
    │   │   ├── constants/
    │   │   │   ├── api.js
    │   │   │   ├── chat.js
    │   │   │   ├── colors.js
    │   │   │   ├── config.js
    │   │   │   ├── platforms.js
    │   │   │   └── routes.js
    │   │   ├── context/
    │   │   │   ├── AuthContext.jsx
    │   │   │   ├── AuthContextValue.js
    │   │   │   ├── ThemeContext.jsx
    │   │   │   └── ThemeContextValue.js
    │   │   ├── hooks/
    │   │   │   ├── useAuth.js
    │   │   │   ├── useBrands.js
    │   │   │   ├── useCampaignDetail.js
    │   │   │   ├── useCampaigns.js
    │   │   │   ├── useChat.js
    │   │   │   ├── useContentEditor.js
    │   │   │   ├── useContentTools.js
    │   │   │   ├── useConversation.js
    │   │   │   ├── useDashboard.js
    │   │   │   ├── useMediaQuery.js
    │   │   │   ├── useMessage.js
    │   │   │   ├── useSavedContents.js
    │   │   │   ├── useStreaming.js
    │   │   │   ├── useTemplates.js
    │   │   │   └── useTheme.js
    │   │   ├── layouts/
    │   │   │   ├── ChatLayout/
    │   │   │   │   ├── ChatLayout.css
    │   │   │   │   └── ChatLayout.jsx
    │   │   │   ├── WorkspaceLayout/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── WorkspaceLayout.css
    │   │   │   │   └── WorkspaceLayout.jsx
    │   │   │   └── MainLayout.jsx
    │   │   ├── pages/
    │   │   │   ├── Brands/
    │   │   │   │   ├── Brands.css
    │   │   │   │   ├── Brands.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── CampaignDetail/
    │   │   │   │   ├── CampaignDetail.css
    │   │   │   │   ├── CampaignDetail.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── Campaigns/
    │   │   │   │   ├── Campaigns.css
    │   │   │   │   ├── Campaigns.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── Chat/
    │   │   │   │   ├── Chat.css
    │   │   │   │   ├── Chat.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── ContentEditor/
    │   │   │   │   ├── ContentEditor.css
    │   │   │   │   ├── ContentEditor.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── Dashboard/
    │   │   │   │   ├── Dashboard.css
    │   │   │   │   ├── Dashboard.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── ForgotPassword/
    │   │   │   │   ├── ForgotPassword.jsx
    │   │   │   │   └── index.js
    │   │   │   ├── Library/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Library.css
    │   │   │   │   └── Library.jsx
    │   │   │   ├── Login/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Login.css
    │   │   │   │   └── Login.jsx
    │   │   │   ├── NotFound/
    │   │   │   │   ├── index.js
    │   │   │   │   └── NotFound.jsx
    │   │   │   ├── Profile/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Profile.css
    │   │   │   │   └── Profile.jsx
    │   │   │   ├── Register/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Register.css
    │   │   │   │   └── Register.jsx
    │   │   │   ├── ResetPassword/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── ResetPassword.css
    │   │   │   │   └── ResetPassword.jsx
    │   │   │   ├── Settings/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Settings.css
    │   │   │   │   └── Settings.jsx
    │   │   │   ├── Templates/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── Templates.css
    │   │   │   │   └── Templates.jsx
    │   │   │   ├── VerifyEmail/
    │   │   │   │   ├── index.js
    │   │   │   │   ├── VerifyEmail.css
    │   │   │   │   └── VerifyEmail.jsx
    │   │   │   └── VerifyResetCode/
    │   │   │       ├── index.js
    │   │   │       ├── VerifyResetCode.css
    │   │   │       └── VerifyResetCode.jsx
    │   │   ├── routes/
    │   │   │   ├── AppRoutes.jsx
    │   │   │   └── index.js
    │   │   ├── services/
    │   │   │   ├── api/
    │   │   │   │   ├── authApi.js
    │   │   │   │   ├── axios.js
    │   │   │   │   ├── brandApi.js
    │   │   │   │   ├── campaignApi.js
    │   │   │   │   ├── chatApi.js
    │   │   │   │   ├── contentEditorApi.js
    │   │   │   │   ├── contentToolsApi.js
    │   │   │   │   ├── conversationApi.js
    │   │   │   │   ├── dashboardApi.js
    │   │   │   │   ├── messageApi.js
    │   │   │   │   ├── quizApi.js
    │   │   │   │   ├── savedContentApi.js
    │   │   │   │   ├── templateApi.js
    │   │   │   │   ├── uploadApi.js
    │   │   │   │   ├── userApi.js
    │   │   │   │   └── voiceoverApi.js
    │   │   │   ├── storage/
    │   │   │   │   └── tokenStorage.js
    │   │   │   └── index.js
    │   │   ├── styles/
    │   │   │   ├── animations.css
    │   │   │   ├── globals.css
    │   │   │   ├── markdown.css
    │   │   │   ├── reset.css
    │   │   │   ├── scrollbar.css
    │   │   │   └── variables.css
    │   │   ├── utils/
    │   │   │   ├── adTemplate.js
    │   │   │   ├── apiError.js
    │   │   │   ├── authValidation.js
    │   │   │   ├── brandProfile.js
    │   │   │   ├── contentEditor.js
    │   │   │   ├── conversationTitle.js
    │   │   │   ├── copy.js
    │   │   │   ├── date.js
    │   │   │   ├── download.js
    │   │   │   ├── emailVerification.js
    │   │   │   ├── exportConversation.js
    │   │   │   ├── exportSavedContent.js
    │   │   │   ├── markdown.js
    │   │   │   ├── passwordReset.js
    │   │   │   ├── registrationError.js
    │   │   │   ├── settingsStorage.js
    │   │   │   └── storage.js
    │   │   ├── App.jsx
    │   │   ├── helpers.js
    │   │   ├── index.css
    │   │   └── main.jsx
    │   ├── tests/
    │   │   ├── adTemplate.test.js
    │   │   ├── authValidation.test.js
    │   │   ├── brandProfile.test.js
    │   │   ├── contentEditor.test.js
    │   │   ├── emailVerification.test.js
    │   │   ├── passwordReset.test.js
    │   │   ├── registrationError.test.js
    │   │   └── settingsStorage.test.js
    │   ├── .dockerignore
    │   ├── .env.example
    │   ├── .gitignore
    │   ├── Dockerfile
    │   ├── eslint.config.js
    │   ├── index.html
    │   ├── nginx.conf
    │   ├── package.json
    │   ├── package-lock.json
    │   ├── README.md
    │   └── vite.config.js
    ├── .env.example
    ├── .gitignore
    ├── docker-compose.yml
    ├── README.md
    └── render.yaml
```

## Ghi chú thư mục chính

- `backend/`: FastAPI, service nghiệp vụ, AI pipeline, database model, migration và test backend.
- `frontend/`: React/Vite, pages, components, hooks, API client, style và test frontend.
- `docs/`: tài liệu tổng quan, chức năng, luồng AI, CSDL, API, vận hành và cây dự án.
- `backend/alembic/versions/`: các migration schema; không tự ý xóa migration đã chạy.
- `backend/app/prompts/`: system prompt, prompt theo nền tảng và quy tắc ad brief.
- `backend/app/services/`: xử lý chat, AI, context, knowledge, trend, campaign, content và voiceover.

File này nên được cập nhật khi thêm module lớn, thay đổi cấu trúc thư mục hoặc thay đổi cách triển khai.

