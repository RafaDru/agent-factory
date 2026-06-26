"""
Body Mapping V2 — Integração WebView + Testes + Renderização Comparativa
=========================================================================
"""

import os
from pathlib import Path

# Diretório alvo
POSE_DIR = Path(r"C:\Users\rafae\PersonalTrainerAgent\pta-mobile\src\pose")


def integrate_webview():
    """Integra MappingEngine no WebView."""
    print("\n1. Integrando MappingEngine no WebView...")
    
    # Criar script de integração que será injetado no WebView
    integration_script = '''
// Body Mapping Engine V2 - Integration
// Este script é injetado no WebView para usar o MappingEngine

class BodyMappingBridge {
    constructor() {
        this.engine = null;
        this.isInitialized = false;
    }
    
    init(config = {}) {
        // Criar engine com configurações padrão
        this.engine = {
            alpha: config.alpha || 0.6,
            confidenceThreshold: config.confidenceThreshold || 0.4,
            maxJump: config.maxJump || 0.15,
            history: new Map(),
            previousPositions: new Map(),
            velocities: new Map(),
        };
        this.isInitialized = true;
        console.log('[BodyMapping] Engine inicializado');
    }
    
    processFrame(landmarks) {
        if (!this.isInitialized || !this.engine) {
            return { landmarks: landmarks, filtered: false };
        }
        
        let filtered = [...landmarks];
        let corrections = 0;
        
        // 1. Confidence Filter
        filtered = filtered.map(lm => ({
            ...lm,
            visibility: lm.visibility >= this.engine.confidenceThreshold ? lm.visibility : 0
        }));
        
        // 2. Temporal Smoother (EMA)
        filtered = filtered.map((lm, idx) => {
            const prev = this.engine.previousPositions.get(idx);
            if (!prev) {
                this.engine.previousPositions.set(idx, lm);
                return lm;
            }
            const smoothed = {
                x: this.engine.alpha * lm.x + (1 - this.engine.alpha) * prev.x,
                y: this.engine.alpha * lm.y + (1 - this.engine.alpha) * prev.y,
                z: this.engine.alpha * lm.z + (1 - this.engine.alpha) * prev.z,
                visibility: lm.visibility,
            };
            this.engine.previousPositions.set(idx, smoothed);
            return smoothed;
        });
        
        // 3. Outlier Detector
        filtered = filtered.map((lm, idx) => {
            const history = this.engine.history.get(idx) || [];
            if (history.length < 3) return lm;
            
            const distances = history.slice(-10).map((prev, i, arr) => {
                if (i === 0) return 0;
                return Math.sqrt(
                    Math.pow(prev.x - arr[i-1].x, 2) +
                    Math.pow(prev.y - arr[i-1].y, 2) +
                    Math.pow(prev.z - arr[i-1].z, 2)
                );
            });
            
            const avgDist = distances.reduce((a, b) => a + b, 0) / distances.length;
            const lastDist = history.length > 0 
                ? Math.sqrt(
                    Math.pow(lm.x - history[history.length-1].x, 2) +
                    Math.pow(lm.y - history[history.length-1].y, 2) +
                    Math.pow(lm.z - history[history.length-1].z, 2)
                )
                : 0;
            
            if (lastDist > avgDist * 2 && avgDist > 0) {
                corrections++;
                return history[history.length - 1];
            }
            return lm;
        });
        
        // Atualizar histórico
        filtered.forEach((lm, idx) => {
            if (!this.engine.history.has(idx)) {
                this.engine.history.set(idx, []);
            }
            const hist = this.engine.history.get(idx);
            hist.push({...lm});
            if (hist.length > 10) hist.shift();
        });
        
        return {
            landmarks: filtered,
            filtered: true,
            corrections: corrections,
            confidence: filtered.reduce((s, lm) => s + lm.visibility, 0) / filtered.length,
        };
    }
    
    reset() {
        if (this.engine) {
            this.engine.history.clear();
            this.engine.previousPositions.clear();
            this.engine.velocities.clear();
        }
    }
}

// Instanciar globalmente para acesso pelo código existente
window.bodyMappingBridge = new BodyMappingBridge();
'''
    
    # Salvar script de integração
    integration_path = POSE_DIR / "body_mapping_integration.js"
    integration_path.write_text(integration_script, encoding="utf-8")
    print(f"  Created: body_mapping_integration.js")
    
    # Atualizar WebView para incluir o script
    webview_path = POSE_DIR / "pose_detection_webview.html"
    if webview_path.exists():
        content = webview_path.read_text(encoding="utf-8")
        
        # Adicionar script antes do </body>
        if "bodyMappingBridge" not in content:
            insertion_point = content.rfind("</body>")
            if insertion_point > 0:
                new_content = content[:insertion_point] + \
                    '\n    <script src="body_mapping_integration.js"></script>\n' + \
                    content[insertion_point:]
                webview_path.write_text(new_content, encoding="utf-8")
                print(f"  Updated: pose_detection_webview.html")
        else:
            print(f"  Already integrated: pose_detection_webview.html")


