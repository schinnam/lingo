import axios from 'axios'

export interface Features {
  discovery: boolean
  relationships: boolean
  voting: boolean
  staleness: boolean
}

export async function fetchFeatures(): Promise<Features> {
  const res = await axios.get<Features>('/api/v1/features')
  return res.data
}
