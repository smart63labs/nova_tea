import { useState, useEffect, useCallback, useRef } from 'react';

export interface ProcessingItem {
  id: string;
  file: File;
  status: 'queued' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  processedContent: string | null;
  taskId: string | null;
  error: string | null;
}

export interface ProcessingState {
  items: ProcessingItem[];
  isProcessing: boolean;
}

export function useDoclingProcessing() {
  const [items, setItems] = useState<ProcessingItem[]>([]);
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isProcessing = items.some(i => ['uploading', 'processing', 'queued'].includes(i.status));

  const addFiles = useCallback((files: File[]) => {
    const newItems: ProcessingItem[] = files.map(file => ({
      id: Math.random().toString(36).substring(7),
      file,
      status: 'queued',
      progress: 0,
      message: 'Aguardando início...',
      processedContent: null,
      taskId: null,
      error: null
    }));

    setItems(prev => [...prev, ...newItems]);
    // Removed auto-start: processNext(newItems);
  }, []);

  const updateItem = useCallback((id: string, updates: Partial<ProcessingItem>) => {
      setItems(prev => prev.map(item => item.id === id ? { ...item, ...updates } : item));
  }, []);

  const startSingleProcessing = useCallback(async (item: ProcessingItem) => {
      updateItem(item.id, { status: 'uploading', message: 'Enviando...', progress: 0 });

      const formData = new FormData();
      formData.append('file', item.file);

      try {
        const res = await fetch('/api/knowledge/process', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (res.ok && data.status === 'queued') {
            updateItem(item.id, { status: 'processing', message: 'Processando (IA)...', taskId: data.task_id, progress: 10 });
        } else if (res.ok && data.status === 'processed') {
            updateItem(item.id, { 
                status: 'completed', 
                message: 'Concluído', 
                processedContent: data.processed_content, 
                progress: 100 
            });
        } else {
            updateItem(item.id, { 
                status: 'failed', 
                error: data.error || 'Erro ao processar arquivo.',
                message: 'Erro'
            });
        }
      } catch {
          updateItem(item.id, { 
              status: 'failed', 
              error: 'Erro de conexão.',
              message: 'Erro'
          });
      }
  }, [updateItem]);

  const startProcessing = useCallback((itemIds?: string[]) => {
      setItems(prevItems => {
          const itemsToProcess = itemIds
              ? prevItems.filter(i => itemIds.includes(i.id) && i.status === 'queued')
              : prevItems.filter(i => i.status === 'queued');

          itemsToProcess.forEach(item => {
              startSingleProcessing(item);
          });

          return prevItems;
      });
  }, [startSingleProcessing]);

  const removeItem = useCallback((id: string) => {
      setItems(prev => prev.filter(i => i.id !== id));
  }, []);

  const reset = useCallback(() => {
      if (pollingRef.current) clearTimeout(pollingRef.current);
      setItems([]);
  }, []);

  // Keep a ref to items to avoid stale closures in the polling interval
  const itemsRef = useRef(items);
  useEffect(() => {
      itemsRef.current = items;
  }, [items]);

  // Polling Effect
  useEffect(() => {
      let timeoutId: ReturnType<typeof setTimeout>;
      
      const poll = async () => {
          // Use ref to get the latest items state
          const activeItems = itemsRef.current.filter(i => i.status === 'processing' && i.taskId);
          if (activeItems.length === 0) return;

          await Promise.all(activeItems.map(async (item) => {
              try {
                  const res = await fetch(`/api/knowledge/status/${item.taskId}`);
                  if (res.ok) {
                      const status = await res.json();
                      
                      setItems(prev => prev.map(prevItem => {
                          if (prevItem.id !== item.id) return prevItem;
                          
                          if (status.status === 'completed') {
                              return {
                                  ...prevItem,
                                  status: 'completed',
                                  processedContent: status.result,
                                  progress: 100,
                                  message: 'Concluído',
                                  taskId: null
                              };
                          } else if (status.status === 'failed') {
                              return {
                                  ...prevItem,
                                  status: 'failed',
                                  error: status.error || "Falha",
                                  message: 'Erro',
                                  taskId: null
                              };
                          } else {
                              return {
                                  ...prevItem,
                                  progress: status.progress || prevItem.progress,
                                  message: status.message || prevItem.message
                              };
                          }
                      }));
                  }
              } catch (e) {
                  console.error("Polling error for " + item.id, e);
              }
          }));

          timeoutId = setTimeout(poll, 1000);
      };

      if (items.some(i => i.status === 'processing')) {
          poll();
      }

      return () => clearTimeout(timeoutId);
  }, [items.some(i => i.status === 'processing')]);

  return { items, isProcessing, addFiles, removeItem, reset, startProcessing };
}
