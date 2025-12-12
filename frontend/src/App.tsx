import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, Send, X, Settings, Check, Save, Copy, Eye, EyeOff, Share2, Printer, FileDown } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AgentConfig {
  name: string
  system_prompt: string
  user_prompt: string
  enabled?: boolean
  enable_web_search?: boolean
  file_search_stores?: string[]
}

interface Store {
  name: string
  display_name: string
}

interface StoreFile {
  name: string
  file_uri: string
  display_name?: string
  mime_type?: string
  size_bytes?: number
  create_time?: string
  update_time?: string
  state?: string
}

interface Config {
  model: string
  api_key: string
  root: {
    system_prompt: string
    user_prompt: string
  }
  agents: Record<string, AgentConfig>
}

function App() {
  const [isOpen, setIsOpen] = useState(false)
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Seja bem vindo ao serviço de atendimento virtual da ATI. Eu sou a TIA, precisando de ajuda? 😊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [config, setConfig] = useState<Config>({
    model: '',
    api_key: '',
    root: { system_prompt: '', user_prompt: '' },
    agents: {}
  })

  const [activeTab, setActiveTab] = useState("general")
  const [showApiKey, setShowApiKey] = useState(false)

  // Knowledge Base State
  const [stores, setStores] = useState<Store[]>([])
  const [storeFiles, setStoreFiles] = useState<StoreFile[]>([])
  const [selectedStore, setSelectedStore] = useState<string | null>(null)
  const [newStoreName, setNewStoreName] = useState("")
  const [isUploading, setIsUploading] = useState(false)

  // Feedback Modal State
  const [feedback, setFeedback] = useState<{
    open: boolean;
    title: string;
    message: string;
    type: 'success' | 'error';
  }>({ open: false, title: '', message: '', type: 'success' });

  const showFeedback = (title: string, message: string, type: 'success' | 'error') => {
    setFeedback({ open: true, title, message, type });
  };

  // Delete Confirmation Modal State
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    open: boolean;
    storeName: string | null;
  }>({ open: false, storeName: null });


  // Groups definition
  const agentGroups = {
    "Secretarias": [
      "Casa Civil",
      "Casa Militar",
      "Controladoria-Geral do Estado",
      "Corpo de Bombeiros Militar",
      "Polícia Militar",
      "Procuradoria-Geral do Estado",
      "Secretaria Executiva da Governadoria",
      "Secretaria Extraordinária de Desenvolvimento da Região Metropolitana de Palmas",
      "Secretaria Extraordinária de Participações Sociais e Políticas de Governo",
      "Secretaria Extraordinária de Representação em Brasília",
      "Secretaria da Administração",
      "Secretaria da Agricultura e Pecuária",
      "Secretaria da Cidadania e Justiça",
      "Secretaria da Comunicação",
      "Secretaria da Cultura",
      "Secretaria da Educação",
      "Secretaria da Fazenda",
      "Secretaria da Igualdade Racial",
      "Secretaria da Indústria, Comércio e Serviços",
      "Secretaria da Mulher",
      "Secretaria da Pesca e Aquicultura",
      "Secretaria da Saúde",
      "Secretaria da Segurança Pública",
      "Secretaria das Cidades, Habitação e Desenvolvimento Regional",
      "Secretaria de Parcerias e Investimentos",
      "Secretaria do Meio Ambiente e Recursos Hídricos",
      "Secretaria do Planejamento e Orçamento",
      "Secretaria do Trabalho e Desenvolvimento Social",
      "Secretaria do Turismo",
      "Secretaria dos Esportes e Juventude",
      "Secretaria dos Povos Originários e Tradicionais"
    ],
    "Autarquias": [
      "Agência Tocantinense de Regulação, Controle e Fiscalização de Serviços Públicos",
      "Agência Tocantinense de Saneamento",
      "Agência de Defesa Agropecuária",
      "Agência de Fomento",
      "Agência de Metrologia",
      "Agência de Mineração",
      "Agência de Tecnologia da Informação",
      "Agência de Transportes, Obras e Infraestrutura",
      "Companhia Imobiliária de Participações, Investimentos e Parcerias",
      "Departamento Estadual de Trânsito",
      "Fundação de Amparo à Pesquisa",
      "Instituto Natureza do Tocantins",
      "Instituto de Desenvolvimento Rural",
      "Instituto de Gestão Previdenciária",
      "Instituto de Terras do Estado do Tocantins",
      "Junta Comercial",
      "Universidade Estadual do Tocantins"
    ],
    "Sites especiais": [
      "CLUBE DE BENEFÍCIOS",
      "Carteira de identificação da pessoa autista",
      "Diário Oficial",
      "ESSA TERRA É NOSSA",
      "Observatório do Lago",
      "Observatório do Turismo",
      "PROGRAMA VALE GÁS",
      "Turismo",
      "Zoneamento Ecológico Econômico do Tocantins"
    ]
  }

  // Helper to find agent key by name
  const findAgentKeyByName = (name: string) => {
    return Object.keys(config.agents).find(key => config.agents[key].name === name)
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, isOpen])

  // PostMessage for Widget resizing
  useEffect(() => {
    const sendResize = (mode: 'fab' | 'chat' | 'full') => {
      window.parent.postMessage({ type: 'tia-resize', mode }, '*')
    }

    if (isConfigOpen) {
      sendResize('full')
    } else if (isOpen) {
      sendResize('chat')
    } else {
      sendResize('fab')
    }
  }, [isOpen, isConfigOpen])

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config')
      const data = await res.json()
      setConfig(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (isConfigOpen) {
      fetchConfig()
    }
  }, [isConfigOpen])

  const handleSaveConfig = async () => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      if (!res.ok) throw new Error('Falha ao salvar configurações')
      setIsConfigOpen(false)
      showFeedback("Sucesso", "Configurações salvas com sucesso!", "success")
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao salvar configurações: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    }
  }

  const handleQuickSave = async () => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      if (!res.ok) throw new Error('Falha ao salvar seleção')
      showFeedback("Sucesso", "Seleção salva com sucesso!", "success")
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao salvar seleção: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    }
  }

  const handleSaveAgent = async (agentKey: string) => {
    const agent = config.agents[agentKey]
    try {
      const res = await fetch(`/api/agent/${agentKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agent)
      })
      if (!res.ok) throw new Error('Falha ao salvar agente')
      showFeedback("Sucesso", "Agente salvo com sucesso!", "success")
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao salvar agente: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    }
  }

  // Knowledge Base API Helpers
  const fetchStores = async () => {
    try {
      const res = await fetch('/api/knowledge/stores')
      const data = await res.json()
      if (Array.isArray(data)) {
        setStores(data)
        await fetchConfig()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleCreateStore = async () => {
    if (!newStoreName.trim()) return
    try {
      const res = await fetch('/api/knowledge/stores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: newStoreName })
      })

      if (!res.ok) {
        const text = await res.text()
        try {
          const err = JSON.parse(text)
          showFeedback("Erro", "Erro ao criar base: " + (err.error || res.statusText), "error")
        } catch {
          showFeedback("Erro", "Erro ao criar base: " + res.statusText, "error")
        }
        return
      }

      const data = await res.json()
      if (data.name) {
        setStores([...stores, data])

        // Check if store name matches an agent name and auto-associate
        const agentKey = findAgentKeyByName(newStoreName)
        if (agentKey) {
          const agent = config.agents[agentKey]
          const currentStores = agent.file_search_stores || []
          if (!currentStores.includes(data.name)) {
            const newStores = [...currentStores, data.name]
            const updatedAgent = { ...agent, file_search_stores: newStores }

            // Update local config
            setConfig(prev => ({
              ...prev,
              agents: {
                ...prev.agents,
                [agentKey]: updatedAgent
              }
            }))

            // Persist to backend
            try {
              await fetch(`/api/agent/${agentKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedAgent)
              })
              showFeedback("Sucesso", `Base criada e associada ao agente "${newStoreName}"!`, "success")
            } catch (err) {
              console.error("Failed to auto-associate store:", err)
              showFeedback("Aviso", "Base criada, mas erro ao associar ao agente automaticamente.", "error")
            }
          } else {
            showFeedback("Sucesso", "Base criada com sucesso!", "success")
          }
        } else {
          showFeedback("Sucesso", "Base criada com sucesso! Associe-a a um agente na aba 'Agentes'.", "success")
        }

        setNewStoreName("")
      } else if (data.error) {
        showFeedback("Erro", "Erro ao criar base: " + data.error, "error")
      }
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro de conexão ao criar base", "error")
    }
  }

  const confirmDeleteStore = async () => {
    const name = deleteConfirmation.storeName;
    if (!name) return;
    setDeleteConfirmation({ open: false, storeName: null }); // Close modal

    try {
      const res = await fetch(`/api/knowledge/stores/${name}`, { method: 'DELETE' })

      if (!res.ok) {
        let errorMsg = res.statusText
        try {
          const errData = await res.json()
          if (errData.error) errorMsg = errData.error
        } catch { }
        showFeedback("Erro", "Erro ao excluir base: " + errorMsg, "error")
        return
      }

      let successMessage = "Base de conhecimento excluída com sucesso!"
      try {
        const data = await res.json()
        if (data.error) {
          showFeedback("Erro", "Erro ao excluir base: " + data.error, "error")
          return
        }
        if (data.message) {
          successMessage = data.message
        }
      } catch (e) {
        console.warn("Response was not JSON", e)
      }

      setStores(stores.filter(s => s.name !== name))
      if (selectedStore === name) {
        setSelectedStore(null)
        setStoreFiles([])
      }
      showFeedback("Sucesso", successMessage, "success")

    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro de conexão ao excluir base", "error")
    }
  }

  const handleDeleteStore = (name: string) => {
    setDeleteConfirmation({ open: true, storeName: name });
  }

  const fetchStoreFiles = async (storeName: string) => {
    setSelectedStore(storeName)
    try {
      const res = await fetch(`/api/knowledge/stores/${storeName}/files`)
      const data = await res.json()
      if (Array.isArray(data)) {
        setStoreFiles(data)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const [fileToDelete, setFileToDelete] = useState<StoreFile | null>(null);

  const handleDeleteFile = (fileName: string) => {
    const file = storeFiles.find(f => f.name === fileName);
    if (file) setFileToDelete(file);
  }

  const confirmDeleteFile = async () => {
    if (!selectedStore || !fileToDelete) return
    const fileName = fileToDelete.name
    setFileToDelete(null) // Close modal

    // Optimistic update
    const previousFiles = [...storeFiles]
    setStoreFiles(storeFiles.filter(f => f.name !== fileName))

    try {
      const res = await fetch(`/api/knowledge/stores/${selectedStore}/files/${fileName}`, {
        method: 'DELETE'
      })

      const data = await res.json()

      if (!res.ok || data.error) {
        throw new Error(data.error || "Falha ao excluir arquivo")
      }

      showFeedback("Sucesso", "Arquivo excluído com sucesso!", "success")
    } catch (e) {
      console.error(e)
      setStoreFiles(previousFiles) // Revert on error
      showFeedback("Erro", "Erro ao excluir arquivo: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    }
  }

  const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0] || !selectedStore) return
    const file = e.target.files[0]
    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('store_name', selectedStore)

    try {
      const res = await fetch('/api/knowledge/upload', {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (data.status === 'uploaded') {
        // Refresh files
        await fetchStoreFiles(selectedStore)
        showFeedback("Sucesso", "Arquivo enviado com sucesso!", "success")
      } else {
        showFeedback("Erro", "Erro ao enviar arquivo: " + (data.error || "Desconhecido"), "error")
      }
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao enviar arquivo", "error")
    } finally {
      setIsUploading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'knowledge' || activeTab === 'agents') {
      fetchStores()
    }
  }, [activeTab])

  const handleShare = async (text: string) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Atendimento Virtual - Governo do Tocantins',
          text: text,
        });
      } catch (err) {
        console.error('Error sharing:', err);
      }
    } else {
      navigator.clipboard.writeText(text);
      // Fallback for desktop/unsupported browsers
    }
  };

  const handlePrint = (contentId: string) => {
    const contentElement = document.getElementById(contentId);
    if (contentElement) {
      const printWindow = window.open('', '_blank');
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>Atendimento Virtual - Governo do Tocantins</title>
              <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; line-height: 1.6; color: #333; }
                img { max-width: 100%; }
                a { color: #2563eb; text-decoration: underline; }
                p { margin-bottom: 1em; }
                strong { font-weight: bold; }
                ul, ol { margin-left: 20px; margin-bottom: 1em; }
                li { margin-bottom: 0.5em; }
                h1, h2, h3 { color: #1e3a8a; margin-top: 1.5em; margin-bottom: 0.5em; }
                blockquote { border-left: 4px solid #ddd; padding-left: 10px; color: #666; }
                pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
                code { background: #f5f5f5; padding: 2px 4px; border-radius: 4px; }
                @media print {
                   body { padding: 0; }
                   .no-print { display: none; }
                }
              </style>
            </head>
            <body>
              <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; display: flex; align-items: center; gap: 15px;">
                <img src="/avatar.png" style="height: 50px; width: 50px; object-fit: cover; border-radius: 50%;" />
                <div>
                  <h2 style="margin: 0; font-size: 18px;">Atendimento Virtual</h2>
                  <p style="margin: 0; font-size: 14px; color: #666;">Governo do Tocantins</p>
                </div>
              </div>
              <div class="content">
                ${contentElement.innerHTML}
              </div>
              <div style="margin-top: 40px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 10px;">
                Gerado em ${new Date().toLocaleDateString()} às ${new Date().toLocaleTimeString()}
              </div>
              <script>
                window.onload = function() { 
                  setTimeout(function() {
                    window.print(); 
                    // window.close(); // Optional: keep open if user wants to check
                  }, 500);
                }
              </script>
            </body>
          </html>
        `);
        printWindow.document.close();
      }
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return

    const userMessage = text
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const formData = new FormData()
      formData.append('message', userMessage)
      formData.append('target', 'auto')

      const response = await fetch('/api/chat', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Network response was not ok')
      }

      const data = await response.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply || 'Sem resposta.' }])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Desculpe, ocorreu um erro ao processar sua mensagem.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleSendMessage(input)
  }

  // Assets placeholders
  const avatarUrl = "/avatar_fundo_transparente.png"
  const logoUrl = "https://placeholder.co/100x40?text=ATI+TO&bg=ffffff&fg=000000" // ATI Logo placeholder

  // Helpers
  const formatBytes = (bytes?: number | null) => {
    if (bytes === undefined || bytes === null) return '?'
    const v = Number(bytes)
    if (!isFinite(v) || Number.isNaN(v)) return '?'
    if (v <= 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(v) / Math.log(k))
    const idx = Math.max(0, Math.min(sizes.length - 1, i))
    const value = v / Math.pow(k, idx)
    if (!isFinite(value) || Number.isNaN(value)) return '?'
    return `${value.toFixed(2)} ${sizes[idx]}`
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('pt-BR')
  }

  const formatFileType = (file: StoreFile) => {
    const fileName = file.display_name || file.name || ''

    // First try to use MIME type if it's specific
    if (file.mime_type && file.mime_type !== 'application/octet-stream') {
      if (file.mime_type === 'application/pdf') return 'PDF'
      if (file.mime_type.startsWith('image/')) return 'Imagem'
      if (file.mime_type.startsWith('text/')) return 'Texto'
      return file.mime_type.split('/').pop()?.toUpperCase() || file.mime_type
    }

    // Fallback to extension
    const extension = fileName.split('.').pop()
    if (extension && extension !== fileName) {
      return extension.toUpperCase()
    }

    return 'Arquivo'
  }

  return (
    <div className="fixed inset-0 pointer-events-none flex items-end justify-end p-4">

      {/* Configuration Dialog */}
      <Dialog open={isConfigOpen} onOpenChange={setIsConfigOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" className="fixed top-4 right-4 bg-white shadow-sm gap-2 pointer-events-auto">
            <Settings className="h-4 w-4" /> Configurações
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto pointer-events-auto">
          <DialogHeader>
            <DialogTitle>Configurações do Sistema</DialogTitle>
            <DialogDescription>
              Ajuste o modelo, chaves de API, prompts dos agentes, integrações e configurações de base do conhecimento (RAG).
            </DialogDescription>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general">Geral</TabsTrigger>
              <TabsTrigger value="agents">Agentes</TabsTrigger>
              <TabsTrigger value="knowledge">Bases de Conhecimento</TabsTrigger>
              <TabsTrigger value="integration">Integração</TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="model">Modelo LLM</Label>
                <Input
                  id="model"
                  value={config.model}
                  onChange={(e) => setConfig({ ...config, model: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="apikey">Google API Key</Label>
                <div className="relative">
                  <Input
                    id="apikey"
                    type={showApiKey ? "text" : "password"}
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowApiKey(!showApiKey)}
                  >
                    {showApiKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="sr-only">Toggle API Key visibility</span>
                  </Button>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="root_sys">Prompt do Sistema (Root/Orquestrador)</Label>
                <Textarea
                  id="root_sys"
                  rows={5}
                  value={config.root?.system_prompt || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    root: { ...config.root, system_prompt: e.target.value }
                  })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="root_user">Prompt do Usuário (Root/Orquestrador)</Label>
                <Textarea
                  id="root_user"
                  rows={3}
                  value={config.root?.user_prompt || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    root: { ...config.root, user_prompt: e.target.value }
                  })}
                />
              </div>
            </TabsContent>

            <TabsContent value="agents" className="space-y-4 py-4">
              <div className="text-sm text-muted-foreground mb-2">
                Configure os prompts específicos para cada agente especialista.
              </div>

              <div className="flex items-center justify-between mb-2 p-2 bg-slate-50 rounded-md border">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="toggle-all"
                    checked={Object.keys(config.agents).length > 0 && Object.values(config.agents).every(a => a.enabled !== false)}
                    onCheckedChange={(checked) => {
                      const newAgents = { ...config.agents }
                      Object.keys(newAgents).forEach(key => {
                        newAgents[key] = { ...newAgents[key], enabled: !!checked }
                      })
                      setConfig({ ...config, agents: newAgents })
                    }}
                  />
                  <Label htmlFor="toggle-all" className="cursor-pointer font-medium">
                    Habilitar/Desabilitar Todos os Agentes
                  </Label>
                </div>
                <Button size="sm" variant="outline" onClick={handleQuickSave} title="Salvar seleção de todos os agentes">
                  <Save className="h-4 w-4 mr-2" /> Salvar Seleção
                </Button>
              </div>

              <div className="h-[400px] overflow-y-auto border rounded-md p-4">
                <Accordion type="single" collapsible className="w-full">
                  {Object.entries(agentGroups).map(([groupName, agentNames]) => (
                    <div key={groupName} className="mb-6 last:mb-0">
                      <h3 className="font-bold text-lg mb-2 text-gray-700 px-1 border-b pb-1">{groupName}</h3>
                      {agentNames.map((agentName) => {
                        const agentKey = findAgentKeyByName(agentName)
                        if (!agentKey) return null

                        return (
                          <AccordionItem key={agentKey} value={agentKey}>
                            <div className="flex items-center px-2 hover:bg-slate-50">
                              <Checkbox
                                id={`chk-${agentKey}`}
                                checked={config.agents[agentKey].enabled !== false}
                                onCheckedChange={(checked) => {
                                  setConfig({
                                    ...config,
                                    agents: {
                                      ...config.agents,
                                      [agentKey]: {
                                        ...config.agents[agentKey],
                                        enabled: !!checked
                                      }
                                    }
                                  })
                                }}
                                className="mr-2"
                              />
                              <AccordionTrigger className="text-left flex-1 py-3 pl-2">
                                {config.agents[agentKey].name || agentKey}
                                {config.agents[agentKey].enabled === false && (
                                  <span className="ml-2 text-xs text-red-500 font-normal">(Desativado)</span>
                                )}
                              </AccordionTrigger>
                            </div>
                            <AccordionContent className="space-y-4 p-2 pl-10 border-t">
                              <div className="p-3 bg-blue-50 rounded-md border border-blue-100">
                                <h4 className="font-semibold text-sm text-blue-800 mb-2">Capacidades de Pesquisa</h4>
                                <div className="flex items-center space-x-2 mb-3">
                                  <Checkbox
                                    id={`web-${agentKey}`}
                                    checked={config.agents[agentKey].enable_web_search !== false} // Default true
                                    onCheckedChange={(checked) => {
                                      const isChecked = !!checked;
                                      setConfig({
                                        ...config,
                                        agents: {
                                          ...config.agents,
                                          [agentKey]: {
                                            ...config.agents[agentKey],
                                            enable_web_search: isChecked,
                                            // User requested both can be on. Do not clear file_search_stores.
                                          }
                                        }
                                      })
                                    }}
                                  />
                                  <Label htmlFor={`web-${agentKey}`} className="cursor-pointer">
                                    Habilitar Pesquisa na Web (Google Search)
                                  </Label>
                                </div>

                                <div className="space-y-2">
                                  <Label className="text-xs font-semibold uppercase text-gray-500">Bases de Conhecimento (File Search)</Label>
                                  {stores.length === 0 && (!config.agents[agentKey].file_search_stores || config.agents[agentKey].file_search_stores.length === 0) ? (
                                    <p className="text-xs text-gray-500 italic">Nenhuma base de conhecimento criada no sistema. Vá para a aba "Bases de Conhecimento" para criar uma.</p>
                                  ) : (
                                    <div className="grid grid-cols-1 gap-2 max-h-32 overflow-y-auto p-2 border rounded bg-white">
                                      {(() => {
                                        const filteredStores = stores.filter(store => {
                                          const normalize = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
                                          const nStore = normalize(store.display_name || store.name);
                                          const nAgent = normalize(config.agents[agentKey].name || agentKey);
                                          return nStore === nAgent;
                                        });

                                        if (filteredStores.length === 0) {
                                          return <p className="text-xs text-gray-500 italic p-2">Para este agente não existe ainda base de conhecimento criada.</p>;
                                        }

                                        return filteredStores.map(store => (
                                          <div key={store.name} className="flex items-center space-x-2">
                                            <Checkbox
                                              id={`store-${agentKey}-${store.name}`}
                                              checked={(() => {
                                                const normalize = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
                                                const nStore = normalize(store.display_name || store.name);
                                                const nAgent = normalize(config.agents[agentKey].name || agentKey);
                                                const isLinked = (config.agents[agentKey].file_search_stores || []).includes(store.name);
                                                return isLinked && nStore === nAgent;
                                              })()}
                                              onCheckedChange={(checked) => {
                                                const currentStores = config.agents[agentKey].file_search_stores || []
                                                let newStores
                                                if (checked) {
                                                  const normalize = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
                                                  const nStore = normalize(store.display_name || store.name);
                                                  const nAgent = normalize(config.agents[agentKey].name || agentKey);
                                                  if (nStore !== nAgent) {
                                                    showFeedback("Aviso", "Esta base não pertence a este agente.", "error")
                                                    return
                                                  }
                                                  newStores = [...currentStores, store.name]
                                                } else {
                                                  newStores = currentStores.filter(s => s !== store.name)
                                                }

                                                setConfig({
                                                  ...config,
                                                  agents: {
                                                    ...config.agents,
                                                    [agentKey]: {
                                                      ...config.agents[agentKey],
                                                      file_search_stores: newStores
                                                      // User requested both can be on. Do not disable web search.
                                                    }
                                                  }
                                                })
                                              }}
                                            />
                                            <Label htmlFor={`store-${agentKey}-${store.name}`} className="text-sm cursor-pointer">
                                              {store.display_name}
                                            </Label>
                                          </div>
                                        ));
                                      })()}
                                      {(config.agents[agentKey].file_search_stores || []).filter(sName => !stores.find(s => s.name === sName)).map(missingStoreName => (
                                        <div key={missingStoreName} className="flex items-center space-x-2 bg-red-50 p-1 rounded">
                                          <Checkbox
                                            id={`store-${agentKey}-${missingStoreName}`}
                                            checked={true}
                                            onCheckedChange={(checked) => {
                                              if (!checked) {
                                                const currentStores = config.agents[agentKey].file_search_stores || []
                                                const newStores = currentStores.filter(s => s !== missingStoreName)
                                                setConfig({
                                                  ...config,
                                                  agents: {
                                                    ...config.agents,
                                                    [agentKey]: {
                                                      ...config.agents[agentKey],
                                                      file_search_stores: newStores
                                                    }
                                                  }
                                                })
                                              }
                                            }}
                                          />
                                          <Label htmlFor={`store-${agentKey}-${missingStoreName}`} className="text-sm cursor-pointer text-red-600" title="Esta base não foi encontrada no servidor. Pode ter sido excluída.">
                                            ⚠️ {missingStoreName.split('/').pop()} (Não encontrada)
                                          </Label>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div className="grid gap-2">
                                <Label htmlFor={`sys-${agentKey}`}>Prompt do Sistema</Label>
                                <Textarea
                                  id={`sys-${agentKey}`}
                                  rows={6}
                                  value={config.agents[agentKey].system_prompt || ''}
                                  onChange={(e) => {
                                    setConfig({
                                      ...config,
                                      agents: {
                                        ...config.agents,
                                        [agentKey]: {
                                          ...config.agents[agentKey],
                                          system_prompt: e.target.value
                                        }
                                      }
                                    })
                                  }}
                                />
                              </div>
                              <div className="grid gap-2">
                                <Label htmlFor={`usr-${agentKey}`}>Prompt do Usuário</Label>
                                <Textarea
                                  id={`usr-${agentKey}`}
                                  rows={3}
                                  value={config.agents[agentKey].user_prompt || ''}
                                  onChange={(e) => {
                                    setConfig({
                                      ...config,
                                      agents: {
                                        ...config.agents,
                                        [agentKey]: {
                                          ...config.agents[agentKey],
                                          user_prompt: e.target.value
                                        }
                                      }
                                    })
                                  }}
                                />
                              </div>
                              <div className="flex justify-end pt-2">
                                <Button size="sm" onClick={() => handleSaveAgent(agentKey)} className="gap-2">
                                  <Save className="h-4 w-4" /> Salvar Agente
                                </Button>
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        )
                      })}
                    </div>
                  ))}
                </Accordion>
              </div>
            </TabsContent>
            <TabsContent value="knowledge" className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4 h-[500px]">
                {/* Left Column: Stores List */}
                <Card>
                  <CardContent className="p-4 h-full flex flex-col">
                    <h3 className="font-bold text-lg mb-4">Bases de Conhecimento (RAG)</h3>

                    <div className="flex space-x-2 mb-4">
                      <Input
                        placeholder="Nome da nova base ou escolha um agente..."
                        value={newStoreName}
                        onChange={(e) => setNewStoreName(e.target.value)}
                        list="agents-list"
                      />
                      <datalist id="agents-list">
                        {Object.values(config.agents).map((agent, idx) => (
                          <option key={`${agent.name}-${idx}`} value={agent.name} />
                        ))}
                      </datalist>
                      <Button onClick={handleCreateStore} disabled={!newStoreName.trim()}>
                        Criar
                      </Button>
                    </div>

                    <div className="flex-1 overflow-y-auto border rounded-md">
                      {stores.length === 0 ? (
                        <div className="p-4 text-center text-gray-500">Nenhuma base encontrada.</div>
                      ) : (
                        stores.map(store => (
                          <div
                            key={store.name}
                            className={`p-3 border-b cursor-pointer flex justify-between items-center hover:bg-slate-50 ${selectedStore === store.name ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}`}
                            onClick={() => fetchStoreFiles(store.name)}
                          >
                            <span className="font-medium truncate" title={store.name}>{store.display_name}</span>
                            <Button variant="ghost" size="icon" className="h-6 w-6 text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteStore(store.name); }}>
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Right Column: Files List */}
                <Card>
                  <CardContent className="p-4 h-full flex flex-col">
                    <h3 className="font-bold text-lg mb-4">
                      Arquivos {selectedStore ? `em "${stores.find(s => s.name === selectedStore)?.display_name}"` : ''}
                    </h3>

                    {!selectedStore ? (
                      <div className="flex-1 flex items-center justify-center text-gray-400">
                        Selecione uma base à esquerda para gerenciar arquivos.
                      </div>
                    ) : (
                      <>
                        <div className="mb-4">
                          <Label htmlFor="file-upload" className="cursor-pointer block">
                            <div className={`border-2 border-dashed rounded-md p-4 text-center transition-colors ${isUploading ? 'bg-gray-100' : 'hover:bg-blue-50 border-blue-200'}`}>
                              {isUploading ? (
                                <span className="flex items-center justify-center text-blue-600"><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Enviando...</span>
                              ) : (
                                <span className="text-blue-600 font-medium">+ Upload de Arquivo</span>
                              )}
                            </div>
                            <Input id="file-upload" type="file" className="hidden" onChange={handleUploadFile} disabled={isUploading} />
                          </Label>
                        </div>

                        <div className="flex-1 overflow-y-auto border rounded-md">
                          {storeFiles.length === 0 ? (
                            <div className="p-4 text-center text-gray-500">Nenhum arquivo nesta base.</div>
                          ) : (
                            storeFiles.map((file, idx) => (
                              <div key={idx} className="p-3 border-b text-sm flex flex-col gap-1 hover:bg-slate-50 transition-colors group relative">
                                <div className="flex justify-between items-center pr-8">
                                  <div className="truncate flex-1 mr-2 font-medium text-slate-900" title={file.file_uri || file.name}>
                                    {file.display_name || (file.name ? file.name.split('/').pop() : 'Sem nome')}
                                  </div>
                                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${file.state && file.state.includes('ACTIVE') ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                    {file.state && file.state.includes('ACTIVE') ? 'Ativo' : (file.state ? 'Processando' : 'Desconhecido')}
                                  </span>
                                </div>
                                <div className="flex justify-between items-center text-xs text-slate-600 font-medium">
                                  <span>{formatBytes(file.size_bytes)} • {formatFileType(file)}</span>
                                  <span>{formatDate(file.create_time)}</span>
                                </div>
                                <div className="text-[10px] text-slate-500 font-mono truncate select-all" title={file.name}>
                                  ID: {file.name.split('/').pop()}
                                </div>

                                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 text-red-400 hover:text-red-600 hover:bg-red-50"
                                    onClick={(e) => { e.stopPropagation(); handleDeleteFile(file.name); }}
                                    title="Excluir Arquivo"
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="integration" className="space-y-4 py-4">
              <div className="text-sm text-muted-foreground mb-4">
                Copie o código abaixo e cole no HTML do seu site para adicionar o chat TIA.
                Certifique-se de substituir o domínio se necessário.
              </div>

              <div className="relative">
                <Textarea
                  className="font-mono text-xs bg-slate-50 min-h-[300px]"
                  readOnly
                  value={`<!-- Início do Widget TIA -->
<div id="tia-widget-container"></div>
<script>
  (function() {
    var iframe = document.createElement('iframe');
    iframe.src = "${window.location.origin}"; // Altere para a URL de produção se necessário
    iframe.style.position = "fixed";
    iframe.style.bottom = "0";
    iframe.style.right = "0";
    iframe.style.border = "none";
    iframe.style.zIndex = "9999";
    // Tamanho inicial apenas para o botão (FAB)
    iframe.style.width = "120px";
    iframe.style.height = "120px";
    iframe.allow = "microphone";
    
    document.body.appendChild(iframe);

    // Escuta mensagens do chat para redimensionar o iframe
    window.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'tia-resize') {
        if (e.data.mode === 'full') {
          iframe.style.width = "100%";
          iframe.style.height = "100%";
        } else if (e.data.mode === 'chat') {
          iframe.style.width = "450px";
          iframe.style.height = "650px";
        } else {
          iframe.style.width = "120px";
          iframe.style.height = "120px";
        }
      }
    });
  })();
</script>
<!-- Fim do Widget TIA -->`}
                />
                <Button
                  size="icon"
                  variant="outline"
                  className="absolute top-2 right-2 h-8 w-8"
                  onClick={() => {
                    navigator.clipboard.writeText(`<!-- Início do Widget TIA -->
<div id="tia-widget-container"></div>
<script>
  (function() {
    var iframe = document.createElement('iframe');
    iframe.src = "${window.location.origin}";
    iframe.style.position = "fixed";
    iframe.style.bottom = "0";
    iframe.style.right = "0";
    iframe.style.border = "none";
    iframe.style.zIndex = "9999";
    iframe.style.width = "120px";
    iframe.style.height = "120px";
    iframe.allow = "microphone";
    document.body.appendChild(iframe);

    window.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'tia-resize') {
        if (e.data.mode === 'full') {
          iframe.style.width = "100%";
          iframe.style.height = "100%";
        } else if (e.data.mode === 'chat') {
          iframe.style.width = "450px";
          iframe.style.height = "650px";
        } else {
          iframe.style.width = "120px";
          iframe.style.height = "120px";
        }
      }
    });
  })();
