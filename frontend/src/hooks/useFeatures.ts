import { useQuery } from '@tanstack/react-query'
import { fetchFeatures, type Features } from '../api/features'

const DEFAULT_FEATURES: Features = {
  discovery: false,
  relationships: false,
  voting: true,
  staleness: false,
}

export function useFeatures(): Features {
  const { data } = useQuery({
    queryKey: ['features'],
    queryFn: fetchFeatures,
    staleTime: Infinity,   // feature flags don't change at runtime
    retry: false,
  })
  return data ?? DEFAULT_FEATURES
}
