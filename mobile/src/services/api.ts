import axios from 'axios';
import { saveOfflineNote, getOfflineNotes, removeOfflineNote, type OfflineNote } from './offlineStorage';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
});

export interface FiscalNoteResponse {
  note_id: string;
  items_count: number;
  seller_name: string;
  total_amount: number;
}

export interface ImportPayload {
  url: string;
  use_browser: boolean;
}

export const importNoteFromUrl = async (url: string): Promise<FiscalNoteResponse> => {
  try {
    const payload: ImportPayload = {
      url,
      use_browser: false,
    };

    const fullUrl = `${API_URL}/import/url`;
    console.log('[API] POST to:', fullUrl);
    console.log('[API] Payload:', payload);

    const response = await api.post<FiscalNoteResponse>('/import/url', payload);
    console.log('[API] Response:', response.data);
    return response.data;
  } catch (error) {
    console.error('[API] Error:', error);
    
    if (axios.isAxiosError(error)) {
      console.error('[API] Axios Error - code:', error.code);
      console.error('[API] Axios Error - message:', error.message);
      console.error('[API] Axios Error - response:', error.response);
      console.error('[API] Axios Error - request:', error.request);
      
      if (error.response) {
        switch (error.response.status) {
          case 409:
            throw new Error('Nota fiscal já importada anteriormente.');
          case 422:
            throw new Error('URL inválida ou não suportada.');
          case 400:
            throw new Error('Requisição inválida.');
          case 404:
            throw new Error('Endpoint não encontrado.');
          case 500:
            throw new Error('Erro interno do servidor.');
          case 504:
            throw new Error('Tempo limite excedido.');
          default:
            throw new Error(`Erro: ${error.response.status} - ${error.response.statusText}`);
        }
      } else if (error.request) {
        const isNetworkError = 
          error.code === 'ERR_NETWORK' || 
          error.code === 'ECONNABORTED' ||
          error.message.includes('Network Error');
        
        if (isNetworkError) {
          saveOfflineNote(url);
          throw new Error('Sem conexão. Nota salva offline para sincronização posterior.');
        }
        
        const errorMsg = `Falha na conexão com ${API_URL}. Código: ${error.code}. Verifique a rede.`;
        console.error('[API]', errorMsg);
        throw new Error(errorMsg);
      } else {
        throw new Error('Erro ao configurar requisição: ' + error.message);
      }
    } else {
      throw new Error('Erro inesperado: ' + (error instanceof Error ? error.message : String(error)));
    }
  }
};

export const syncOfflineNotes = async (): Promise<{ success: number; failed: number }> => {
  const offlineNotes = getOfflineNotes();
  
  if (offlineNotes.length === 0) {
    return { success: 0, failed: 0 };
  }
  
  let success = 0;
  let failed = 0;
  
  for (const note of offlineNotes) {
    try {
      await importNoteFromUrl(note.url);
      removeOfflineNote(note.url);
      success++;
    } catch {
      failed++;
    }
  }
  
  return { success, failed };
};

export const getOfflineNotesPending = (): OfflineNote[] => {
  return getOfflineNotes();
};

export default api;
