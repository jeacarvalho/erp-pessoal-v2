import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sun, Moon, Scan, Receipt, ChartBar, Gear, QrCode } from '@phosphor-icons/react';
import QRCodeScanner from './components/QRCodeScanner';
import { importNoteFromUrl } from './services/api';
import { Toast } from './components/ui';

type TabType = 'scanner' | 'notes' | 'stats' | 'settings';

function App() {
  const [darkMode] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('scanner');
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'warning' | 'info'; message: string } | null>(null);

  const handleQRCodeDetected = async (decodedText: string): Promise<void> => {
    try {
      await importNoteFromUrl(decodedText);
      setToast({ type: 'success', message: 'Nota fiscal importada com sucesso!' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao importar nota fiscal';
      setToast({ type: 'error', message });
    }
  };

  const handleError = (errorMessage: string): void => {
    setToast({ type: 'error', message: errorMessage });
  };

  const tabs = [
    { id: 'scanner' as const, icon: Scan, label: 'Scanner' },
    { id: 'notes' as const, icon: Receipt, label: 'Notas' },
    { id: 'stats' as const, icon: ChartBar, label: 'Estatísticas' },
    { id: 'settings' as const, icon: Gear, label: 'Ajustes' },
  ];

  return (
    <div className={`min-h-screen bg-gray-900 flex flex-col`}>
      <Toast
        type={toast?.type || 'info'}
        message={toast?.message || ''}
        isVisible={!!toast}
        onClose={() => setToast(null)}
      />

      <header className="px-5 py-4 flex items-center justify-between">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-glow">
            <QrCode className="w-6 h-6 text-white" weight="bold" />
          </div>
          <div>
            <h1 className="text-heading-3 text-white font-bold">ERP Pessoal</h1>
            <p className="text-caption text-gray-400">Controle financeiro</p>
          </div>
        </motion.div>

        <button
          className="p-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors"
          aria-label={darkMode ? 'Modo claro' : 'Modo escuro'}
        >
          {darkMode ? (
            <Sun className="w-5 h-5 text-yellow-400" />
          ) : (
            <Moon className="w-5 h-5 text-gray-400" />
          )}
        </button>
      </header>

      <main className="flex-1 px-4 pb-24">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {activeTab === 'scanner' && (
              <div className="max-w-md mx-auto pt-4">
                <h2 className="text-heading-2 text-white mb-4 text-center">Scanner NFC-e</h2>
                <QRCodeScanner
                  onQRCodeDetected={handleQRCodeDetected}
                  onError={handleError}
                />
              </div>
            )}

            {activeTab === 'notes' && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <Receipt className="w-16 h-16 mb-4 opacity-50" />
                <p className="text-body">Nenhuma nota fiscal ainda</p>
                <p className="text-body-sm mt-1">Escaneie um QR Code para começar</p>
              </div>
            )}

            {activeTab === 'stats' && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <ChartBar className="w-16 h-16 mb-4 opacity-50" />
                <p className="text-body">Estatísticas em breve</p>
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <Gear className="w-16 h-16 mb-4 opacity-50" />
                <p className="text-body">Configurações em breve</p>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 bg-gray-800/95 backdrop-blur-lg border-t border-gray-800 px-2 pb-safe">
        <div className="flex justify-around items-center max-w-md mx-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex flex-col items-center gap-1 py-3 px-4 rounded-xl transition-all duration-200
                  relative
                  ${isActive ? 'text-primary-500' : 'text-gray-400 hover:text-gray-300'}
                `}
              >
                <motion.div
                  whileTap={{ scale: 0.9 }}
                  className="relative"
                >
                  <Icon className="w-6 h-6" weight={isActive ? 'fill' : 'regular'} />
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary-500"
                    />
                  )}
                </motion.div>
                <span className="text-caption">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export default App;
