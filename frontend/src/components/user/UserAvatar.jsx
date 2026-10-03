import { useEffect, useState } from "react";

import { getUserAvatarBlob } from "../../services/api/userApi";

function UserAvatar({ user, className, fallback, alt = "Ảnh đại diện" }) {
  const [localSource, setLocalSource] = useState(null);
  const avatarUrl = user?.avatar_url;
  const isProtectedAvatar = avatarUrl === "/users/me/avatar";

  useEffect(() => {
    let active = true;
    let objectUrl = null;
    if (!isProtectedAvatar) return undefined;

    getUserAvatarBlob()
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setLocalSource(objectUrl);
      })
      .catch(() => {
        if (active) setLocalSource(null);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [isProtectedAvatar, user]);

  const source = isProtectedAvatar ? localSource : avatarUrl;
  return <div className={className}>{source ? <img src={source} alt={alt} /> : fallback}</div>;
}

export default UserAvatar;