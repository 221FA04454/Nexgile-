import { useCallback, useEffect, useState } from "react";

export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.resolve()
      .then(fetcher)
      .then((result) => {
        if (alive) setData(result);
      })
      .catch((err) => {
        if (alive) setError(err.message || "Unable to load");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => reload(), [reload]);

  return { data, loading, error, reload, setData };
}
