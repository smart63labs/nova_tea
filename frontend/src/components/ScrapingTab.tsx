import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from '@/components/ui/accordion';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription
} from '@/components/ui/dialog';
import { Card, CardContent } from '@/components/ui/card';
import { Globe, CheckCircle2, XCircle, Loader2, X, Eye, UploadCloud, ChevronLeft, ChevronRight } from 'lucide-react';
import { useScrapingProgress } from '@/hooks/useScrapingProgress';
import type { ScrapingResult } from '@/hooks/useScrapingProgress';

interface ScrapingTabProps {
    stores: Array<{ name: string; display_name: string }>;
    isLoading?: boolean;
    error?: string | null;
    onRefresh?: () => Promise<void> | void;
}

interface ReviewItem {
    url: string;
    filename: string;
    markdown_content: string;
    status: 'pending' | 'uploaded' | 'error';
    error?: string;
}

export function ScrapingTab({ stores, isLoading, error: storesError, onRefresh }: ScrapingTabProps) {
    const [urlsText, setUrlsText] = useState('');
    const [selectedStore, setSelectedStore] = useState('');
    const [taskId, setTaskId] = useState<string | null>(null);
    const [error, setError] = useState('');
    const [isRecursive, setIsRecursive] = useState(false);

    // Estado para revisão
    const [reviewItem, setReviewItem] = useState<ReviewItem | null>(null);
    const [isReviewOpen, setIsReviewOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 4;

    // Estado para upload em lote
    const [uploadedFiles, setUploadedFiles] = useState<Set<string>>(new Set());
    const [isBatchUploading, setIsBatchUploading] = useState(false);
    const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 });

    const { status, isPolling, cancelTask } = useScrapingProgress(taskId);

    const [feedbackModal, setFeedbackModal] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({
        isOpen: false,
        type: 'success',
        message: ''
    });

    const validateUrls = (text: string) => {
        return text.split('\n')
            .map((url) => url.trim())
            .filter((url) => url.length > 0);
    };

    // Conta URLs válidas
    const urls = validateUrls(urlsText);

    const validUrlCount = urls.filter((url) => {
        try {
            // Valida usando o construtor URL nativo (mais seguro e robusto)
            const urlToTest = url.match(/^https?:\/\//) ? url : `https://${url}`;
            new URL(urlToTest);
            return url.includes('.');
        } catch {
            return false;
        }
    }).length;

    const handleProcess = async () => {
        setError('');
        setCurrentPage(1);

        if (urls.length === 0) {
            setError('Por favor, insira pelo menos uma URL');
            return;
        }

        if (!selectedStore) {
            setError('Por favor, selecione uma base de conhecimento');
            return;
        }

        try {
            const response = await fetch('/api/scraping/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    urls: urls,
                    store_name: selectedStore,
                    preview_only: true,
                    recursive: isRecursive
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Erro ao iniciar scraping');
            }

            const data = await response.json();
            setTaskId(data.task_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Erro desconhecido');
        }
    };

    const handleCancel = () => {
        cancelTask();
    };

    const handleReset = () => {
        setTaskId(null);
        setUrlsText('');
        setSelectedStore('');
        setError('');
        setReviewItem(null);
        setCurrentPage(1);
        setUploadedFiles(new Set());
        setBatchProgress({ current: 0, total: 0 });
    };

    const openReview = (result: ScrapingResult) => {
        setReviewItem({
            url: result.url,
            filename: result.filename || result.url,
            markdown_content: result.markdown_content || '',
            status: 'pending'
        });
        setIsReviewOpen(true);
    };

    const handleConfirmUpload = async () => {
        if (!reviewItem || !selectedStore) return;

        setUploading(true);
        try {
            const response = await fetch('/api/scraping/confirm_upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    markdown_content: reviewItem.markdown_content,
                    filename: reviewItem.filename,
                    store_name: selectedStore
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Falha no upload');
            }

            setReviewItem(prev => prev ? { ...prev, status: 'uploaded' } : null);
            setIsReviewOpen(false); // Fecha modal após sucesso

            // Adiciona aos arquivos carregados
            if (reviewItem.filename) {
                setUploadedFiles(prev => new Set(prev).add(reviewItem.filename));
            }

            setFeedbackModal({
                isOpen: true,
                type: 'success',
                message: 'Conteúdo adicionado à base de conhecimento com sucesso!'
            });

        } catch (err) {
            console.error(err);
            setReviewItem(prev => prev ? { ...prev, status: 'error', error: err instanceof Error ? err.message : 'Erro ao enviar' } : null);
            setFeedbackModal({
                isOpen: true,
                type: 'error',
                message: `Erro ao adicionar à base: ${err instanceof Error ? err.message : 'Erro desconhecido'}`
            });
        } finally {
            setUploading(false);
        }
    };

    const handleBatchUpload = async () => {
        if (!status?.results || !selectedStore) return;

        const filesToUpload = status.results.filter(r =>
            r.status === 'success' &&
            !!r.filename &&
            !uploadedFiles.has(r.filename) &&
            !!r.markdown_content
        );

        if (filesToUpload.length === 0) {
            setFeedbackModal({
                isOpen: true,
                type: 'success',
                message: 'Todos os arquivos válidos já foram adicionados!'
            });
            return;
        }

        setIsBatchUploading(true);
        setBatchProgress({ current: 0, total: filesToUpload.length });
        let successCount = 0;
        const errors: string[] = [];

        for (let i = 0; i < filesToUpload.length; i++) {
            const file = filesToUpload[i];
            const filename = file.filename || file.url;
            try {
                const response = await fetch('/api/scraping/confirm_upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        markdown_content: file.markdown_content,
                        filename: filename,
                        store_name: selectedStore
                    })
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    throw new Error(errData.error || 'Falha no upload');
                }

                setUploadedFiles(prev => new Set(prev).add(filename));
                successCount++;
            } catch (err) {
                console.error(`Erro ao enviar ${filename}:`, err);
                errors.push(filename);
            }

            setBatchProgress(prev => ({ ...prev, current: i + 1 }));
        }

        setIsBatchUploading(false);

        if (errors.length === 0) {
            setFeedbackModal({
                isOpen: true,
                type: 'success',
                message: `${successCount} arquivos adicionados com sucesso!`
            });
        } else {
            setFeedbackModal({
                isOpen: true,
                type: 'error',
                message: `${successCount} arquivos enviados. Falha em ${errors.length} arquivos.`
            });
        }
    };

    const progressPercentage = status
        ? (status.progress.completed / status.progress.total) * 100
        : 0;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 mb-4">
                <Globe className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Web Scraping</h3>
                {onRefresh && (
                    <Button
                        variant="outline"
                        size="sm"
                        className="ml-auto"
                        onClick={() => onRefresh()}
                        disabled={!!isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Atualizando...
                            </>
                        ) : (
                            'Atualizar bases'
                        )}
                    </Button>
                )}
            </div>

            <p className="text-sm text-muted-foreground">
                Extraia conteúdo de páginas web e adicione automaticamente à base de conhecimento.
                O sistema detecta automaticamente se o site é estático ou requer JavaScript.
            </p>

            {!taskId ? (
                <>
                    {/* Formulário de entrada */}
                    <div className="space-y-4">
                        <div>
                            <Label htmlFor="urls">URLs para Processar</Label>
                            <Textarea
                                id="urls"
                                placeholder="https://example.com&#10;https://another-site.com&#10;(uma URL por linha)"
                                value={urlsText}
                                onChange={(e) => setUrlsText(e.target.value)}
                                rows={6}
                                className="mt-2 font-mono text-sm"
                            />
                            <p className="text-xs text-muted-foreground mt-1">
                                {validUrlCount} URL{validUrlCount !== 1 ? 's' : ''} válida{validUrlCount !== 1 ? 's' : ''}
                            </p>
                        </div>

                        <div>
                            <div className="flex items-center space-x-2 my-4">
                                <Checkbox
                                    id="recursive"
                                    checked={isRecursive}
                                    onCheckedChange={(checked) => setIsRecursive(checked as boolean)}
                                />
                                <Label htmlFor="recursive" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                    Scraping Recursivo (incluir links internos)
                                </Label>
                            </div>

                            <Label htmlFor="store">Base de Conhecimento</Label>
                            {storesError && (
                                <div className="mt-2 text-xs text-red-600">
                                    {storesError}
                                </div>
                            )}
                            <select
                                id="store"
                                value={selectedStore}
                                onChange={(e) => setSelectedStore(e.target.value)}
                                className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            >
                                <option value="">Selecione uma base de conhecimento</option>
                                {stores.map((store) => (
                                    <option key={store.name} value={store.name}>
                                        {store.display_name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 p-3 rounded-md bg-red-50 border border-red-200 text-red-800 text-sm">
                                <XCircle className="h-4 w-4 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <Button
                            onClick={handleProcess}
                            disabled={urls.length === 0 || !selectedStore}
                            className="w-full"
                        >
                            <Globe className="h-4 w-4 mr-2" />
                            Processar URLs
                        </Button>
                    </div>
                </>
            ) : (
                <>
                    {/* Interface de progresso */}
                    <div className="space-y-4">
                        {/* Barra de progresso */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <Label>Progresso</Label>
                                <span className="text-sm text-muted-foreground">
                                    {status?.progress.completed || 0} / {status?.progress.total || 0}
                                </span>
                            </div>
                            <Progress value={progressPercentage} className="h-2" />
                        </div>

                        {/* URL atual */}
                        {status?.progress.current_url && (
                            <div className="flex items-center gap-2 p-3 rounded-md bg-blue-50 border border-blue-200 text-blue-800 text-sm">
                                <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
                                <span className="font-mono text-xs truncate w-full">{status.progress.current_url}</span>
                            </div>
                        )}

                        {/* Status */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {isPolling && <Loader2 className="h-4 w-4 animate-spin" />}
                                <span className="text-sm font-medium">
                                    Status:{' '}
                                    {status?.status === 'processing' && 'Processando...'}
                                    {status?.status === 'completed' && 'Concluído'}
                                    {status?.status === 'error' && 'Erro'}
                                    {status?.status === 'cancelled' && 'Cancelado'}
                                    {status?.status === 'initializing' && 'Inicializando...'}
                                </span>
                            </div>

                            {isPolling && (
                                <Button variant="outline" size="sm" onClick={handleCancel}>
                                    <X className="h-4 w-4 mr-2" />
                                    Cancelar
                                </Button>
                            )}
                        </div>

                        {/* Lista de resultados */}
                        {status && status.results.length > 0 && (
                            <div className="space-y-4">
                                <Label>Resultados ({status.results.length})</Label>

                                <div className="grid gap-3">
                                    {status.results
                                        .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
                                        .map((result, idx) => (
                                            <Card key={idx} className="overflow-hidden border shadow-sm hover:shadow-md transition-shadow">
                                                <CardContent className="p-3 flex items-center gap-3">
                                                    {result.status === 'success' ? (
                                                        <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />
                                                    ) : (
                                                        <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                                                    )}

                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-mono truncate mb-1" title={result.url}>{result.url}</p>
                                                        {result.status === 'success' ? (
                                                            <div className="flex items-center justify-between gap-2">
                                                                <div className="flex flex-col flex-1 min-w-0">
                                                                    <span className="text-xs text-muted-foreground font-medium truncate">
                                                                        {result.filename}
                                                                    </span>
                                                                    {!!result.filename && uploadedFiles.has(result.filename) && (
                                                                        <span className="text-[10px] text-green-600 font-medium flex items-center gap-1">
                                                                            <CheckCircle2 className="h-3 w-3" />
                                                                            Adicionado à base
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-[10px] text-gray-400 font-mono hidden sm:inline-block">
                                                                        Preview: {String(result.preview)}
                                                                    </span>
                                                                    <Button
                                                                        size="sm"
                                                                        variant="secondary"
                                                                        className="h-7 text-xs px-2"
                                                                        onClick={() => openReview(result)}
                                                                    >
                                                                        <Eye className="h-3 w-3 mr-1" />
                                                                        Revisar
                                                                    </Button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <p className="text-xs text-red-600 truncate">{result.error}</p>
                                                        )}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        ))}
                                </div>

                                {/* Paginação */}
                                {status.results.length > ITEMS_PER_PAGE && (
                                    <div className="flex items-center justify-between pt-2">
                                        <div className="text-xs text-muted-foreground">
                                            Página {currentPage} de {Math.ceil(status.results.length / ITEMS_PER_PAGE)}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                                disabled={currentPage === 1}
                                            >
                                                <ChevronLeft className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                onClick={() => setCurrentPage(p => Math.min(Math.ceil(status.results.length / ITEMS_PER_PAGE), p + 1))}
                                                disabled={currentPage >= Math.ceil(status.results.length / ITEMS_PER_PAGE)}
                                            >
                                                <ChevronRight className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Erro geral */}
                        {status?.error && (
                            <div className="flex items-center gap-2 p-3 rounded-md bg-red-50 border border-red-200 text-red-800 text-sm">
                                <XCircle className="h-4 w-4 flex-shrink-0" />
                                <span>{status.error}</span>
                            </div>
                        )}

                        {/* Botão de reset e Add All */}
                        {!isPolling && (
                            <div className="flex gap-2">
                                <Button onClick={handleReset} variant="outline" className="flex-1">
                                    Processar Novas URLs
                                </Button>
                                {status && status.results.some(r => r.status === 'success' && !!r.filename && !uploadedFiles.has(r.filename)) && (
                                    <Button
                                        onClick={handleBatchUpload}
                                        disabled={isBatchUploading}
                                        className="flex-1 bg-green-600 hover:bg-green-700"
                                    >
                                        {isBatchUploading ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Enviando ({batchProgress.current}/{batchProgress.total})
                                            </>
                                        ) : (
                                            <>
                                                <UploadCloud className="h-4 w-4 mr-2" />
                                                Adicionar Todos à Base
                                            </>
                                        )}
                                    </Button>
                                )}
                            </div>
                        )}
                    </div>
                </>
            )}

            {/* Modal de Revisão */}
            <Dialog open={isReviewOpen} onOpenChange={setIsReviewOpen}>
                <DialogContent className="max-w-[95vw] w-[1400px] h-[90vh] flex flex-col p-0 z-[200]">
                    <DialogHeader className="px-6 py-4 border-b">
                        <DialogTitle>Revisão de Conteúdo Extraído</DialogTitle>
                        <DialogDescription>
                            Revise o conteúdo extraído do site original antes de adicionar à base de conhecimento.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 flex overflow-hidden">
                        {/* Lado Esquerdo: Site Original */}
                        <div className="w-1/2 border-r bg-gray-50 flex flex-col">
                            <div className="p-2 bg-gray-100 border-b text-xs font-mono truncate px-4">
                                {reviewItem?.url}
                            </div>
                            <iframe
                                src={reviewItem?.url}
                                className="w-full h-full border-none"
                                title="Site Original"
                                sandbox="allow-same-origin allow-scripts" // Segurança básica
                            />
                        </div>

                        {/* Lado Direito: Markdown Gerado */}
                        <div className="w-1/2 flex flex-col bg-white">
                            <div className="p-2 bg-gray-100 border-b text-xs font-semibold px-4">
                                Resultado Extraído (Markdown)
                            </div>
                            <div className="flex-1 p-4 overflow-auto">
                                <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800">
                                    {reviewItem?.markdown_content}
                                </pre>
                            </div>
                        </div>
                    </div>

                    <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                        <Button variant="outline" onClick={() => setIsReviewOpen(false)}>
                            Cancelar
                        </Button>
                        <Button onClick={handleConfirmUpload} disabled={uploading}>
                            {uploading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Adicionando...
                                </>
                            ) : (
                                <>
                                    <UploadCloud className="h-4 w-4 mr-2" />
                                    Confirmar e Adicionar à Base
                                </>
                            )}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Modal de Feedback (Sucesso/Erro) */}
            <Dialog open={feedbackModal.isOpen} onOpenChange={(open) => setFeedbackModal(prev => ({ ...prev, isOpen: open }))}>
                <DialogContent className="sm:max-w-[425px] z-[250]">
                    <DialogHeader>
                        <DialogTitle className={feedbackModal.type === 'success' ? 'text-green-600' : 'text-red-600'}>
                            {feedbackModal.type === 'success' ? 'Sucesso' : 'Erro'}
                        </DialogTitle>
                        <DialogDescription>
                            {feedbackModal.message}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button onClick={() => setFeedbackModal(prev => ({ ...prev, isOpen: false }))}>
                            Fechar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Informações adicionais */}
            <Accordion type="single" collapsible className="border rounded-lg">
                <AccordionItem value="info" className="border-0">
                    <AccordionTrigger className="px-4">
                        ℹ️ Informações e Limitações
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-4">
                        <div className="space-y-2 text-sm text-muted-foreground">
                            <p>
                                <strong>Como funciona:</strong> O sistema detecta automaticamente se o site é
                                estático ou requer JavaScript. Agora com modo de revisão antes de adicionar à base.
                            </p>
                            <p>
                                <strong>Limitações:</strong>
                            </p>
                            <ul className="list-disc list-inside space-y-1 ml-2">
                                <li>Alguns sites podem bloquear a visualização na janela de revisão (X-Frame-Options).</li>
                                <li>Máximo de 5 URLs processadas simultaneamente</li>
                                <li>Timeout de 10s para sites estáticos, 30s para sites JavaScript</li>
                            </ul>
                        </div>
                    </AccordionContent>
                </AccordionItem>
            </Accordion>
        </div>
    );
}