</script>
<!-- Fim do Widget TIA -->`)
                  }}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>

              <div className="rounded-md bg-blue-50 p-4 text-sm text-blue-800 border border-blue-200 mt-4">
                <strong>Como funciona:</strong> O script cria um iframe que se redimensiona automaticamente.
                Inicialmente ele ocupa apenas o canto para mostrar o botão. Ao abrir o chat, ele expande.
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            {activeTab === 'general' ? (
              <Button onClick={handleSaveConfig}>Salvar Alterações</Button>
            ) : (
              <Button variant="outline" onClick={() => setIsConfigOpen(false)}>Fechar</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog >

      {/* Floating Action Button (FAB) */}
      {
        !isOpen && (
          <Button
            className="fixed bottom-6 right-6 h-20 w-20 rounded-full shadow-xl p-0 overflow-hidden border-2 border-white transition-transform hover:scale-105 pointer-events-auto"
            onClick={() => setIsOpen(true)}
          >
            <img src={avatarUrl} alt="TIA Avatar" className="h-full w-full object-cover" />
          </Button>
        )
      }

      {/* Chat Widget Window */}
      {
        isOpen && (
          <Card className="fixed bottom-6 right-6 w-[380px] h-[600px] flex flex-col shadow-2xl rounded-xl overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-300 border-0 ring-1 ring-black/10 z-50 pointer-events-auto">

            {/* Header */}
            <div className="relative z-20 shadow-sm">
              <img src="/barratia.png" alt="Header" className="w-full h-auto object-cover" />
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 h-8 w-8 bg-black/20 text-white hover:bg-black/40 rounded-full backdrop-blur-sm"
                onClick={() => setIsOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Chat Body */}
            <CardContent className="flex-1 overflow-y-auto p-0 bg-[#f0f2f5] flex flex-col">

              {/* Banner Section Removed (Moved to Header) */}

              {/* Messages Area */}
              <div className="flex-1 px-4 space-y-4 pb-4 pt-6">

                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="mr-2 flex-shrink-0 self-end mb-1">
                        <img src={avatarUrl} className="h-6 w-6 rounded-full" alt="Bot" />
                      </div>
                    )}
                    <div
                      className={`max-w-[85%] p-3 text-sm shadow-sm ${msg.role === 'user'
                        ? 'bg-[#dcf8c6] text-gray-800 rounded-2xl rounded-tr-none'
                        : 'bg-white text-gray-800 rounded-2xl rounded-tl-none border border-gray-100 whitespace-pre-wrap'
                        }`}
                    >
                      {msg.role === 'assistant' ? (
                        <>
                          <div id={`msg-content-${index}`}>
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                h1: ({ node, ...props }) => <h1 {...props} className="text-lg font-bold text-slate-900 mb-3 mt-4 border-b border-slate-200 pb-2" />,
                                h2: ({ node, ...props }) => <h2 {...props} className="text-base font-semibold text-slate-800 mb-2 mt-3" />,
                                h3: ({ node, ...props }) => <h3 {...props} className="text-sm font-semibold text-slate-700 mb-1 mt-2" />,
                                p: ({ node, ...props }) => <p {...props} className="mb-3 leading-relaxed text-slate-700" />,
                                ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-5 mb-3 space-y-1 text-slate-700" />,
                                ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-5 mb-3 space-y-1 text-slate-700" />,
                                li: ({ node, ...props }) => <li {...props} className="pl-1" />,
                                a: ({ node, ...props }) => <a {...props} className="text-blue-600 hover:text-blue-800 font-medium hover:underline transition-colors break-all" target="_blank" rel="noopener noreferrer" />,
                                blockquote: ({ node, ...props }) => <blockquote {...props} className="border-l-4 border-blue-200 pl-4 py-1 my-3 bg-slate-50 text-slate-600 italic rounded-r" />,
                                code: ({ node, className, children, ...props }: any) => {
                                  const match = /language-(\w+)/.exec(className || '')
                                  return match ? (
                                    <code {...props} className={`bg-transparent text-inherit font-mono text-xs ${className}`}>{children}</code>
                                  ) : (
                                    <code {...props} className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-xs font-mono border border-slate-200">{children}</code>
                                  )
                                },
                                pre: ({ node, ...props }) => <div className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-white my-3 shadow-sm"><pre {...props} className="m-0" /></div>,
                                table: ({ node, ...props }) => <div className="overflow-x-auto my-4 rounded-lg border border-slate-200 shadow-sm"><table {...props} className="w-full text-sm text-left text-slate-700" /></div>,
                                thead: ({ node, ...props }) => <thead {...props} className="bg-slate-50 text-slate-700 font-semibold uppercase text-xs" />,
                                th: ({ node, ...props }) => <th {...props} className="px-4 py-3 border-b border-slate-200 whitespace-nowrap" />,
                                td: ({ node, ...props }) => <td {...props} className="px-4 py-3 border-b border-slate-100" />,
                                hr: ({ node, ...props }) => <hr {...props} className="my-6 border-slate-200" />,
                                strong: ({ node, ...props }) => <strong {...props} className="font-semibold text-slate-900" />,
                                img: ({ node, ...props }) => <img {...props} className="rounded-lg max-w-full h-auto my-3 border border-slate-200 shadow-sm" alt={props.alt || 'Imagem'} />,
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                          {index > 0 && (
                            <div className="flex gap-1 mt-2 pt-2 border-t border-gray-100 justify-end no-print">
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-gray-400 hover:text-gray-600" onClick={() => handleShare(msg.content)} title="Compartilhar">
                                <Share2 className="h-3 w-3" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-gray-400 hover:text-gray-600" onClick={() => handlePrint(`msg-content-${index}`)} title="Imprimir">
                                <Printer className="h-3 w-3" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-gray-400 hover:text-gray-600" onClick={() => handlePrint(`msg-content-${index}`)} title="Salvar PDF">
                                <FileDown className="h-3 w-3" />
                              </Button>
                            </div>
                          )}
                        </>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="mr-2 flex-shrink-0 self-end mb-1">
                      <img src={avatarUrl} className="h-6 w-6 rounded-full" alt="Bot" />
                    </div>
                    <div className="bg-white p-3 rounded-2xl rounded-tl-none border border-gray-100 shadow-sm">
                      <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
                    </div>
                  </div>
                )}

                {/* Suggestion Button (only shown when only welcome message exists and not loading) */}
                {messages.length === 1 && !isLoading && (
                  <div className="flex justify-start ml-8">
                    <Button
                      variant="outline"
                      className="rounded-full text-xs h-8 bg-white border-gray-200 hover:bg-gray-50 text-gray-600 shadow-sm"
                      onClick={() => handleSendMessage('Veja o que eu faço')}
                    >
                      Veja o que eu faço
                    </Button>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </CardContent>

            {/* Footer Input */}
            <div className="bg-white p-2 border-t">
              <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-gray-50 rounded-full px-4 py-2 border border-gray-200 focus-within:ring-1 focus-within:ring-blue-300 transition-all">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Pergunte algo..."
                  disabled={isLoading}
                  className="flex-1 border-0 bg-transparent focus-visible:ring-0 shadow-none h-auto p-0 placeholder:text-gray-400 text-sm"
                />
                <Button
                  type="submit"
                  disabled={isLoading || !input.trim()}
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-blue-600 hover:bg-blue-100 rounded-full shrink-0"
                >
                  <Send className="h-4 w-4" />
                  <span className="sr-only">Enviar</span>
                </Button>
              </form>
              <div className="text-center mt-1">
                <span className="text-[10px] text-gray-400">Desenvolvido por ATI Tocantins</span>
              </div>
            </div>
          </Card>
        )
      }

      {/* Feedback Modal */}
      <Dialog open={feedback.open} onOpenChange={(open) => setFeedback(prev => ({ ...prev, open }))}>
        <DialogContent className="sm:max-w-[425px] pointer-events-auto">
          <DialogHeader>
            <DialogTitle className={feedback.type === 'error' ? "text-red-600" : "text-green-600"}>
              {feedback.title}
            </DialogTitle>
            <DialogDescription>
              {feedback.message}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setFeedback(prev => ({ ...prev, open: false }))}>OK</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteConfirmation.open} onOpenChange={(open) => setDeleteConfirmation(prev => ({ ...prev, open }))}>
        <DialogContent className="sm:max-w-[425px] pointer-events-auto">
          <DialogHeader>
            <DialogTitle>Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir esta base de conhecimento?
              Esta ação não pode ser desfeita e removerá todos os arquivos associados.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmation(prev => ({ ...prev, open: false }))}>Cancelar</Button>
            <Button variant="destructive" onClick={confirmDeleteStore}>Excluir</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!fileToDelete} onOpenChange={(open) => !open && setFileToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir o arquivo <strong>{fileToDelete?.display_name || fileToDelete?.name.split('/').pop()}</strong>?
              <br />
              Essa ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFileToDelete(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={confirmDeleteFile}>Excluir</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div >
  )
}

export default App
