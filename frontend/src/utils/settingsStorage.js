export const PREFERENCES_KEY = "adgen_preferences";

export const DEFAULT_PREFERENCES = {
  theme: "system",
  autoScroll: true,
  showMessageTime: true,
  confirmBeforeDelete: true,
  openLatestConversation: true,
  defaultPlatform: "facebook",
  defaultTone: "professional",
  defaultLanguage: "vi",
  defaultLength: "medium",
  defaultExportFormat: "markdown",
  includeTimestamps: true,
};

export const getPreferences = () => {
  try {
    return {
      ...DEFAULT_PREFERENCES,
      ...JSON.parse(localStorage.getItem(PREFERENCES_KEY)),
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
};

export const savePreferences = (preferences) => {
  localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
};