def update_react_native():
    """Atualiza PoseDetectionWebView.tsx para usar engine."""
    print("\n2. Atualizando PoseDetectionWebView.tsx...")
    
    tsx_path = POSE_DIR / "PoseDetectionWebView.tsx"
    if not tsx_path.exists():
        print(f"  File not found: {tsx_path}")
        return
    
    content = tsx_path.read_text(encoding="utf-8")
    
    # Verificar se já foi atualizado
    if "bodyMappingBridge" in content:
        print(f"  Already updated: PoseDetectionWebView.tsx")
        return
    
    # Adicionar interfaces para o Body Mapping
    new_interfaces = '''
interface BodyMappingConfig {
  alpha?: number;
  confidenceThreshold?: number;
  maxJump?: number;
}

interface BodyMappingResult {
  landmarks: Landmark[];
  filtered: boolean;
  corrections: number;
  confidence: number;
}
'''
    
    # Inserir após as interfaces existentes
    insertion_point = content.find("export interface PoseDetectionWebViewRef")
    if insertion_point > 0:
        content = content[:insertion_point] + new_interfaces + "\n" + content[insertion_point:]
    
    # Atualizar a função de processamento de dados
    old_onmessage = '''onMessage={(event) => {
                try {
                    const data = JSON.parse(event.nativeEvent.data);
                    if (data.type === 'pose') {
                        onPoseData?.(data.payload);
                    } else if (data.type === 'ready') {
                        setIsReady(true);
                        onReady?.();
                    }
                } catch (error) {
                    onError?.(error.message);
                }
            }}'''
    
    new_onmessage = '''onMessage={(event) => {
                try {
                    const data = JSON.parse(event.nativeEvent.data);
                    if (data.type === 'pose') {
                        // Processar com Body Mapping Engine
                        const landmarks = data.payload.landmarks || [];
                        const mappingResult = (window as any).bodyMappingBridge?.processFrame(landmarks);
                        
                        const enhancedPayload = {
                            ...data.payload,
                            landmarks: mappingResult?.landmarks || landmarks,
                            bodyMapping: {
                                filtered: mappingResult?.filtered || false,
                                corrections: mappingResult?.corrections || 0,
                                confidence: mappingResult?.confidence || 0,
                            },
                        };
                        
                        onPoseData?.(enhancedPayload);
                    } else if (data.type === 'ready') {
                        // Inicializar Body Mapping Engine
                        (window as any).bodyMappingBridge?.init({
                            alpha: 0.6,
                            confidenceThreshold: 0.4,
                        });
                        setIsReady(true);
                        onReady?.();
                    }
                } catch (error) {
                    onError?.(error.message);
                }
            }}'''
    
    if old_onmessage in content:
        content = content.replace(old_onmessage, new_onmessage)
        tsx_path.write_text(content, encoding="utf-8")
        print(f"  Updated: PoseDetectionWebView.tsx")
    else:
        print(f"  Could not find insertion point in PoseDetectionWebView.tsx")


