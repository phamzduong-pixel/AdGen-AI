import { useCallback, useEffect, useState } from "react";

import useToast from "../components/ui/Toast/useToast";
import {
  createBrand as createBrandApi,
  deleteBrand as deleteBrandApi,
  getBrands,
  setDefaultBrand as setDefaultBrandApi,
  updateBrand as updateBrandApi,
} from "../services/api/brandApi";
import { getUserErrorMessage } from "../utils/apiError";

function useBrands(query = "") {
  const toast = useToast();
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  const loadBrands = useCallback(async () => {
    setLoading(true);
    try {
      setBrands(await getBrands(query));
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải thương hiệu."));
    } finally {
      setLoading(false);
    }
  }, [query, toast]);

  useEffect(() => {
    const timer = window.setTimeout(loadBrands, query ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [loadBrands, query]);

  const run = async (action, successMessage) => {
    if (pending) return null;
    setPending(true);
    try {
      const result = await action();
      await loadBrands();
      toast.success(successMessage);
      return result;
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật thương hiệu."));
      return null;
    } finally {
      setPending(false);
    }
  };

  return {
    brands,
    loading,
    pending,
    reload: loadBrands,
    createBrand: (data) =>
      run(() => createBrandApi(data), "Đã tạo hồ sơ thương hiệu."),
    updateBrand: (id, data) =>
      run(() => updateBrandApi(id, data), "Đã cập nhật thương hiệu."),
    deleteBrand: (id) =>
      run(() => deleteBrandApi(id), "Đã xóa thương hiệu."),
    setDefaultBrand: (id) =>
      run(() => setDefaultBrandApi(id), "Đã đặt làm thương hiệu mặc định."),
  };
}

export default useBrands;
