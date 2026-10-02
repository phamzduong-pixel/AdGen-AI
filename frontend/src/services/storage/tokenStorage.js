const ACCESS_TOKEN_KEY = "access_token";

const tokenStorage = {
  getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  setAccessToken(token) {
    if (!token) return;

    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  },

  removeAccessToken() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },

  hasAccessToken() {
    return Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));
  },
};

export default tokenStorage;
