import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { TrustProfile } from "../../api/types";
import { getMockProfile } from "./trustMockData";

interface UseTrustProfileResult {
  profile: TrustProfile | null;
  loading: boolean;
  error: string | null;
}

export function useTrustProfile(
  subjectType: string | undefined,
  subjectId: string | undefined
): UseTrustProfileResult {
  const [profile, setProfile] = useState<TrustProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subjectType || !subjectId) {
      setLoading(false);
      return;
    }

    if (import.meta.env.VITE_TRUST_MOCK === "true") {
      setProfile(getMockProfile(subjectId));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    api
      .trustProfile(subjectType, subjectId)
      .then((p) => {
        setProfile(p);
      })
      .catch((e: Error) => {
        if (import.meta.env.DEV) {
          setProfile(getMockProfile(subjectId));
        } else {
          setError(e.message);
        }
      })
      .finally(() => setLoading(false));
  }, [subjectType, subjectId]);

  return { profile, loading, error };
}
