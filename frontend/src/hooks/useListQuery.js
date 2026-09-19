import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const EMPTY_META = { total: 0, page: 1, page_size: 10, pages: 0 };

/**
 * 列表页通用逻辑：维护过滤条件与分页，并在条件变化时自动请求。
 * fetcher 允许每次渲染传入新函数，内部用 ref 保持稳定，避免重复请求。
 *
 * initialFilters 为首次进入时的筛选（可由 URL 参数推导，看板下钻场景）；
 * resetBase 为点击「重置」时恢复的基线（通常是页面自带的全空默认值）。
 */
export function useListQuery(fetcher, initialFilters = {}, pageSize = 10, resetBase = null) {
  const resetBaseRef = useRef(resetBase || initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const params = useMemo(
    () => ({ ...filters, page, page_size: pageSize }),
    [filters, page, pageSize],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current(params);
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    reload();
  }, [reload]);

  const updateFilter = useCallback((key, value) => {
    setPage(1);
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setPage(1);
    setFilters(resetBaseRef.current);
  }, []);

  return {
    items: data?.items ?? [],
    meta: data?.meta ?? EMPTY_META,
    loading,
    error,
    filters,
    page,
    pageSize,
    setPage,
    updateFilter,
    resetFilters,
    reload,
  };
}