def create_tests():
    """Cria testes unitários para o Body Mapping Engine."""
    print("\n3. Criando testes unitários...")
    
    tests_dir = Path(r"C:\Users\rafae\PersonalTrainerAgent\pta-mobile\src\pose\__tests__")
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    test_code = '''/**
 * Body Mapping Engine V2 - Testes Unitários
 */

import { MappingEngine, Landmark, PoseFrame } from '../core/MappingEngine';
import { TemporalSmoother } from '../core/filters/TemporalSmoother';
import { ConfidenceFilter } from '../core/filters/ConfidenceFilter';
import { OutlierDetector } from '../core/filters/OutlierDetector';
import { PredictiveCorrector } from '../core/filters/PredictiveCorrector';
import { DepthEstimator } from '../context/DepthEstimator';
import { OcclusionDetector } from '../context/OcclusionDetector';
import { ExerciseRules } from '../context/ExerciseRules';

describe('TemporalSmoother', () => {
    let smoother: TemporalSmoother;
    
    beforeEach(() => {
        smoother = new TemporalSmoother(0.6);
    });
    
    it('should smooth landmark positions', () => {
        const lm1: Landmark = { x: 0.5, y: 0.5, z: 0, visibility: 0.9 };
        const lm2: Landmark = { x: 0.6, y: 0.5, z: 0, visibility: 0.9 };
        
        const result1 = smoother.smooth(0, lm1);
        const result2 = smoother.smooth(0, lm2);
        
        expect(result1.x).toBeCloseTo(0.5);
        expect(result2.x).toBeGreaterThan(0.5);
        expect(result2.x).toBeLessThan(0.6);
    });
    
    it('should reset history', () => {
        smoother.smooth(0, { x: 0.5, y: 0.5, z: 0, visibility: 0.9 });
        smoother.reset();
        
        const result = smoother.smooth(0, { x: 0.6, y: 0.5, z: 0, visibility: 0.9 });
        expect(result.x).toBe(0.6);
    });
});

describe('ConfidenceFilter', () => {
    let filter: ConfidenceFilter;
    
    beforeEach(() => {
        filter = new ConfidenceFilter(0.4);
    });
    
    it('should keep landmarks above threshold', () => {
        const landmarks: Landmark[] = [
            { x: 0.5, y: 0.5, z: 0, visibility: 0.8 },
            { x: 0.6, y: 0.6, z: 0, visibility: 0.3 },
        ];
        
        const result = filter.filter(landmarks);
        
        expect(result[0].visibility).toBe(0.8);
        expect(result[1].visibility).toBe(0);
    });
});

describe('OutlierDetector', () => {
    let detector: OutlierDetector;
    
    beforeEach(() => {
        detector = new OutlierDetector(2.0, 10);
    });
    
    it('should detect spikes', () => {
        const history = new Map<number, Landmark[]>();
        history.set(0, [
            { x: 0.5, y: 0.5, z: 0, visibility: 0.9 },
            { x: 0.51, y: 0.5, z: 0, visibility: 0.9 },
            { x: 0.52, y: 0.5, z: 0, visibility: 0.9 },
        ]);
        
        const current: Landmark = { x: 0.9, y: 0.5, z: 0, visibility: 0.9 };
        
        const result = detector.detect([current], history);
        
        expect(result.corrections).toBeGreaterThan(0);
    });
});

describe('MappingEngine', () => {
    let engine: MappingEngine;
    
    beforeEach(() => {
        engine = new MappingEngine({ alpha: 0.6, confidenceThreshold: 0.4 });
    });
    
    it('should process frame with filters', () => {
        const frame: PoseFrame = {
            landmarks: Array(33).fill(null).map((_, i) => ({
                x: 0.5 + Math.random() * 0.1,
                y: 0.5 + Math.random() * 0.1,
                z: 0,
                visibility: 0.8,
            })),
            worldLandmarks: [],
            confidence: 0.8,
            timestamp: Date.now(),
        };
        
        const result = engine.processFrame(frame);
        
        expect(result.landmarks).toHaveLength(33);
        expect(result.filtersApplied).toContain('ConfidenceFilter');
        expect(result.filtersApplied).toContain('TemporalSmoother');
    });
    
    it('should reset state', () => {
        engine.processFrame({
            landmarks: Array(33).fill({ x: 0.5, y: 0.5, z: 0, visibility: 0.8 }),
            worldLandmarks: [],
            confidence: 0.8,
            timestamp: Date.now(),
        });
        
        engine.reset();
        
        const result = engine.processFrame({
            landmarks: Array(33).fill({ x: 0.6, y: 0.6, z: 0, visibility: 0.8 }),
            worldLandmarks: [],
            confidence: 0.8,
            timestamp: Date.now(),
        });
        
        expect(result.landmarks[0].x).toBeCloseTo(0.6);
    });
});

describe('DepthEstimator', () => {
    let estimator: DepthEstimator;
    
    beforeEach(() => {
        estimator = new DepthEstimator();
    });
    
    it('should estimate depth from shoulder width', () => {
        const frame: PoseFrame = {
            landmarks: Array(33).fill(null).map((_, i) => ({
                x: i === 11 ? 0.3 : i === 12 ? 0.7 : 0.5,
                y: 0.5,
                z: 0,
                visibility: 0.9,
            })),
            worldLandmarks: [],
            confidence: 0.9,
            timestamp: Date.now(),
        };
        
        const result = estimator.estimateDepth(frame);
        
        expect(result.userDistance).toBeGreaterThan(0);
        expect(result.confidence).toBeGreaterThan(0);
    });
});

describe('OcclusionDetector', () => {
    let detector: OcclusionDetector;
    
    beforeEach(() => {
        detector = new OcclusionDetector(0.3, 0.5);
    });
    
    it('should detect occluded landmarks', () => {
        const landmarks: Landmark[] = Array(33).fill(null).map((_, i) => ({
            x: 0.5,
            y: 0.5,
            z: 0,
            visibility: i === 27 ? 0.1 : 0.8,
        }));
        
        const result = detector.detect(landmarks);
        
        expect(result.occludedLandmarks).toContain(27);
        expect(result.type).not.toBe('none');
    });
});

describe('ExerciseRules', () => {
    it('should validate squat rules', () => {
        const rules = new ExerciseRules('squat');
        
        const landmarks: Landmark[] = Array(33).fill(null).map((_, i) => ({
            x: i === 25 ? 0.5 : i === 27 ? 0.6 : 0.5,
            y: 0.5,
            z: 0,
            visibility: 0.8,
        }));
        
        const result = rules.validate(landmarks);
        
        expect(result.passed.length + result.failed.length).toBeGreaterThan(0);
    });
});
'''
    
    test_path = tests_dir / "body_mapping.test.ts"
    test_path.write_text(test_code, encoding="utf-8")
    print(f"  Created: __tests__/body_mapping.test.ts")


