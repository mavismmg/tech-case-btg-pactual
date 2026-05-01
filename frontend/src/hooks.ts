import { useCallback, useEffect, useState } from "react";

import { getUserFriendlyErrorMessage } from "./utils/errors";
import type { ErrorContext } from "./utils/errors";

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = [], errorContext: ErrorContext = "load") {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await loader());
    } catch (err) {
      setError(getUserFriendlyErrorMessage(err, errorContext));
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload };
}

export function errorMessage(err: unknown, context?: ErrorContext) {
  return getUserFriendlyErrorMessage(err, context);
}
