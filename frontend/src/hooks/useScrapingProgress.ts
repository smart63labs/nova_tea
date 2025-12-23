import { useState, useEffect, useCallback } from 'react';

interface ScrapingProgress {
  completed: number;
  total: number;
  current_url: string;
}

export interface ScrapingResult {
  url: string;
  status: 'success' | 'error';
  filename?: string;
  file_uri?: string;
  markdown_content?: string;
  preview?: unknown;
  scraper_type?: 'static' | 'dynamic';
  error?: string;
}

interface ScrapingStatus {
  task_id: string;
  status: 'initializing' | 'processing' | 'completed' | 'error' | 'cancelled';
  progress: ScrapingProgress;
  results: ScrapingResult[];
  error?: string;
}

/**
 * Hook para acompanhar progresso de tarefa de scraping
 */
export function useScrapingProgress(taskId: string | null) {
  const [status, setStatus] = useState<ScrapingStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!taskId) return;

    try {
      const response = await fetch(`/api/scraping/status/${taskId}`);
      if (!response.ok) {
        throw new Error('Falha ao obter status');
      }

      const data: ScrapingStatus = await response.json();
      setStatus(data);

      // Para polling se tarefa completou, teve erro ou foi cancelada
      if (['completed', 'error', 'cancelled'].includes(data.status)) {
        setIsPolling(false);
      }
    } catch (error) {
      console.error('Erro ao buscar status:', error);
      setIsPolling(false);
    }
  }, [taskId]);

  // Inicia polling quando taskId é definido
  useEffect(() => {
    if (taskId) {
      setIsPolling(true);
    }
  }, [taskId]);

  // Polling a cada 2 segundos
  useEffect(() => {
    if (!isPolling || !taskId) return;

    const interval = setInterval(fetchStatus, 2000);

    // Busca imediatamente
    fetchStatus();

    return () => clearInterval(interval);
  }, [isPolling, taskId, fetchStatus]);

  const cancelTask = useCallback(async () => {
    if (!taskId) return;

    try {
      const response = await fetch(`/api/scraping/cancel/${taskId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Falha ao cancelar tarefa');
      }

      setIsPolling(false);
    } catch (error) {
      console.error('Erro ao cancelar tarefa:', error);
    }
  }, [taskId]);

  return {
    status,
    isPolling,
    cancelTask,
  };
}
