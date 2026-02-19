import axios from 'axios';

// Create an Axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Define TypeScript interfaces
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

/**
 * Imports a fiscal note from a given URL
 * @param url The URL of the fiscal note to import
 * @returns Promise<FiscalNoteResponse> The imported fiscal note data
 */
export const importNoteFromUrl = async (url: string): Promise<FiscalNoteResponse> => {
  try {
    const payload: ImportPayload = {
      url,
      use_browser: false,
    };

    const response = await api.post<FiscalNoteResponse>('/import/url', payload);
    return response.data;
  } catch (error) {
    // Handle different types of errors and return user-friendly messages
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with error status
        switch (error.response.status) {
          case 409:
            throw new Error('Nota fiscal já importada anteriormente.');
          case 422:
            throw new Error('URL inválida ou não suportada. Por favor, verifique a URL e tente novamente.');
          case 400:
            throw new Error('Requisição inválida. Verifique os parâmetros enviados.');
          case 404:
            throw new Error('Endpoint não encontrado. Verifique se o servidor está funcionando corretamente.');
          case 500:
            throw new Error('Erro interno do servidor. Ocorreu um problema ao processar sua solicitação.');
          case 504:
            throw new Error('Tempo limite excedido. O sistema demorou muito para processar a requisição.');
          default:
            throw new Error(`Erro na requisição: ${error.response.status} - ${error.response.statusText}`);
        }
      } else if (error.request) {
        // Request was made but no response received
        throw new Error('Falha na conexão com o servidor. Verifique sua conexão de internet e tente novamente.');
      } else {
        // Something else happened while setting up the request
        throw new Error('Ocorreu um erro inesperado ao configurar a requisição.');
      }
    } else {
      // Non-Axios error
      throw new Error('Ocorreu um erro inesperado durante a operação.');
    }
  }
};

export default api;