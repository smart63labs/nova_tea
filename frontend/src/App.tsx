import { useState, useRef, useEffect } from 'react'
import type { ComponentProps } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Loader2, Send, X, Settings, Save, Copy, Eye, EyeOff, Share2, Printer, FileDown, Upload, ChevronLeft, ChevronRight, Database, Search as SearchIcon, Info } from "lucide-react"

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

type MarkdownComponentProps<T extends keyof JSX.IntrinsicElements> = ComponentProps<T> & { node?: unknown }

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AgentConfig {
  name: string
  system_prompt: string
  user_prompt: string
  enabled?: boolean
  enable_web_search?: boolean // Legado
  file_search_stores?: string[] // Legado
  gemini_enable_web?: boolean
  gemini_file_search_stores?: string[]
  others_enable_web?: boolean
  others_file_search_stores?: string[]
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

interface ModelItem {
  id: string
  name: string
  type: string
  description: string
  enabled: boolean
  endpoint?: string
  api_key?: string
  api_base?: string
}

interface ModelsConfig {
  active_model_id: string
  models: ModelItem[]
}

import { DoclingUploadModal } from './components/DoclingUploadModal'
import { useDoclingProcessing } from './hooks/useDoclingProcessing'
import { ScrapingTab } from './components/ScrapingTab'
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"



const isGeminiModel = (modelName: string) => {
  return modelName && (modelName.toLowerCase().startsWith('gemini') || modelName.includes('google'));
};

function App() {

  const [isOpen, setIsOpen] = useState(false)
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Seja bem vindo ao serviço de atendimento virtual da ATI. Eu sou a TIA, precisando de ajuda? 😊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const renderStoreSelection = (agentKey: string, type: 'gemini' | 'others') => {
    const isGemini = type === 'gemini';
    const field = isGemini ? 'gemini_file_search_stores' : 'others_file_search_stores';
    const legacyField = 'file_search_stores';

    // Get current stores for this type, fallback to legacy if new field is undefined
    const selectedStores = config.agents[agentKey][field] || (isGemini ? (config.agents[agentKey][legacyField] || []) : []);

    const allAssociatedStores = new Set<string>();
    Object.entries(config.agents).forEach(([key, agent]) => {
      if (key !== agentKey) {
        // Coleta TODAS as bases vinculadas a outros agentes
        [
          ...(agent.gemini_file_search_stores || []),
          ...(agent.others_file_search_stores || []),
          ...(agent.file_search_stores || [])
        ].forEach(s => {
          if (s) allAssociatedStores.add(s);
        });
      }
    });

    const filteredStores = stores.filter(store => {
      const myAgent = config.agents[agentKey];
      if (!myAgent) return false;

      // 1. Minhas bases (ja vinculadas por ID)
      const myIds = [
        ...(myAgent.gemini_file_search_stores || []),
        ...(myAgent.others_file_search_stores || []),
        ...(myAgent.file_search_stores || [])
      ];
      const isMyStoreById = myIds.includes(store.name);

      // 2. Fallback: Base tem o nome EXATO do meu agente?
      const isMyStoreByName = store.display_name === myAgent.name;

      if (isMyStoreById || isMyStoreByName) return true;

      // 3. Verificação de Ocupação: Alguém mais tem essa base (por ID)?
      if (allAssociatedStores.has(store.name)) return false;

      // 4. Fallback de Ocupação: Algum OUTRO agente tem o nome EXATO desta base?
      const agentWithStoreNameExists = Object.values(config.agents).some(a =>
        a.name === store.display_name && a.name !== myAgent.name
      );
      if (agentWithStoreNameExists) return false;

      // Se chegamos aqui e a base não tem dono, mostramos para permitir associação
      return true;
    });

    if (filteredStores.length === 0 && selectedStores.length === 0) {
      return <p className="text-[10px] text-gray-500 italic p-1">Nenhuma base disponível.</p>;
    }

    return (
      <>
        {filteredStores.map(store => (
          <div key={store.name} className="flex items-center space-x-2">
            <Checkbox
              id={`store-${type}-${agentKey}-${store.name}`}
              checked={selectedStores.includes(store.name)}
              onCheckedChange={(checked) => {
                const currentStores = selectedStores;
                let newStores;
                if (checked) {
                  newStores = [...currentStores, store.name];
                } else {
                  newStores = currentStores.filter(s => s !== store.name);
                }

                setConfig({
                  ...config,
                  agents: {
                    ...config.agents,
                    [agentKey]: {
                      ...config.agents[agentKey],
                      [field]: newStores
                    }
                  }
                });
              }}
            />
            <Label htmlFor={`store-${type}-${agentKey}-${store.name}`} className="text-xs cursor-pointer truncate" title={store.display_name}>
              {store.display_name}
            </Label>
          </div>
        ))}
        {selectedStores.filter(sName => !stores.find(s => s.name === sName)).map(missingStoreName => (
          <div key={missingStoreName} className="flex items-center space-x-2 bg-red-50 p-1 rounded">
            <Checkbox
              id={`store-missing-${type}-${agentKey}-${missingStoreName}`}
              checked={true}
              onCheckedChange={(checked) => {
                if (!checked) {
                  const newStores = selectedStores.filter(s => s !== missingStoreName);
                  setConfig({
                    ...config,
                    agents: {
                      ...config.agents,
                      [agentKey]: {
                        ...config.agents[agentKey],
                        [field]: newStores
                      }
                    }
                  });
                }
              }}
            />
            <Label htmlFor={`store-missing-${type}-${agentKey}-${missingStoreName}`} className="text-[10px] cursor-pointer text-red-600 truncate" title="Base não encontrada">
              ⚠️ {missingStoreName.split('/').pop()}
            </Label>
          </div>
        ))}
      </>
    );
  };

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [config, setConfig] = useState<Config>({
    model: '',
    api_key: '',
    root: { system_prompt: '', user_prompt: '' },
    agents: {}
  })

  const [modelsConfig, setModelsConfig] = useState<ModelsConfig>({
    active_model_id: '',
    models: []
  })
  const [testingModelId, setTestingModelId] = useState<string | null>(null)

  const [activeTab, setActiveTab] = useState("general")
  const [modelSearchQuery, setModelSearchQuery] = useState("")

  const [showModelApiKeys, setShowModelApiKeys] = useState<Record<string, boolean>>({})

  // Knowledge Base State
  const [stores, setStores] = useState<Store[]>([])
  const [isLoadingStores, setIsLoadingStores] = useState(false)
  const [storesError, setStoresError] = useState<string | null>(null)
  const [storeFiles, setStoreFiles] = useState<StoreFile[]>([])
  const [selectedStore, setSelectedStore] = useState<string | null>(null)
  const [newStoreName, setNewStoreName] = useState("")
  const [isUploading, setIsUploading] = useState(false)

  // Association Modal State
  const [associationModalOpen, setAssociationModalOpen] = useState(false)
  const [pendingStore, setPendingStore] = useState<Store | null>(null)
  const [selectedAgentForAssociation, setSelectedAgentForAssociation] = useState<string>("")
  const [isDoclingModalOpen, setIsDoclingModalOpen] = useState(false)
  const [storesPage, setStoresPage] = useState(1)
  const [filesPage, setFilesPage] = useState(1)
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [cloudModelsPage, setCloudModelsPage] = useState(1)
  const [localModelsPage, setLocalModelsPage] = useState(1)
  const ITEMS_PER_PAGE = 4
  const MODELS_ITEMS_PER_PAGE = 2

  const filteredCloudModelsList = (modelsConfig.models || [])
    .filter(m => (m.type === 'google_genai' || m.type === 'google_genai_edge' || m.type === 'litellm'))
    .filter(m => {
      if (!modelSearchQuery) return true;
      const query = modelSearchQuery.toLowerCase();
      return m.name.toLowerCase().includes(query) || (m.description && m.description.toLowerCase().includes(query));
    });

  const filteredLocalModelsList = (modelsConfig.models || [])
    .filter(m => (m.type.startsWith('local_') || m.type === 'litellm_local'))
    .filter(m => {
      if (!modelSearchQuery) return true;
      const query = modelSearchQuery.toLowerCase();
      return m.name.toLowerCase().includes(query) || (m.description && m.description.toLowerCase().includes(query));
    });

  const cloudModelsTotal = filteredCloudModelsList.length
  const cloudModelsTotalPages = Math.max(1, Math.ceil(cloudModelsTotal / MODELS_ITEMS_PER_PAGE))
  const cloudModelsCurrentPage = Math.min(cloudModelsPage, cloudModelsTotalPages)

  const localModelsTotal = filteredLocalModelsList.length
  const localModelsTotalPages = Math.max(1, Math.ceil(localModelsTotal / MODELS_ITEMS_PER_PAGE))
  const localModelsCurrentPage = Math.min(localModelsPage, localModelsTotalPages)

  useEffect(() => {
    setCloudModelsPage(1)
    setLocalModelsPage(1)
  }, [modelSearchQuery])

  const loadingMessages = [
    "Analisando sua pergunta...",
    "Consultando a base de conhecimento do Tocantins...",
    "Verificando informações com as Secretarias...",
    "Formatando a melhor resposta para você...",
    "Só mais um momento, estou finalizando...",
    "Acessando os últimos leis, decretos e normativas...",
    "Cruzando referências para garantir precisão...",
    "Buscando dados atualizados nos sistemas do Estado...",
    "Organizando as informações de forma clara...",
    "Validando as fontes oficiais...",
    "Verificando a legislação vigente sobre o tema..."
  ];
  const [currentLoadingMessage, setCurrentLoadingMessage] = useState(loadingMessages[0]);

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
  const [isDeletingStore, setIsDeletingStore] = useState(false);

  const doclingProcessing = useDoclingProcessing();


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

  const fetchModelsConfig = async () => {
    try {
      const res = await fetch('/api/models')
      const data = await res.json()
      setModelsConfig(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (isConfigOpen) {
      fetchConfig()
      fetchModelsConfig()
    }
  }, [isConfigOpen])

  const testModelConnection = async (model: ModelItem) => {
    setTestingModelId(model.id)
    try {
      const res = await fetch('/api/models/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: model.id,
          model_type: model.type,
          endpoint: model.endpoint,
          api_key: model.api_key
        })
      })
      const data = await res.json()
      if (data.success) {
        showFeedback("Conexão Bem Sucedida", `Conectado ao modelo ${model.name}!`, "success")
      } else {
        showFeedback("Erro na Conexão", data.message, "error")
      }
    } catch {
      showFeedback("Erro de Rede", "Não foi possível testar a conexão.", "error")
    } finally {
      setTestingModelId(null)
    }
  }

  const handleSaveModelsConfig = async () => {
    try {
      const res = await fetch('/api/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(modelsConfig)
      })
      if (!res.ok) throw new Error('Falha ao salvar configurações de modelos')

      const data = await res.json()
      setModelsConfig(data.config) // Update with returned config

      // Update main config model as well to reflect sync
      setConfig(prev => ({ ...prev, model: data.config.active_model_id }))

      showFeedback("Sucesso", "Configurações de modelos salvas!", "success")
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao salvar modelos: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    }
  }

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
    setIsLoadingStores(true)
    setStoresError(null)
    try {
      const res = await fetch('/api/knowledge/stores')
      if (!res.ok) {
        throw new Error(`Erro ${res.status}: ${res.statusText}`)
      }
      const data = await res.json()
      if (Array.isArray(data)) {
        setStores(data)
        await fetchConfig()
      } else if (data.error) {
        setStoresError(data.error)
      } else {
        setStoresError("Formato de resposta inválido")
      }
    } catch (e) {
      console.error(e)
      setStoresError(e instanceof Error ? e.message : "Erro desconhecido ao carregar bases")
    } finally {
      setIsLoadingStores(false)
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
          await associateStoreToAgent(agentKey, data.name, newStoreName)
        } else {
          // Open modal for manual association
          setPendingStore(data)
          setAssociationModalOpen(true)
          setSelectedAgentForAssociation("")
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

  const associateStoreToAgent = async (agentKey: string, storeName: string, _storeDisplayName: string) => {
    const agent = config.agents[agentKey]
    const currentStores = agent.file_search_stores || []

    if (!currentStores.includes(storeName)) {
      const updatedAgent = {
        ...agent,
        file_search_stores: [...(agent.file_search_stores || []), storeName],
        gemini_file_search_stores: [...(agent.gemini_file_search_stores || []), storeName],
        others_file_search_stores: [...(agent.others_file_search_stores || []), storeName]
      }

      // Update local config
      setConfig(prev => ({
        ...prev,
        agents: {
          ...prev.agents,
          [agentKey]: updatedAgent
        }
      }))

      // Persist to backend (Both Agent Individual and potentially Global if needed)
      try {
        await fetch(`/api/agent/${agentKey}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedAgent)
        })

        // Final Force: Save Global Config to ensure consistency
        fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...config,
            agents: {
              ...config.agents,
              [agentKey]: updatedAgent
            }
          })
        }).catch(e => console.error("Global sync failed:", e));

        showFeedback("Sucesso", `Base associada ao agente "${agent.name}"!`, "success")
      } catch (err) {
        console.error("Failed to associate store:", err)
        showFeedback("Aviso", "Erro ao salvar associação.", "error")
      }
    } else {
      showFeedback("Sucesso", `Base criada e já associada a "${agent.name}"!`, "success")
    }
  }

  const handleManualAssociation = async () => {
    if (!pendingStore || !selectedAgentForAssociation) return
    await associateStoreToAgent(selectedAgentForAssociation, pendingStore.name, pendingStore.display_name)
    setAssociationModalOpen(false)
    setPendingStore(null)
  }

  const confirmDeleteStore = async () => {
    const name = deleteConfirmation.storeName;
    if (!name) return;

    setIsDeletingStore(true);

    try {
      const res = await fetch(`/api/knowledge/stores/${name}`, { method: 'DELETE' })

      if (!res.ok) {
        let errorMsg = res.statusText
        try {
          const errData = await res.json()
          if (errData.error) errorMsg = errData.error
        } catch {
          errorMsg = res.statusText
        }
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
      setDeleteConfirmation({ open: false, storeName: null }); // Close modal only on success

    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro de conexão ao excluir base", "error")
    } finally {
      setIsDeletingStore(false);
    }
  }

  const handleDeleteStore = (name: string) => {
    setDeleteConfirmation({ open: true, storeName: name });
  }

  const fetchStoreFiles = async (storeName: string) => {
    setSelectedStore(storeName)
    setFilesPage(1) // Reset to first page
    setIsLoadingFiles(true)
    try {
      const res = await fetch(`/api/knowledge/stores/${storeName}/files`)
      const data = await res.json()
      if (Array.isArray(data)) {
        setStoreFiles(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoadingFiles(false)
    }
  }

  const [fileToDelete, setFileToDelete] = useState<StoreFile | null>(null);
  const [isDeletingFile, setIsDeletingFile] = useState(false);

  const handleDeleteFile = (fileName: string) => {
    const file = storeFiles.find(f => f.name === fileName);
    if (file) setFileToDelete(file);
  }

  const confirmDeleteFile = async () => {
    if (!selectedStore || !fileToDelete) return
    const fileName = fileToDelete.name

    setIsDeletingFile(true)

    try {
      const res = await fetch(`/api/knowledge/stores/${selectedStore}/files/${fileName}`, {
        method: 'DELETE'
      })

      const data = await res.json()

      if (!res.ok || data.error) {
        throw new Error(data.error || "Falha ao excluir arquivo")
      }

      setStoreFiles(storeFiles.filter(f => f.name !== fileName))
      showFeedback("Sucesso", "Arquivo excluído com sucesso!", "success")
      setFileToDelete(null) // Close modal only on success
    } catch (e) {
      console.error(e)
      showFeedback("Erro", "Erro ao excluir arquivo: " + (e instanceof Error ? e.message : "Desconhecido"), "error")
    } finally {
      setIsDeletingFile(false)
    }
  }

  const uploadFilesToStore = async (files: File[]) => {
    if (!selectedStore) return
    setIsUploading(true)

    let successCount = 0;
    let errorCount = 0;

    for (const file of files) {
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
          successCount++;
        } else {
          errorCount++;
        }
      } catch (e) {
        console.error(e)
        errorCount++;
      }
    }

    // Refresh files
    await fetchStoreFiles(selectedStore)

    if (errorCount === 0) {
      showFeedback("Sucesso", `${successCount} arquivo(s) enviado(s) com sucesso!`, "success")
    } else {
      showFeedback("Atenção", `${successCount} enviados, ${errorCount} falharam.`, "error")
    }

    setIsUploading(false)
  }

  useEffect(() => {
    if (activeTab === 'knowledge' || activeTab === 'agents' || activeTab === 'scraping') {
      fetchStores()
    }
    if (activeTab === 'models') {
      setCloudModelsPage(1)
      setLocalModelsPage(1)
    }
  }, [activeTab])

  useEffect(() => {
    setCloudModelsPage(p => Math.min(p, cloudModelsTotalPages))
    setLocalModelsPage(p => Math.min(p, localModelsTotalPages))
  }, [cloudModelsTotalPages, localModelsTotalPages])

  useEffect(() => {
    let interval: any;
    if (isLoading) {
      let msgIndex = 0;
      setCurrentLoadingMessage(loadingMessages[0]);
      interval = setInterval(() => {
        msgIndex = (msgIndex + 1) % loadingMessages.length;
        setCurrentLoadingMessage(loadingMessages[msgIndex]);
      }, 5000); // Intervalo aumentado de 3s para 5s para reduzir sensação de loop
    }
    return () => clearInterval(interval);
  }, [isLoading]);

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
                body { 
                  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
                  padding: 40px; 
                  line-height: 1.4; 
                  color: #111; 
                  max-width: 210mm; 
                  margin: 0 auto;
                  font-size: 14px;
                }
                img { max-width: 100%; border-radius: 4px; }
                a { color: #2563eb; text-decoration: none; font-weight: 500; }
                p { margin-bottom: 0.8em; text-align: justify; margin-top: 0; }
                strong { font-weight: 700; color: #000; }
                
                ul, ol { margin-left: 0; padding-left: 20px; margin-bottom: 0.8em; margin-top: 0; }
                li { margin-bottom: 0.3em; padding-left: 5px; }
                
                h1 { color: #1e3a8a; margin-top: 1.5em; margin-bottom: 0.8em; font-size: 20px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
                h2 { color: #1e3a8a; margin-top: 1.2em; margin-bottom: 0.6em; font-size: 16px; font-weight: 700; }
                h3 { color: #334155; margin-top: 1em; margin-bottom: 0.5em; font-size: 14px; font-weight: 700; text-transform: uppercase; }
                
                blockquote { border-left: 4px solid #cbd5e1; padding-left: 12px; color: #475569; margin: 1em 0; font-style: italic; background: #f8fafc; padding: 8px 12px; border-radius: 4px; }
                pre { background: #f1f5f9; padding: 12px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; border-radius: 6px; border: 1px solid #e2e8f0; margin: 1em 0; }
                code { background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 0.9em; border: 1px solid #e2e8f0; }
                
                /* Table Styles if they appear */
                table { width: 100%; border-collapse: collapse; margin-bottom: 1em; }
                th, td { border: 1px solid #e2e8f0; padding: 8px; text-align: left; }
                th { background-color: #f8fafc; font-weight: 600; }

                @media print {
                   @page {
                      size: A4;
                      margin: 15mm 15mm 15mm 15mm;
                   }
                   body { 
                      padding: 0; 
                      margin: 0; 
                      max-width: 100%; 
                      width: 100%;
                      -webkit-print-color-adjust: exact;
                      print-color-adjust: exact;
                   }
                   .no-print { display: none; }
                   a { text-decoration: none; color: #000; }
                   
                   /* Ensure breaks inside page */
                   h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
                   img { break-inside: avoid; page-break-inside: avoid; }
                   ul, ol, pre, blockquote { break-inside: avoid; page-break-inside: avoid; }
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
        throw new Error('Falha na comunicação com o servidor.')
      }

      // Preparação para processar o streaming SSE
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantMessage = ''
      let assistantMessageAdded = false

      if (!reader) throw new Error('Streaming não suportado pelo navegador.')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          const trimmedLine = line.trim()
          if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue

          const dataStr = trimmedLine.slice(6)
          if (dataStr === '[DONE]') continue

          try {
            const data = JSON.parse(dataStr)

            if (data.chunk || data.reply) {
              // Assim que recebermos o primeiro pedaço de texto, paramos o loading
              setIsLoading(false)

              const contentDelta = data.chunk || data.reply
              if (data.reply) {
                assistantMessage = contentDelta // Se for reply final, substitui
              } else {
                assistantMessage += contentDelta // Se for chunk, acumula
              }

              if (!assistantMessageAdded) {
                setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage }])
                assistantMessageAdded = true
              } else {
                setMessages(prev => {
                  const newMsgs = [...prev]
                  const lastMsg = newMsgs[newMsgs.length - 1]
                  if (lastMsg && lastMsg.role === 'assistant') {
                    lastMsg.content = assistantMessage
                  }
                  return newMsgs
                })
              }

              // Rolagem automática durante o stream
              scrollToBottom()
            } else if (data.error) {
              throw new Error(data.reply || data.error)
            }
          } catch (e) {
            console.warn('Erro ao processar chunk de streaming:', e)
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setIsLoading(false)
      const errorMsg = error instanceof Error ? error.message : 'Desculpe, ocorreu um erro ao processar sua mensagem.'
      setMessages(prev => {
        const newMsgs = [...prev]
        const lastMsg = newMsgs[newMsgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === '') {
          lastMsg.content = `⚠️ **Erro:** ${errorMsg}`
          return newMsgs
        }
        return [...prev, { role: 'assistant', content: `⚠️ **Erro:** ${errorMsg}` }]
      })
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
        <DialogContent className="max-w-4xl h-[90vh] !flex !flex-col overflow-hidden pointer-events-auto p-0 gap-0 z-[100]">
          <DialogHeader className="px-6 py-4 border-b shrink-0">
            <DialogTitle>Configurações do Sistema</DialogTitle>
            <DialogDescription>
              Ajuste o modelo, chaves de API, prompts dos agentes, integrações e configurações de base do conhecimento (RAG).
            </DialogDescription>
          </DialogHeader>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full flex-1 flex flex-col overflow-hidden min-h-0">
            <div className="px-6 pt-4 shrink-0">
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="general" className="text-xs">Geral</TabsTrigger>
                <TabsTrigger value="models" className="text-xs">Modelos</TabsTrigger>
                <TabsTrigger value="agents" className="text-xs">Agentes</TabsTrigger>
                <TabsTrigger value="knowledge" className="text-xs">Base conhecimento (RAG)</TabsTrigger>
                <TabsTrigger value="scraping" className="text-xs">Scraping</TabsTrigger>
                <TabsTrigger value="integration" className="text-xs">Integração</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="models" className="flex-1 overflow-hidden p-6 space-y-4 m-0 flex flex-col min-h-0 h-full data-[state=active]:flex">
              <div className="shrink-0 flex items-center gap-4 bg-slate-50 p-3 rounded-md border">
                <div className="relative flex-1">
                  <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Pesquisar modelos por nome ou descrição..."
                    value={modelSearchQuery}
                    onChange={(e) => setModelSearchQuery(e.target.value)}
                    className="pl-10 h-10 w-full"
                  />
                </div>
                {modelSearchQuery && (
                  <Button variant="ghost" size="sm" onClick={() => setModelSearchQuery("")}>
                    Limpar
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4 flex-1 min-h-0 overflow-hidden">
                <Card className="flex-1 flex flex-col min-h-0 overflow-hidden">
                  <CardContent className="p-4 flex-1 flex flex-col min-h-0 overflow-hidden">
                    <h3 className="text-lg font-semibold mb-4">Modelos em Nuvem </h3>
                    <div className="flex-1 overflow-y-auto pr-2 border rounded-md">
                      <RadioGroup
                        value={modelsConfig.active_model_id}
                        onValueChange={(val) => setModelsConfig({ ...modelsConfig, active_model_id: val })}
                        className="space-y-0.5 p-1"
                      >
                        {filteredCloudModelsList
                          .slice((cloudModelsCurrentPage - 1) * MODELS_ITEMS_PER_PAGE, cloudModelsCurrentPage * MODELS_ITEMS_PER_PAGE)
                          .map(model => (
                            <Card key={model.id} className={`border-2 ${modelsConfig.active_model_id === model.id ? 'border-primary bg-primary/10 ring-1 ring-primary/20' : 'border-transparent'} shadow-sm hover:border-gray-200 transition-all mb-2`}>
                              <CardContent className="p-2">
                                <div className="flex items-start space-x-3">
                                  <RadioGroupItem value={model.id} id={`r-${model.id}`} className="mt-1" />
                                  <div className="flex-1 space-y-2">
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-1.5">
                                        <Label htmlFor={`r-${model.id}`} className="font-bold text-sm cursor-pointer hover:text-primary transition-colors">
                                          {model.name}
                                        </Label>
                                        <span title={model.description} className="cursor-help inline-flex items-center">
                                          <Info className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                                        </span>
                                      </div>
                                      {modelsConfig.active_model_id === model.id && (
                                        <span className="text-[9px] bg-primary text-primary-foreground px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                          Ativo
                                        </span>
                                      )}
                                    </div>

                                    <div className="mt-1">
                                      <Label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">API Key</Label>
                                      <div className="flex space-x-2">
                                        <div className="relative flex-1">
                                          <Input
                                            type={showModelApiKeys[model.id] ? "text" : "password"}
                                            placeholder="Digite / Cole a API Key"
                                            value={model.api_key || ''}
                                            onChange={(e) => {
                                              const newModels = modelsConfig.models.map(m =>
                                                m.id === model.id ? { ...m, api_key: e.target.value } : m
                                              )
                                              setModelsConfig({ ...modelsConfig, models: newModels })
                                            }}
                                            className="mt-1 h-8 text-sm"
                                          />
                                          <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                            onClick={() => setShowModelApiKeys(prev => ({ ...prev, [model.id]: !prev[model.id] }))}
                                          >
                                            {showModelApiKeys[model.id] ? (
                                              <EyeOff className="h-4 w-4" />
                                            ) : (
                                              <Eye className="h-4 w-4" />
                                            )}
                                          </Button>
                                        </div>
                                      </div>
                                    </div>

                                    <div className="pt-1 flex gap-2">
                                      <Button onClick={handleSaveModelsConfig} size="sm" className="h-7 text-[10px] px-3 gap-1">
                                        <Save className="h-3 w-3" /> Salvar
                                      </Button>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-[10px] px-3"
                                        onClick={() => testModelConnection(model)}
                                        disabled={testingModelId === model.id}
                                      >
                                        {testingModelId === model.id ? (
                                          <><Loader2 className="mr-1 h-2 w-2 animate-spin" /> ...</>
                                        ) : (
                                          "Testar"
                                        )}
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </RadioGroup>
                    </div>

                    {cloudModelsTotal > 0 && (
                      <div className="flex justify-between items-center mt-auto pt-3 text-xs text-gray-500 shrink-0 border-t bg-slate-50/50 px-2 rounded-b-md">
                        <Button
                          variant="outline" size="sm" className="h-7 w-7 p-0 bg-white"
                          disabled={cloudModelsCurrentPage === 1}
                          onClick={() => setCloudModelsPage(p => Math.max(1, p - 1))}
                        >
                          <ChevronLeft className="h-3 w-3" />
                        </Button>
                        <span className="font-semibold text-gray-600 text-[10px]">
                          Página {cloudModelsCurrentPage} de {cloudModelsTotalPages}
                        </span>
                        <Button
                          variant="outline" size="sm" className="h-7 w-7 p-0 bg-white"
                          disabled={cloudModelsCurrentPage >= cloudModelsTotalPages}
                          onClick={() => setCloudModelsPage(p => Math.min(cloudModelsTotalPages, p + 1))}
                        >
                          <ChevronRight className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="flex-1 flex flex-col min-h-0 overflow-hidden">
                  <CardContent className="p-4 flex-1 flex flex-col min-h-0 overflow-hidden">
                    <h3 className="text-lg font-semibold mb-4">Modelos Locais</h3>
                    <div className="flex-1 overflow-y-auto pr-2 border rounded-md">
                      <RadioGroup
                        value={modelsConfig.active_model_id}
                        onValueChange={(val) => setModelsConfig({ ...modelsConfig, active_model_id: val })}
                        className="space-y-0.5 p-1"
                      >
                        {filteredLocalModelsList
                          .slice((localModelsCurrentPage - 1) * MODELS_ITEMS_PER_PAGE, localModelsCurrentPage * MODELS_ITEMS_PER_PAGE)
                          .map(model => (
                            <Card key={model.id} className={`border-2 ${modelsConfig.active_model_id === model.id ? 'border-primary bg-primary/10 ring-1 ring-primary/20' : 'border-transparent'} shadow-sm hover:border-gray-200 transition-all mb-2`}>
                              <CardContent className="p-2">
                                <div className="flex items-start space-x-3">
                                  <RadioGroupItem value={model.id} id={`r-${model.id}`} className="mt-1" />
                                  <div className="flex-1 space-y-2">
                                    <div className="flex items-center justify-between">
                                      <div className="flex items-center gap-1.5">
                                        <Label htmlFor={`r-${model.id}`} className="font-bold text-sm cursor-pointer hover:text-primary transition-colors">
                                          {model.name}
                                        </Label>
                                        <span title={model.description} className="cursor-help inline-flex items-center">
                                          <Info className="h-3.5 w-3.5 text-blue-500 shrink-0" />
                                        </span>
                                      </div>
                                      {modelsConfig.active_model_id === model.id && (
                                        <span className="text-[9px] bg-primary text-primary-foreground px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                                          Ativo
                                        </span>
                                      )}
                                    </div>

                                    <div className="mt-1">
                                      <Label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Endpoint URL</Label>
                                      <Input
                                        value={model.endpoint || model.api_base || ''}
                                        onChange={(e) => {
                                          const newModels = modelsConfig.models.map(m =>
                                            m.id === model.id ? { ...m, endpoint: e.target.value } : m
                                          )
                                          setModelsConfig({ ...modelsConfig, models: newModels })
                                        }}
                                        className="mt-1 h-8 text-sm"
                                        placeholder="http://localhost:12434/v1"
                                      />
                                    </div>

                                    <Accordion type="single" collapsible className="w-full">
                                      <AccordionItem value="api-key" className="border-none">
                                        <AccordionTrigger className="py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider hover:no-underline">
                                          API Key (Opcional)
                                        </AccordionTrigger>
                                        <AccordionContent className="pb-2">
                                          <div className="flex space-x-2">
                                            <div className="relative flex-1">
                                              <Input
                                                type={showModelApiKeys[model.id] ? "text" : "password"}
                                                placeholder="Opcional"
                                                value={model.api_key || ''}
                                                onChange={(e) => {
                                                  const newModels = modelsConfig.models.map(m =>
                                                    m.id === model.id ? { ...m, api_key: e.target.value } : m
                                                  )
                                                  setModelsConfig({ ...modelsConfig, models: newModels })
                                                }}
                                                className="h-8 text-sm"
                                              />
                                              <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                                onClick={() => setShowModelApiKeys(prev => ({ ...prev, [model.id]: !prev[model.id] }))}
                                              >
                                                {showModelApiKeys[model.id] ? (
                                                  <EyeOff className="h-4 w-4" />
                                                ) : (
                                                  <Eye className="h-4 w-4" />
                                                )}
                                              </Button>
                                            </div>
                                          </div>
                                        </AccordionContent>
                                      </AccordionItem>
                                    </Accordion>

                                    <div className="pt-1 flex gap-2">
                                      <Button onClick={handleSaveModelsConfig} size="sm" className="h-7 text-[10px] px-3 gap-1">
                                        <Save className="h-3 w-3" /> Salvar
                                      </Button>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-[10px] px-3"
                                        onClick={() => testModelConnection(model)}
                                        disabled={testingModelId === model.id}
                                      >
                                        {testingModelId === model.id ? (
                                          <><Loader2 className="mr-1 h-2 w-2 animate-spin" /> ...</>
                                        ) : (
                                          "Testar"
                                        )}
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          ))}
                      </RadioGroup>
                    </div>

                    {localModelsTotal > 0 && (
                      <div className="flex justify-between items-center mt-auto pt-3 text-xs text-gray-500 shrink-0 border-t bg-slate-50/50 px-2 rounded-b-md">
                        <Button
                          variant="outline" size="sm" className="h-7 w-7 p-0 bg-white"
                          disabled={localModelsCurrentPage === 1}
                          onClick={() => setLocalModelsPage(p => Math.max(1, p - 1))}
                        >
                          <ChevronLeft className="h-3 w-3" />
                        </Button>
                        <span className="font-semibold text-gray-600 text-[10px]">
                          Página {localModelsCurrentPage} de {localModelsTotalPages}
                        </span>
                        <Button
                          variant="outline" size="sm" className="h-7 w-7 p-0 bg-white"
                          disabled={localModelsCurrentPage >= localModelsTotalPages}
                          onClick={() => setLocalModelsPage(p => Math.min(localModelsTotalPages, p + 1))}
                        >
                          <ChevronRight className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="general" className="flex-1 overflow-y-auto p-6 space-y-4 m-0 min-h-0 h-full">
              <div className="grid gap-2">
                <Label htmlFor="root_sys">Prompt do Sistema (Root/Orquestrador)</Label>
                <Textarea
                  id="root_sys"
                  rows={15}
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
                  rows={6}
                  value={config.root?.user_prompt || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    root: { ...config.root, user_prompt: e.target.value }
                  })}
                />
              </div>
            </TabsContent>

            <TabsContent value="agents" className="flex-1 overflow-hidden p-6 space-y-4 m-0 flex flex-col min-h-0 h-full data-[state=active]:flex">
              <div className="text-sm text-muted-foreground mb-2 shrink-0">
                Configure os prompts específicos para cada agente especialista.
              </div>

              <div className="flex items-center justify-between mb-2 p-2 bg-slate-50 rounded-md border shrink-0">
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

              <div className="border rounded-md p-4 flex-1 overflow-y-auto">
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
                              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                                <h4 className="font-semibold text-sm text-slate-800 mb-4 flex items-center gap-2">

                                  <Settings className="h-4 w-4 text-slate-600" /> Configuração por Família de LLM
                                </h4>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                  {/* Coluna 1: Lado Gemini */}
                                  {(() => {
                                    const activeModel = modelsConfig.models.find(m => m.id === modelsConfig.active_model_id);
                                    const isGeminiActive = activeModel ? isGeminiModel(activeModel.name) : false;

                                    return (
                                      <div className={`group space-y-3 p-4 bg-blue-50/30 rounded-md border border-blue-100 shadow-sm relative overflow-hidden transition-all duration-300 ${!isGeminiActive ? 'opacity-60 grayscale-[0.8]' : ''}`}>
                                        {!isGeminiActive && (
                                          <div className="absolute inset-0 z-10 bg-slate-100/40 backdrop-blur-[2px] cursor-not-allowed flex items-center justify-center border-2 border-dashed border-blue-200 rounded-md m-0.5">
                                            <div className="bg-blue-600 text-white text-[10px] font-bold px-3 py-1.5 rounded-md shadow-xl transform -rotate-3 flex items-center gap-1.5 border border-blue-400">
                                              <Settings className="h-3 w-3 animate-pulse" /> CONFIGURAÇÃO INDISPONÍVEL
                                            </div>
                                          </div>
                                        )}
                                        <div className="flex items-center gap-2 mb-1">
                                          <div className="p-1 bg-blue-500 rounded-sm">
                                            <Database className="h-3 w-3 text-white" />
                                          </div>
                                          <span className="text-sm font-bold text-blue-900">LLM Gemini (Google)</span>
                                        </div>
                                        <p className="text-[11px] text-blue-800/70 leading-tight italic">
                                          Configurações aplicadas a modelos Google Gemini.
                                        </p>

                                        <div className="pt-3 space-y-4 border-t border-blue-100">
                                          <div className="flex items-center space-x-2">
                                            <Checkbox
                                              id={`web-gemini-${agentKey}`}
                                              disabled={!isGeminiActive}
                                              checked={config.agents[agentKey].gemini_enable_web !== false}
                                              onCheckedChange={(checked) => {
                                                setConfig({
                                                  ...config,
                                                  agents: {
                                                    ...config.agents,
                                                    [agentKey]: { ...config.agents[agentKey], gemini_enable_web: !!checked }
                                                  }
                                                })
                                              }}
                                            />
                                            <Label htmlFor={`web-gemini-${agentKey}`} className={`text-sm font-medium text-blue-900 ${!isGeminiActive ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                                              Habilitar Pesquisa Web (Google Search)
                                            </Label>
                                          </div>

                                          <div className="space-y-2">
                                            <Label className="text-[10px] font-extrabold uppercase text-blue-700 tracking-wider">Base Conhecimento (RAG Nuvem - File Search Tool)</Label>
                                            <div className={`grid grid-cols-1 gap-1.5 max-h-32 overflow-y-auto p-1 bg-white/50 rounded border border-blue-100 ${!isGeminiActive ? 'pointer-events-none' : ''}`}>
                                              {renderStoreSelection(agentKey, 'gemini')}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })()}

                                  {/* Coluna 2: Lado Terceiros */}
                                  {(() => {
                                    const activeModel = modelsConfig.models.find(m => m.id === modelsConfig.active_model_id);
                                    const isGeminiActive = activeModel ? isGeminiModel(activeModel.name) : false;
                                    const isOthersActive = !isGeminiActive && !!activeModel;

                                    return (
                                      <div className={`group space-y-3 p-4 bg-slate-100/50 rounded-md border border-slate-200 shadow-sm relative overflow-hidden transition-all duration-300 ${!isOthersActive ? 'opacity-60 grayscale-[0.8]' : ''}`}>
                                        {!isOthersActive && (
                                          <div className="absolute inset-0 z-10 bg-slate-200/40 backdrop-blur-[2px] cursor-not-allowed flex items-center justify-center border-2 border-dashed border-slate-300 rounded-md m-0.5">
                                            <div className="bg-slate-700 text-white text-[10px] font-bold px-3 py-1.5 rounded-md shadow-xl transform rotate-3 flex items-center gap-1.5 border border-slate-500">
                                              <Settings className="h-3 w-3 animate-pulse" /> CONFIGURAÇÃO INDISPONÍVEL
                                            </div>
                                          </div>
                                        )}
                                        <div className="flex items-center gap-2 mb-1">
                                          <div className="p-1 bg-slate-600 rounded-sm">
                                            <Database className="h-3 w-3 text-white" />
                                          </div>
                                          <span className="text-sm font-bold text-slate-900">LLM Terceiros </span>
                                        </div>
                                        <p className="text-[11px] text-slate-800/70 leading-tight italic">
                                          Configurações aplicadas para LLM Terceiros (Nuvem/Local).
                                        </p>

                                        <div className="pt-3 space-y-4 border-t border-slate-200">
                                          <div className="flex items-center space-x-2">
                                            <Checkbox
                                              id={`web-others-${agentKey}`}
                                              disabled={!isOthersActive}
                                              checked={config.agents[agentKey].others_enable_web === true}
                                              onCheckedChange={(checked) => {
                                                setConfig({
                                                  ...config,
                                                  agents: {
                                                    ...config.agents,
                                                    [agentKey]: { ...config.agents[agentKey], others_enable_web: !!checked }
                                                  }
                                                })
                                              }}
                                            />
                                            <Label htmlFor={`web-others-${agentKey}`} className={`text-sm font-medium text-slate-900 ${!isOthersActive ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                                              Habilitar Pesquisa Web (DuckDuckGo)
                                            </Label>
                                          </div>

                                          <div className="space-y-2">
                                            <Label className="text-[10px] font-extrabold uppercase text-slate-700 tracking-wider">Base Conhecimento (RAG Local - ChromaDB)</Label>
                                            <div className={`grid grid-cols-1 gap-1.5 max-h-32 overflow-y-auto p-1 bg-white/50 rounded border border-slate-200 ${!isOthersActive ? 'pointer-events-none' : ''}`}>
                                              {renderStoreSelection(agentKey, 'others')}
                                            </div>
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })()}
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
            <TabsContent value="knowledge" className="flex-1 overflow-y-auto p-6 space-y-4 m-0 flex flex-col min-h-0 h-full data-[state=active]:flex">
              <div className="grid grid-cols-2 gap-4 flex-1 min-h-[500px]">
                {/* Left Column: Stores List */}
                <Card>
                  <CardContent className="p-4 h-full flex flex-col">
                    <h3 className="font-bold text-lg mb-4">Bases de Conhecimento (RAG)</h3>

                    <div className="flex space-x-2 mb-4">
                      <Input
                        className="flex-1"
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

                    <div className="flex-1 overflow-y-auto border rounded-md relative">
                      {isLoadingStores && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10">
                          <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-2" />
                          <span className="text-sm text-gray-500">Carregando bases de conhecimento...</span>
                        </div>
                      )}

                      {stores.length === 0 ? (
                        <div className="p-4 text-center text-gray-500">Nenhuma base encontrada.</div>
                      ) : (
                        stores
                          .slice((storesPage - 1) * ITEMS_PER_PAGE, storesPage * ITEMS_PER_PAGE)
                          .map(store => {
                            const associatedAgent = Object.values(config.agents).find(agent =>
                              (agent.file_search_stores || []).includes(store.name) ||
                              (agent.gemini_file_search_stores || []).includes(store.name) ||
                              (agent.others_file_search_stores || []).includes(store.name) ||
                              agent.name === store.display_name // Fallback por nome
                            )

                            return (
                              <div
                                key={store.name}
                                className={`p-3 border-b cursor-pointer flex justify-between items-center hover:bg-slate-50 ${selectedStore === store.name ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''}`}
                                onClick={() => fetchStoreFiles(store.name)}
                              >
                                <div className="flex flex-col truncate">
                                  <span className="font-medium truncate" title={store.name}>{store.display_name}</span>
                                  {associatedAgent && (
                                    <span className="text-xs text-muted-foreground truncate flex items-center gap-1">
                                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block"></span>
                                      {associatedAgent.name}
                                    </span>
                                  )}
                                </div>
                                <Button variant="ghost" size="icon" className="h-6 w-6 text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteStore(store.name); }}>
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            )
                          })

                      )}
                    </div>
                    {stores.length > ITEMS_PER_PAGE && (
                      <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                        <Button
                          variant="ghost" size="sm" className="h-8 w-8 p-0"
                          disabled={storesPage === 1}
                          onClick={() => setStoresPage(p => Math.max(1, p - 1))}
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <span>Página {storesPage} de {Math.ceil(stores.length / ITEMS_PER_PAGE)}</span>
                        <Button
                          variant="ghost" size="sm" className="h-8 w-8 p-0"
                          disabled={storesPage >= Math.ceil(stores.length / ITEMS_PER_PAGE)}
                          onClick={() => setStoresPage(p => p + 1)}
                        >
                          <ChevronRight className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
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
                          <div
                            className={`border-2 border-dashed rounded-md p-4 text-center transition-colors cursor-pointer ${isUploading || doclingProcessing.isProcessing ? 'bg-gray-100' : 'hover:bg-blue-50 border-blue-200'}`}
                            onClick={() => !isUploading && setIsDoclingModalOpen(true)}
                          >
                            {isUploading ? (
                              <span className="flex items-center justify-center text-blue-600"><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Enviando...</span>
                            ) : doclingProcessing.isProcessing ? (
                              <span className="flex items-center justify-center text-blue-600"><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Processando {doclingProcessing.items.filter(i => ['processing', 'queued', 'uploading'].includes(i.status)).length} arquivos...</span>
                            ) : (
                              <span className="text-blue-600 font-medium flex items-center justify-center gap-2">
                                <Upload className="w-4 h-4" />
                                Importar Documento
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex-1 overflow-y-auto border rounded-md relative">
                          {isLoadingFiles && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10">
                              <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-2" />
                              <span className="text-sm text-gray-500 text-center px-4">
                                Carregando Arquivos da base ({stores.find(s => s.name === selectedStore)?.display_name})...
                              </span>
                            </div>
                          )}

                          {storeFiles.length === 0 ? (
                            <div className="p-4 text-center text-gray-500">Nenhum arquivo nesta base.</div>
                          ) : (
                            storeFiles
                              .slice((filesPage - 1) * ITEMS_PER_PAGE, filesPage * ITEMS_PER_PAGE)
                              .map((file, idx) => (
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
                        {storeFiles.length > ITEMS_PER_PAGE && (
                          <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
                            <Button
                              variant="ghost" size="sm" className="h-8 w-8 p-0"
                              disabled={filesPage === 1}
                              onClick={() => setFilesPage(p => Math.max(1, p - 1))}
                            >
                              <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <span>Página {filesPage} de {Math.ceil(storeFiles.length / ITEMS_PER_PAGE)}</span>
                            <Button
                              variant="ghost" size="sm" className="h-8 w-8 p-0"
                              disabled={filesPage >= Math.ceil(storeFiles.length / ITEMS_PER_PAGE)}
                              onClick={() => setFilesPage(p => p + 1)}
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </div>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="scraping" forceMount={true} className="flex-1 overflow-hidden p-6 space-y-4 m-0 flex flex-col min-h-0 h-full data-[state=active]:flex">
              <div className="flex-1 h-full overflow-y-auto">
                <ScrapingTab
                  stores={stores}
                  isLoading={isLoadingStores}
                  error={storesError}
                  onRefresh={fetchStores}
                />
              </div>
            </TabsContent>

            <TabsContent value="integration" className="flex-1 overflow-hidden p-6 space-y-4 m-0 flex flex-col min-h-0 h-full data-[state=active]:flex">
              <div className="text-sm text-muted-foreground mb-4 shrink-0">
                Copie o código abaixo e cole no HTML do seu site para adicionar o chat TIA.
                Certifique-se de substituir o domínio se necessário.
              </div>

              <div className="flex-1 overflow-y-auto">
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
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter className="p-4 border-t shrink-0 bg-gray-50/50">
            {activeTab === 'general' ? (
              <Button onClick={handleSaveConfig} className="gap-2">
                <Save className="h-4 w-4" /> Salvar Alterações
              </Button>
            ) : activeTab === 'models' ? (
              <Button onClick={handleSaveModelsConfig} className="gap-2">
                <Save className="h-4 w-4" /> Salvar Alterações
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setIsConfigOpen(false)}>Fechar</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog >

      <Dialog open={associationModalOpen} onOpenChange={() => { }}>
        <DialogContent className="sm:max-w-[425px] pointer-events-auto z-[150]">
          <DialogHeader>
            <DialogTitle>Associar a um Agente (Obrigatório)</DialogTitle>
            <DialogDescription>
              A base "{pendingStore?.display_name}" foi criada com sucesso.
              <br />
              É obrigatório associá-la a um agente para continuar.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="agent-select">Escolha um Agente:</Label>
              <select
                id="agent-select"
                autoFocus
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={selectedAgentForAssociation}
                onChange={(e) => setSelectedAgentForAssociation(e.target.value)}
              >
                <option value="" disabled>Selecione...</option>
                {Object.entries(config.agents)
                  .sort(([, a], [, b]) => a.name.localeCompare(b.name))
                  .map(([key, agent]) => (
                    <option key={key} value={key}>{agent.name}</option>
                  ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleManualAssociation} disabled={!selectedAgentForAssociation}>
              Salvar Associação
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
                        : 'bg-white text-gray-800 rounded-2xl rounded-tl-none border border-gray-100'
                        }`}
                    >
                      {msg.role === 'assistant' ? (
                        <>
                          <div id={`msg-content-${index}`}>
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                h1: ({ node, ...props }: MarkdownComponentProps<'h1'>) => {
                                  void node
                                  return <h1 {...props} className="text-lg font-bold text-slate-900 mb-1 mt-2 border-b border-slate-200 pb-1" />
                                },
                                h2: ({ node, ...props }: MarkdownComponentProps<'h2'>) => {
                                  void node
                                  return <h2 {...props} className="text-base font-semibold text-slate-800 mb-1 mt-2" />
                                },
                                h3: ({ node, ...props }: MarkdownComponentProps<'h3'>) => {
                                  void node
                                  return <h3 {...props} className="text-sm font-semibold text-slate-700 mb-1 mt-1" />
                                },
                                p: ({ node, ...props }: MarkdownComponentProps<'p'>) => {
                                  void node
                                  return <p {...props} className="mb-1 leading-relaxed text-slate-700" />
                                },
                                ul: ({ node, ...props }: MarkdownComponentProps<'ul'>) => {
                                  void node
                                  return <ul {...props} className="list-disc pl-5 mb-1 space-y-0.5 text-slate-700" />
                                },
                                ol: ({ node, ...props }: MarkdownComponentProps<'ol'>) => {
                                  void node
                                  return <ol {...props} className="list-decimal pl-5 mb-1 space-y-0.5 text-slate-700" />
                                },
                                li: ({ node, ...props }: MarkdownComponentProps<'li'>) => {
                                  void node
                                  return <li {...props} className="pl-1" />
                                },
                                a: ({ node, ...props }: MarkdownComponentProps<'a'>) => {
                                  void node
                                  return <a {...props} className="text-blue-600 hover:text-blue-800 font-medium hover:underline transition-colors break-all" target="_blank" rel="noopener noreferrer" />
                                },
                                blockquote: ({ node, ...props }: MarkdownComponentProps<'blockquote'>) => {
                                  void node
                                  return <blockquote {...props} className="border-l-4 border-blue-200 pl-4 py-1 my-2 bg-slate-50 text-slate-600 italic rounded-r" />
                                },
                                code: ({ node, className, children, ...props }: MarkdownComponentProps<'code'>) => {
                                  void node
                                  const match = /language-(\w+)/.exec(className || '')
                                  return match ? (
                                    <code {...props} className={`bg-transparent text-inherit font-mono text-xs ${className}`}>{children}</code>
                                  ) : (
                                    <code {...props} className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-xs font-mono border border-slate-200">{children}</code>
                                  )
                                },
                                pre: ({ node, ...props }: MarkdownComponentProps<'pre'>) => {
                                  void node
                                  return <div className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-white my-2 shadow-sm"><pre {...props} className="m-0" /></div>
                                },
                                table: ({ node, ...props }: MarkdownComponentProps<'table'>) => {
                                  void node
                                  return <div className="overflow-x-auto my-2 rounded-lg border border-slate-200 shadow-sm"><table {...props} className="w-full text-sm text-left text-slate-700" /></div>
                                },
                                thead: ({ node, ...props }: MarkdownComponentProps<'thead'>) => {
                                  void node
                                  return <thead {...props} className="bg-slate-50 text-slate-700 font-semibold uppercase text-xs" />
                                },
                                th: ({ node, ...props }: MarkdownComponentProps<'th'>) => {
                                  void node
                                  return <th {...props} className="px-4 py-3 border-b border-slate-200 whitespace-nowrap" />
                                },
                                td: ({ node, ...props }: MarkdownComponentProps<'td'>) => {
                                  void node
                                  return <td {...props} className="px-4 py-3 border-b border-slate-100" />
                                },
                                hr: ({ node, ...props }: MarkdownComponentProps<'hr'>) => {
                                  void node
                                  return <hr {...props} className="my-6 border-slate-200" />
                                },
                                strong: ({ node, ...props }: MarkdownComponentProps<'strong'>) => {
                                  void node
                                  return <strong {...props} className="font-semibold text-slate-900" />
                                },
                                img: ({ node, ...props }: MarkdownComponentProps<'img'>) => {
                                  void node
                                  return <img {...props} className="rounded-lg max-w-full h-auto my-2 border border-slate-200 shadow-sm" alt={props.alt || 'Imagem'} />
                                },
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                          {index > 0 && msg.content && (
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
                    <div className="bg-white p-3 rounded-2xl rounded-tl-none border border-gray-100 shadow-sm flex items-center gap-3">
                      <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                      <span className="text-xs text-blue-600 font-medium animate-pulse">
                        {currentLoadingMessage}
                      </span>
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
        <DialogContent className="sm:max-w-[425px] pointer-events-auto z-[150]">
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
      <Dialog open={deleteConfirmation.open} onOpenChange={(open) => !isDeletingStore && setDeleteConfirmation(prev => ({ ...prev, open }))}>
        <DialogContent className="sm:max-w-[425px] pointer-events-auto z-[150]">
          <DialogHeader>
            <DialogTitle>Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir esta base de conhecimento?
              Esta ação não pode ser desfeita e removerá todos os arquivos associados.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmation(prev => ({ ...prev, open: false }))} disabled={isDeletingStore}>Cancelar</Button>
            <Button variant="destructive" onClick={confirmDeleteStore} disabled={isDeletingStore}>
              {isDeletingStore ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Excluindo...</> : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!fileToDelete} onOpenChange={(open) => !open && !isDeletingFile && setFileToDelete(null)}>
        <DialogContent className="z-[150]">
          <DialogHeader>
            <DialogTitle>Confirmar Exclusão</DialogTitle>
            <DialogDescription>
              Tem certeza que deseja excluir o arquivo <strong>{fileToDelete?.display_name || fileToDelete?.name.split('/').pop()}</strong>?
              <br />
              Essa ação não pode ser desfeita.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFileToDelete(null)} disabled={isDeletingFile}>Cancelar</Button>
            <Button variant="destructive" onClick={confirmDeleteFile} disabled={isDeletingFile}>
              {isDeletingFile ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Excluindo...</> : "Excluir"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <DoclingUploadModal
        isOpen={isDoclingModalOpen}
        onClose={() => setIsDoclingModalOpen(false)}
        onConfirm={uploadFilesToStore}
        storeName={stores.find(s => s.name === selectedStore)?.display_name || ''}
        processingState={{ items: doclingProcessing.items, isProcessing: doclingProcessing.isProcessing }}
        onAddFiles={doclingProcessing.addFiles}
        onRemoveFile={doclingProcessing.removeItem}
        onReset={doclingProcessing.reset}
        startProcessing={doclingProcessing.startProcessing}
      />
    </div >
  )
}

export default App
