import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import useQRScanner from './useQRScanner';
import { Button } from '../ui';
import {
  CameraRotate,
  Scan,
  Warning,
  ArrowCounterClockwise
} from '@phosphor-icons/react';

export interface QRCodeScannerProps {
  onQRCodeDetected: (decodedText: string) => Promise<void>;
  onError?: (errorMessage: string) => void;
}

const QRCodeScanner: React.FC<QRCodeScannerProps> = ({
  onQRCodeDetected,
  onError,
}) => {
  const [permissionStatus, setPermissionStatus] = useState<'prompt' | 'granted' | 'denied' | 'checking'>('checking');

  const {
    isScanning,
    isLoading,
    startScanning,
    resetScanner,
    toggleCamera,
  } = useQRScanner(onQRCodeDetected, onError);

  useEffect(() => {
    const checkCameraSupport = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setPermissionStatus('denied');
          return;
        }

        if (navigator.permissions && navigator.permissions.query) {
          try {
            const result = await navigator.permissions.query({ name: 'camera' as PermissionName });
            setPermissionStatus(result.state as 'prompt' | 'granted' | 'denied');
          } catch {
            setPermissionStatus('prompt');
          }
        } else {
          setPermissionStatus('prompt');
        }
      } catch {
        setPermissionStatus('denied');
      }
    };

    checkCameraSupport();
  }, []);

  const handleStartScanning = useCallback(async () => {
    try {
      await startScanning();
      setPermissionStatus('granted');
    } catch {
      setPermissionStatus('denied');
    }
  }, [startScanning]);

  return (
    <div className="relative">
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-gray-900/90 backdrop-blur-sm flex flex-col items-center justify-center gap-4 rounded-2xl"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Scan className="w-12 h-12 text-primary-500" />
            </motion.div>
            <p className="text-body text-gray-300">Processando nota fiscal...</p>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        layout
        className="relative overflow-hidden rounded-2xl bg-gray-800"
      >
        <div id={SCANNER_ELEMENT_ID} className="w-full min-h-[320px]" />

        {isScanning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 pointer-events-none"
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.div
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="w-56 h-56 border-4 border-primary-500/50 rounded-2xl relative"
              >
                <div className="absolute inset-0 border-4 border-primary-500 rounded-2xl m-[-4px]" />
                <motion.div
                  animate={{ top: ['0%', '100%', '0%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-primary-400 to-transparent shadow-[0_0_15px_rgba(96,165,250,0.8)]"
                />
              </motion.div>
            </div>

            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur-sm px-4 py-2 rounded-full">
              <p className="text-body-sm text-white">Posicione o QR Code aqui</p>
            </div>
          </motion.div>
        )}
      </motion.div>

      <div className="mt-4 flex flex-col gap-3">
        {!isScanning && isLoading === false && permissionStatus !== 'denied' && (
          <Button
            onClick={handleStartScanning}
            variant="primary"
            size="lg"
            leftIcon={<Scan className="w-6 h-6" />}
            className="w-full"
          >
            Iniciar Scanner
          </Button>
        )}

        {permissionStatus === 'denied' && (
          <div className="p-4 bg-gray-800 rounded-xl">
            <div className="flex items-start gap-3 mb-3">
              <Warning className="w-6 h-6 text-yellow-500 flex-shrink-0" />
              <div>
                <p className="text-body text-white font-medium">Acesso à Câmera Negado</p>
                <p className="text-body-sm text-gray-400 mt-1">
                  Para escanear QR Codes, você precisa permitir o acesso à câmera nas configurações do app.
                </p>
              </div>
            </div>
            <Button
              onClick={() => window.location.reload()}
              variant="secondary"
              size="md"
              leftIcon={<ArrowCounterClockwise className="w-5 h-5" />}
              className="w-full"
            >
              Recarregar Página
            </Button>
          </div>
        )}

        {isLoading === false && isScanning === false && (
          <Button
            onClick={resetScanner}
            variant="success"
            size="lg"
            leftIcon={<Scan className="w-6 h-6" />}
            className="w-full"
          >
            Escanear Próxima
          </Button>
        )}

        {isScanning && (
          <div className="flex gap-3 justify-center">
            <Button
              onClick={toggleCamera}
              variant="secondary"
              size="lg"
              className="flex-1"
              leftIcon={<CameraRotate className="w-6 h-6" />}
            >
              Trocar Câmera
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default QRCodeScanner;

const SCANNER_ELEMENT_ID = 'qr-code-scanner';