def create_comparative_rendering():
    """Cria script de renderização comparativa."""
    print("\n4. Criando script de renderização comparativa...")
    
    scripts_dir = Path(r"C:\Users\rafae\PersonalTrainerAgent\scripts")
    
    comparative_code = '''"""
Body Mapping V2 — Renderização Comparativa
==========================================
Compara renderização nativa (sem filtros) vs com filtros de melhoria.

Uso:
    python scripts/render_comparative.py --input <video> --output <output>
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
import sys

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("MediaPipe não instalado. Instale com: pip install mediapipe")


class TemporalSmoother:
    """Suavização temporal (EMA)."""
    
    def __init__(self, alpha=0.6):
        self.alpha = alpha
        self.previous = {}
    
    def smooth(self, idx, current):
        if idx not in self.previous:
            self.previous[idx] = current
            return current
        
        prev = self.previous[idx]
        smoothed = {
            'x': self.alpha * current['x'] + (1 - self.alpha) * prev['x'],
            'y': self.alpha * current['y'] + (1 - self.alpha) * prev['y'],
            'z': self.alpha * current['z'] + (1 - self.alpha) * prev['z'],
            'visibility': current['visibility'],
        }
        self.previous[idx] = smoothed
        return smoothed
    
    def reset(self):
        self.previous.clear()


class ConfidenceFilter:
    """Filtro por confiança."""
    
    def __init__(self, threshold=0.4):
        self.threshold = threshold
    
    def filter(self, landmarks):
        return [
            lm if lm['visibility'] >= self.threshold 
            else {'x': lm['x'], 'y': lm['y'], 'z': lm['z'], 'visibility': 0}
            for lm in landmarks
        ]


class OutlierDetector:
    """Detector de outliers."""
    
    def __init__(self, threshold_multiplier=2.0):
        self.threshold_multiplier = threshold_multiplier
        self.history = {}
    
    def detect(self, idx, current):
        if idx not in self.history:
            self.history[idx] = []
        
        hist = self.history[idx]
        if len(hist) < 3:
            hist.append(current)
            return current
        
        distances = []
        for i in range(1, len(hist)):
            d = np.sqrt(
                (hist[i]['x'] - hist[i-1]['x'])**2 +
                (hist[i]['y'] - hist[i-1]['y'])**2 +
                (hist[i]['z'] - hist[i-1]['z'])**2
            )
            distances.append(d)
        
        avg_dist = np.mean(distances) if distances else 0
        last_dist = np.sqrt(
            (current['x'] - hist[-1]['x'])**2 +
            (current['y'] - hist[-1]['y'])**2 +
            (current['z'] - hist[-1]['z'])**2
        )
        
        if last_dist > avg_dist * self.threshold_multiplier and avg_dist > 0:
            return hist[-1]
        
        hist.append(current)
        if len(hist) > 10:
            hist.pop(0)
        return current
    
    def reset(self):
        self.history.clear()


class BodyMappingEngine:
    """Engine de mapeamento corporal completo."""
    
    def __init__(self):
        self.smoother = TemporalSmoother(0.6)
        self.confidence_filter = ConfidenceFilter(0.4)
        self.outlier_detector = OutlierDetector(2.0)
    
    def process(self, landmarks):
        # 1. Confidence Filter
        filtered = self.confidence_filter.filter(landmarks)
        
        # 2. Outlier Detection + Smoothing
        result = []
        for i, lm in enumerate(filtered):
            lm = self.outlier_detector.detect(i, lm)
            lm = self.smoother.smooth(i, lm)
            result.append(lm)
        
        return result
    
    def reset(self):
        self.smoother.reset()
        self.outlier_detector.reset()


def draw_landmarks(img, landmarks, color=(0, 255, 0), radius=4, thickness=2):
    """Desenha landmarks na imagem."""
    h, w = img.shape[:2]
    
    for lm in landmarks:
        if lm['visibility'] > 0.3:
            x = int(lm['x'] * w)
            y = int(lm['y'] * h)
            cv2.circle(img, (x, y), radius, color, -1)
            cv2.circle(img, (x, y), radius, (255, 255, 255), 1)


def draw_connections(img, landmarks, connections, color=(0, 255, 0), thickness=2):
    """Desenha conexões entre landmarks."""
    h, w = img.shape[:2]
    
    for start, end in connections:
        if start < len(landmarks) and end < len(landmarks):
            lm1 = landmarks[start]
            lm2 = landmarks[end]
            
            if lm1['visibility'] > 0.3 and lm2['visibility'] > 0.3:
                x1, y1 = int(lm1['x'] * w), int(lm1['y'] * h)
                x2, y2 = int(lm2['x'] * w), int(lm2['y'] * h)
                cv2.line(img, (x1, y1), (x2, y2), color, thickness)


def calculate_angle(p1, p2, p3):
    """Calcula ângulo entre três pontos."""
    v1 = np.array([p1['x'] - p2['x'], p1['y'] - p2['y']])
    v2 = np.array([p3['x'] - p2['x'], p3['y'] - p2['y']])
    
    cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    angle = np.arccos(np.clip(cosine, -1, 1))
    return np.degrees(angle)


def process_video(input_path, output_path):
    """Processa vídeo e gera comparação lado a lado."""
    
    if not MEDIAPIPE_AVAILABLE:
        print("MediaPipe não disponível. Use: pip install mediapipe")
        return
    
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"Erro ao abrir vídeo: {input_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Vídeo: {input_path}")
    print(f"Resolução: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total de frames: {total_frames}")
    
    # Configurar MediaPipe
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    
    # Conexões do esqueleto
    CONNECTIONS = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
        (25, 27), (26, 28),
    ]
    
    # Engine de mapeamento
    engine = BodyMappingEngine()
    
    # Configurar escrita de vídeo
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width * 2, height)  # Lado a lado
    )
    
    frame_count = 0
    angles_native = []
    angles_filtered = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Converter para RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        
        # Frame para lado nativo
        frame_native = frame.copy()
        # Frame para lado filtrado
        frame_filtered = frame.copy()
        
        if results.pose_landmarks:
            landmarks_raw = []
            for lm in results.pose_landmarks.landmark:
                landmarks_raw.append({
                    'x': lm.x,
                    'y': lm.y,
                    'z': lm.z,
                    'visibility': lm.visibility,
                })
            
            # Lado NATIVO (sem filtros)
            draw_connections(frame_native, landmarks_raw, CONNECTIONS, (0, 255, 0), 2)
            draw_landmarks(frame_native, landmarks_raw, (0, 255, 0), 4)
            
            # Adicionar informações
            cv2.putText(frame_native, "NATIVO (sem filtros)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Calcular ângulo nativo (joelho)
            if len(landmarks_raw) > 28:
                angle = calculate_angle(landmarks_raw[23], landmarks_raw[25], landmarks_raw[27])
                angles_native.append(angle)
                cv2.putText(frame_native, f"Angulo: {angle:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Lado FILTRADO (com engine)
            filtered = engine.process(landmarks_raw)
            
            draw_connections(frame_filtered, filtered, CONNECTIONS, (255, 100, 0), 2)
            draw_landmarks(frame_filtered, filtered, (255, 100, 0), 4)
            
            # Adicionar informações
            cv2.putText(frame_filtered, "FILTRADO (Body Mapping V2)", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 100, 0), 2)
            
            # Calcular ângulo filtrado
            if len(filtered) > 28:
                angle = calculate_angle(filtered[23], filtered[25], filtered[27])
                angles_filtered.append(angle)
                cv2.putText(frame_filtered, f"Angulo: {angle:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Combinar lado a lado
        combined = np.hstack((frame_native, frame_filtered))
        out.write(combined)
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Processado: {frame_count}/{total_frames} frames")
    
    cap.release()
    out.release()
    pose.close()
    
    # Calcular estatísticas
    if angles_native and angles_filtered:
        native_std = np.std(angles_native)
        filtered_std = np.std(angles_filtered)
        improvement = ((native_std - filtered_std) / native_std) * 100
        
        print(f"\n{'='*60}")
        print(f"Resultados da Renderização Comparativa")
        print(f"{'='*60}")
        print(f"Total de frames processados: {frame_count}")
        print(f"\nVariação do ângulo (joelho):")
        print(f"  Nativo:   {native_std:.2f}° (desvio padrão)")
        print(f"  Filtrado: {filtered_std:.2f}° (desvio padrão)")
        print(f"  Melhoria: {improvement:.1f}%")
        print(f"\nVídeo de saída: {output_path}")
    else:
        print(f"\nVídeo processado: {output_path}")
    
    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Renderização comparativa: Nativo vs Body Mapping V2"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Caminho do vídeo de entrada"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Caminho do vídeo de saída (padrão: <input>_comparative.mp4)"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Arquivo não encontrado: {input_path}")
        return
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_comparative.mp4"
    
    process_video(input_path, output_path)


if __name__ == "__main__":
    main()
'''
    
    comparative_path = scripts_dir / "render_comparative.py"
    comparative_path.write_text(comparative_code, encoding="utf-8")
    print(f"  Created: scripts/render_comparative.py")


if __name__ == "__main__":
    print("=" * 60)
    print("Body Mapping V2 — Integração + Testes + Comparativo")
    print("=" * 60)
    
    integrate_webview()
    update_react_native()
    create_tests()
    create_comparative_rendering()
    
    print("\n" + "=" * 60)
    print("Concluído!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Abrir Expo Go para testar WebView")
    print("2. Executar testes: npm test")
    print("3. Executar comparativo:")
    print("   python scripts/render_comparative.py --input <video>")
