import { useState, useMemo, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Upload, Loader2, AlertCircle, Trash2, File as FileIcon, Plus, ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ProcessingItem } from '@/hooks/useDoclingProcessing';

interface DoclingUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (files: File[]) => Promise<void>;
  storeName: string;
  processingState: {
      items: ProcessingItem[];
      isProcessing: boolean;
  };
  onAddFiles: (files: File[]) => void;
  onRemoveFile: (id: string) => void;
  onReset: () => void;
  startProcessing: (itemIds?: string[]) => void;
}

export function DoclingUploadModal({ 
    isOpen, 
    onClose, 
    onConfirm, 
    storeName,
    processingState,
    onAddFiles,
    onRemoveFile,
    onReset,
    startProcessing
}: DoclingUploadModalProps) {
  // Safe destructuring with default values
  const { items = [], isProcessing = false } = processingState || {};

  const [isUploading, setIsUploading] = useState(false);
  const [uploadFormat, setUploadFormat] = useState<'processed' | 'original' | 'both'>('processed');
  
  // Selection and Pagination State
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<'processed' | 'original'>('processed');
  const [currentPage, setCurrentPage] = useState(1);

  // Auto-select first item when items change and nothing is selected
  useEffect(() => {
    if (items.length > 0 && !selectedItemId) {
      setSelectedItemId(items[0].id);
    } else if (items.length === 0) {
      setSelectedItemId(null);
    }
  }, [items, selectedItemId]);

  // Derived state for the selected item
  const selectedItem = useMemo(() => 
    items.find(i => i.id === selectedItemId), 
  [items, selectedItemId]);

  // Pagination logic for selected item
  const processedPages = useMemo(() => {
    if (!selectedItem?.processedContent) return [];
    return selectedItem.processedContent.split(/<!-- Page \d+ -->/).filter(p => p.trim().length > 0);
  }, [selectedItem?.processedContent]);

  const currentProcessedContent = useMemo(() => {
    if (processedPages.length === 0) return selectedItem?.processedContent || '';
    // Adjust index (currentPage is 1-based)
    return processedPages[currentPage - 1] || '';
  }, [processedPages, currentPage, selectedItem]);

  // Reset pagination when selection changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedItemId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onAddFiles(Array.from(e.target.files));
    }
  };

  const [workflowState, setWorkflowState] = useState<'idle' | 'processing' | 'uploading'>('idle');

  // Auto-upload effect
  useEffect(() => {
      if (workflowState === 'processing') {
          const hasPending = items.some(i => ['queued', 'uploading', 'processing'].includes(i.status));
          const hasFailed = items.some(i => i.status === 'failed');
          
          if (!hasPending) {
              // Processing batch finished
              if (hasFailed) {
                  setWorkflowState('idle'); 
                  // Could add error toast here
              } else {
                  // All successful, proceed to upload
                  setWorkflowState('uploading');
                  handleConfirm();
              }
          }
      }
  }, [items, workflowState]);

  const handleStartWorkflow = () => {
    if (items.length === 0) return;

    if (uploadFormat === 'original') {
        // No processing needed, go straight to upload
        setWorkflowState('uploading');
        handleConfirm();
    } else {
        // Need processing first
        setWorkflowState('processing');
        startProcessing();
    }
  };

  const handleConfirm = async () => {
    // Only set uploading state if not already set (avoid double trigger from effect)
    if (workflowState !== 'uploading') setIsUploading(true); 
    
    try {
      const filesToUpload: File[] = [];
      const completedItems = items.filter(i => i.status === 'completed');

      if (uploadFormat === 'original') {
          // Upload originals for all items
          items.forEach(item => {
              filesToUpload.push(item.file);
          });
      } else if (uploadFormat === 'processed') {
          // Upload processed markdown for completed items only
          if (completedItems.length === 0) {
              setIsUploading(false);
              setWorkflowState('idle');
              return;
          }
          for (const item of completedItems) {
              const newFileName = item.file.name.replace(/\.[^/.]+$/, "") + ".md";
              const blob = new Blob([item.processedContent || ''], { type: 'text/markdown' });
              const markdownFile = new File([blob], newFileName, { type: 'text/markdown' });
              filesToUpload.push(markdownFile);
          }
      } else if (uploadFormat === 'both') {
          // Upload both for completed items
          if (completedItems.length === 0) {
             setIsUploading(false);
             setWorkflowState('idle');
             return;
          }
          for (const item of completedItems) {
              // Original
              filesToUpload.push(item.file);
              
              // Processed
              const newFileName = item.file.name.replace(/\.[^/.]+$/, "") + ".md";
              const blob = new Blob([item.processedContent || ''], { type: 'text/markdown' });
              const markdownFile = new File([blob], newFileName, { type: 'text/markdown' });
              filesToUpload.push(markdownFile);
          }
      }

      if (filesToUpload.length > 0) {
        await onConfirm(filesToUpload);
        onClose();
        onReset();
      }
    } catch (err) {
        console.error(err);
    } finally {
      setIsUploading(false);
      setWorkflowState('idle');
    }
  };

  const hasQueuedItems = items.some(i => i.status === 'queued');
  // showStartProcessing removed in favor of unified button


  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if(!open) onClose(); }}>
      <DialogContent className="max-w-7xl h-[90vh] flex flex-col p-0 gap-0 sm:rounded-xl z-[150]">
        <DialogHeader className="p-6 pb-4 shrink-0 border-b">
          <DialogTitle className="text-xl">Importação Inteligente de Documentos</DialogTitle>
          <DialogDescription>
            Processe documentos com IA antes de adicionar à base <strong>{storeName}</strong>.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex">
          {/* Left Sidebar: File Queue */}
          <div className="w-1/3 border-r bg-slate-50 flex flex-col h-full">
             <div className="p-4 border-b bg-white/50">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                   <Upload className="w-4 h-4" />
                   Fila de Arquivos ({items.length})
                </h3>
             </div>
             
             <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-400 border-2 border-dashed border-slate-200 rounded-lg bg-white">
                         <div className="p-3 bg-slate-50 rounded-full mb-2">
                             <Upload className="w-6 h-6" />
                         </div>
                         <p className="text-sm">Nenhum arquivo adicionado</p>
                    </div>
                ) : (
                    items.map(item => (
                        <div 
                           key={item.id}
                           onClick={() => setSelectedItemId(item.id)}
                           className={`p-3 rounded-lg border cursor-pointer transition-all ${
                               selectedItemId === item.id 
                               ? 'bg-white border-blue-400 shadow-md ring-1 ring-blue-400' 
                               : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'
                           }`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium truncate max-w-[180px]" title={item.file.name}>
                                    {item.file.name}
                                </span>
                                <Button 
                                    variant="ghost" 
                                    size="icon" 
                                    className="h-6 w-6 -mr-2 text-slate-400 hover:text-red-500"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onRemoveFile(item.id);
                                    }}
                                >
                                    <Trash2 className="w-3 h-3" />
                                </Button>
                            </div>
                            
                            <div className="space-y-1">
                                <div className="flex items-center justify-between text-xs text-slate-500">
                                    <span>{item.message}</span>
                                    <span>{item.progress}%</span>
                                </div>
                                <Progress value={item.progress} className={`h-1.5 ${
                                    item.status === 'completed' ? 'bg-green-100' : 
                                    item.status === 'failed' ? 'bg-red-100' : 'bg-slate-100'
                                }`} />
                            </div>
                        </div>
                    ))
                )}
             </div>

             <div className="p-4 border-t bg-white shrink-0">
                <div className="relative border-2 border-dashed border-slate-300 rounded-lg p-3 text-center hover:bg-slate-50 transition-colors cursor-pointer bg-slate-50/50">
                    <input 
                        type="file" 
                        multiple
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        onChange={handleFileChange}
                        accept=".pdf,.docx,.pptx,.html,.txt"
                    />
                    <div className="flex items-center justify-center gap-2 text-blue-600">
                        <Plus className="w-4 h-4" />
                        <span className="text-sm font-medium">Adicionar Arquivos</span>
                    </div>
                </div>
             </div>
          </div>

          {/* Right Main Area: Preview */}
          <div className="flex-1 flex flex-col h-full bg-white overflow-hidden relative">
             {selectedItem ? (
                 <>
                    <div className="border-b px-6 py-3 flex items-center justify-between bg-white shrink-0">
                        <h2 className="text-lg font-semibold truncate flex-1 mr-4" title={selectedItem.file.name}>
                            {selectedItem.file.name}
                        </h2>
                        <Tabs value={previewTab} onValueChange={(v) => setPreviewTab(v === 'original' ? 'original' : 'processed')} className="w-[300px]">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="processed">Processado</TabsTrigger>
                                <TabsTrigger value="original">Original</TabsTrigger>
                            </TabsList>
                        </Tabs>
                    </div>

                    <div className="flex-1 overflow-hidden relative bg-slate-50">
                        {previewTab === 'processed' ? (
                            selectedItem.status === 'completed' ? (
                                <div className="h-full flex flex-col">
                                    <div className="flex-1 overflow-y-auto p-8 bg-white shadow-sm max-w-3xl mx-auto w-full my-4 rounded-lg border">
                                        <div className="prose prose-slate max-w-none">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {currentProcessedContent}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                    
                                    {/* Pagination Controls */}
                                    {processedPages.length > 1 && (
                                        <div className="p-3 border-t bg-white flex items-center justify-center gap-4 shrink-0 shadow-sm z-10">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                                disabled={currentPage === 1}
                                            >
                                                <ChevronLeft className="w-4 h-4 mr-1" />
                                                Anterior
                                            </Button>
                                            <span className="text-sm font-medium">
                                                Página {currentPage} de {processedPages.length}
                                            </span>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => setCurrentPage(p => Math.min(processedPages.length, p + 1))}
                                                disabled={currentPage === processedPages.length}
                                            >
                                                Próxima
                                                <ChevronRight className="w-4 h-4 ml-1" />
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-3">
                                    {selectedItem.status === 'failed' ? (
                                        <>
                                            <AlertCircle className="w-10 h-10 text-red-400" />
                                            <p>Falha no processamento deste arquivo.</p>
                                            <p className="text-xs text-red-500">{selectedItem.error}</p>
                                        </>
                                    ) : selectedItem.status === 'queued' ? (
                                        <>
                                            <FileText className="w-10 h-10 text-slate-300" />
                                            <p>Aguardando início do processamento...</p>
                                            {uploadFormat === 'original' && <p className="text-xs text-slate-400">(Processamento não necessário para upload original)</p>}
                                        </>
                                    ) : (
                                        <>
                                            <Loader2 className="w-10 h-10 animate-spin text-blue-400" />
                                            <p>Processando conteúdo...</p>
                                        </>
                                    )}
                                </div>
                            )
                        ) : (
                            // Original File Preview
                            <div className="h-full w-full flex items-center justify-center bg-slate-100">
                                {selectedItem.file.type === 'application/pdf' || selectedItem.file.type.startsWith('image/') ? (
                                    <iframe 
                                        src={URL.createObjectURL(selectedItem.file)} 
                                        className="w-full h-full" 
                                        title="Original File Preview"
                                    />
                                ) : (
                                    <div className="text-center p-6 bg-white rounded-lg shadow-sm max-w-sm">
                                        <FileIcon className="w-12 h-12 mx-auto text-slate-400 mb-3" />
                                        <p className="text-slate-600 mb-2">Visualização não disponível para este formato.</p>
                                        <p className="text-xs text-slate-400">({selectedItem.file.type})</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                 </>
             ) : (
                 <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                     <Eye className="w-12 h-12 opacity-20" />
                     <p>Selecione um arquivo para visualizar</p>
                 </div>
             )}
          </div>
        </div>

        <DialogFooter className="flex-col gap-4 p-6 border-t bg-white shrink-0 z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          {items.length > 0 && (
            <div className="w-full bg-slate-50 p-3 rounded-lg border border-slate-100 flex flex-col gap-2">
                <span className="text-sm font-medium text-slate-700">Formato de Salvamento:</span>
                <div className="flex flex-wrap gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input 
                            type="radio" 
                            name="uploadFormat" 
                            value="processed" 
                            checked={uploadFormat === 'processed'} 
                            onChange={() => setUploadFormat('processed')}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-700">Processado (Markdown)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input 
                            type="radio" 
                            name="uploadFormat" 
                            value="original" 
                            checked={uploadFormat === 'original'} 
                            onChange={() => setUploadFormat('original')}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-700">Original</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input 
                            type="radio" 
                            name="uploadFormat" 
                            value="both" 
                            checked={uploadFormat === 'both'} 
                            onChange={() => setUploadFormat('both')}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-slate-700">Ambos (Original + Markdown)</span>
                    </label>
                </div>
                {uploadFormat !== 'original' && !items.some(i => i.status === 'completed') && !isProcessing && hasQueuedItems && (
                    <p className="text-xs text-blue-600 mt-1 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Clique em "Iniciar Processamento" para converter os arquivos.
                    </p>
                )}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="ghost" onClick={onClose} disabled={isUploading || workflowState !== 'idle'}>
                {isProcessing ? "Minimizar" : "Cancelar"}
            </Button>
            
            {items.length > 0 && (
                <Button 
                    onClick={handleStartWorkflow}
                    disabled={isUploading || workflowState !== 'idle'}
                    className={`${
                        uploadFormat === 'original' 
                        ? 'bg-blue-600 hover:bg-blue-700' 
                        : 'bg-purple-600 hover:bg-purple-700'
                    } text-white`}
                >
                    {workflowState === 'idle' ? (
                         <>
                            {uploadFormat === 'original' ? (
                                <>
                                    <Upload className="w-4 h-4 mr-2" />
                                    Importar Original
                                </>
                            ) : (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2" />
                                    {uploadFormat === 'both' ? 'Processar e Importar (Ambos)' : 'Processar e Importar'}
                                </>
                            )}
                         </>
                    ) : (
                        <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            {workflowState === 'processing' ? 'Processando...' : 'Enviando...'}
                        </>
                    )}
                </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
