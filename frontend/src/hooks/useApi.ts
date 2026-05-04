import { useCallback, useState } from 'react'

export function useApi<TArgs extends unknown[], TResult>(
  request: (...args: TArgs) => Promise<TResult>,
) {
  const [data, setData] = useState<TResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const execute = useCallback(
    async (...args: TArgs) => {
      setLoading(true)
      setError(null)

      try {
        const result = await request(...args)
        setData(result)
        return result
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [request],
  )

  return {
    data,
    loading,
    error,
    execute,
    setData,
  }
}
