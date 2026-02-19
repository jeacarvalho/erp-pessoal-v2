import { useEffect, useRef, useState, useCallback } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import { Haptics, ImpactStyle, NotificationType } from '@capacitor/haptics';

export interface QRScannerState {
  isScanning: boolean;
  isLoading: boolean;
  scannedUrl: string | null;
}

export interface QRScannerActions {
  startScanning: () => Promise<void>;
  stopScanning: () => Promise<void>;
  resetScanner: () => void;
  toggleCamera: () => void;
  toggleFlashlight: () => Promise<void>;
}

export interface UseQRScannerReturn extends QRScannerState, QRScannerActions {}

const SCANNER_ELEMENT_ID = 'qr-code-scanner';

export const useQRScanner = (
  onQRCodeDetected: (decodedText: string) => Promise<void>,
  onError?: (errorMessage: string) => void
): UseQRScannerReturn => {
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [scannedUrl, setScannedUrl] = useState<string | null>(null);
  const [currentCameraIndex, setCurrentCameraIndex] = useState<number>(-1);
  const [cameras, setCameras] = useState<Array<{ id: string; label: string }>>([]);
  const [flashlightSupported, setFlashlightSupported] = useState(false);

  const triggerHaptic = useCallback(async (type: 'success' | 'error' | 'medium' = 'medium') => {
    try {
      if (type === 'success') {
        await Haptics.notification({ type: NotificationType.Success });
      } else if (type === 'error') {
        await Haptics.notification({ type: NotificationType.Error });
      } else {
        await Haptics.impact({ style: ImpactStyle.Medium });
      }
    } catch {
      // Haptics not available
    }
  }, []);

  const initializeCameras = useCallback(async (): Promise<void> => {
    try {
      const devices = await Html5Qrcode.getCameras();
      if (devices && devices.length > 0) {
        setCameras(devices);
        setFlashlightSupported(devices.length > 0);
        
        const backCameraIndex = devices.findIndex(
          (device) =>
            device.label.toLowerCase().includes('back') ||
            device.label.toLowerCase().includes('rear') ||
            device.label.toLowerCase().includes('traseira') ||
            device.label.toLowerCase().includes('posterior')
        );
        
        setCurrentCameraIndex(backCameraIndex >= 0 ? backCameraIndex : devices.length - 1);
      } else {
        throw new Error('Nenhuma câmera encontrada no dispositivo.');
      }
    } catch (err) {
      throw new Error('Erro ao acessar câmeras. Verifique as permissões.');
    }
  }, []);

  const startScanning = useCallback(async (): Promise<void> => {
    if (scannerRef.current?.isScanning) {
      return;
    }

    setScannedUrl(null);
    setIsLoading(true);

    try {
      if (cameras.length === 0) {
        await initializeCameras();
      }

      if (cameras.length === 0) {
        throw new Error('Nenhuma câmera disponível.');
      }

      scannerRef.current = new Html5Qrcode(SCANNER_ELEMENT_ID, {
        formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
        verbose: false,
      });

      const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 },
        aspectRatio: 1.0,
      };

      const currentCamera = cameras[currentCameraIndex] || cameras[0];

      await scannerRef.current.start(
        currentCamera.id,
        config,
        async (decodedText: string) => {
          if (scannerRef.current?.isScanning) {
            await scannerRef.current.pause();
            setIsScanning(false);
            setScannedUrl(decodedText);
            setIsLoading(true);
            
            await triggerHaptic('medium');

            try {
              await onQRCodeDetected(decodedText);
              await triggerHaptic('success');
            } catch (err) {
              const errorMsg = err instanceof Error ? err.message : 'Erro ao importar nota fiscal';
              await triggerHaptic('error');
              if (onError) {
                onError(errorMsg);
              }
              throw err;
            } finally {
              setIsLoading(false);
            }
          }
        },
        () => {
          // QR Code not found yet - ignore continuous scanning errors
        }
      );

      setIsScanning(true);
      setIsLoading(false);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Erro ao iniciar scanner';
      setIsScanning(false);
      setIsLoading(false);
      if (onError) {
        onError(errorMsg);
      }
    }
  }, [cameras, currentCameraIndex, initializeCameras, onQRCodeDetected, onError, triggerHaptic]);

  const stopScanning = useCallback(async (): Promise<void> => {
    if (scannerRef.current?.isScanning) {
      try {
        await scannerRef.current.stop();
      } catch {
        // Ignore stop errors
      }
    }
    setIsScanning(false);
  }, []);

  const resetScanner = useCallback((): void => {
    stopScanning();
    setScannedUrl(null);
    setScannedUrl(null);
    setTimeout(() => startScanning(), 300);
  }, [startScanning, stopScanning]);

  const toggleCamera = useCallback((): void => {
    if (cameras.length <= 1) {
      return;
    }

    const nextIndex = (currentCameraIndex + 1) % cameras.length;
    setCurrentCameraIndex(nextIndex);
    
    if (isScanning) {
      stopScanning().then(() => {
        setTimeout(() => startScanning(), 300);
      });
    }
  }, [cameras.length, currentCameraIndex, isScanning, startScanning, stopScanning]);

  const toggleFlashlight = useCallback(async (): Promise<void> => {
    if (!scannerRef.current || !flashlightSupported) {
      return;
    }

    return;
  }, [flashlightSupported]);

  useEffect(() => {
    initializeCameras();
    return () => {
      if (scannerRef.current?.isScanning) {
        scannerRef.current.stop().catch(() => {
          // Ignore cleanup errors
        });
      }
    };
  }, [initializeCameras]);

  return {
    isScanning,
    isLoading,
    scannedUrl,
    startScanning,
    stopScanning,
    resetScanner,
    toggleCamera,
    toggleFlashlight,
  };
};

export default useQRScanner;
