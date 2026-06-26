"""
Body Mapping V2 — Script de Implementação
==========================================
Gera os arquivos do Body Mapping Engine V2.
"""

import os
from pathlib import Path

# Diretório alvo - PTA Project
POSE_DIR = Path(r"C:\Users\rafae\PersonalTrainerAgent\pta-mobile\src\pose")


def create_core_mapping_engine():
    """Cria o Core Mapping Engine."""
    core_dir = POSE_DIR / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    
    # MappingEngine.ts
    engine_code = '''/**
 * Body Mapping Engine V2
 * =====================
 * Engine principal de mapeamento corporal.
 * Processa frames de pose e aplica filtros + contexto.
 */

import { TemporalSmoother } from './filters/TemporalSmoother';
import { ConfidenceFilter } from './filters/ConfidenceFilter';
import { OutlierDetector } from './filters/OutlierDetector';
import { PredictiveCorrector } from './filters/PredictiveCorrector';

export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility: number;
}

export interface PoseFrame {
  landmarks: Landmark[];
  worldLandmarks: Landmark[];
  confidence: number;
  timestamp: number;
}

export interface ExerciseContext {
  exerciseType: string;
  phase: string;
  fixedPoints: number[];
  expectedROM: { [joint: string]: { min: number; max: number } };
  cameraAngle: string;
}

export interface EnhancedLandmark extends Landmark {
  smoothed: boolean;
  predicted: boolean;
  interpolated: boolean;
  confidence: number;
}

export interface MappedBody {
  landmarks: EnhancedLandmark[];
  confidence: number;
  filtersApplied: string[];
  correctionsMade: number;
  timestamp: number;
}

export class MappingEngine {
  private smoother: TemporalSmoother;
  private confidenceFilter: ConfidenceFilter;
  private outlierDetector: OutlierDetector;
  private predictiveCorrector: PredictiveCorrector;
  
  private history: Map<number, Landmark[]> = new Map();
  
  constructor(config?: { alpha?: number; confidenceThreshold?: number }) {
    this.smoother = new TemporalSmoother(config?.alpha ?? 0.6);
    this.confidenceFilter = new ConfidenceFilter(config?.confidenceThreshold ?? 0.4);
    this.outlierDetector = new OutlierDetector();
    this.predictiveCorrector = new PredictiveCorrector();
  }
  
  processFrame(frame: PoseFrame): MappedBody {
    const filtersApplied: string[] = [];
    let correctionsMade = 0;
    
    // 1. Confidence Filter - remove pontos ruins
    let landmarks = this.confidenceFilter.filter(frame.landmarks);
    filtersApplied.push('ConfidenceFilter');
    
    // 2. Outlier Detector - remove spikes
    const outlierResult = this.outlierDetector.detect(landmarks, this.history);
    landmarks = outlierResult.filtered;
    correctionsMade += outlierResult.corrections;
    filtersApplied.push('OutlierDetector');
    
    // 3. Temporal Smoother - reduz jitter
    landmarks = landmarks.map((lm, idx) => {
      const smoothed = this.smoother.smooth(idx, lm);
      return smoothed;
    });
    filtersApplied.push('TemporalSmoother');
    
    // 4. Predictive Corrector - corrige pontos que pulam
    landmarks = landmarks.map((lm, idx) => {
      const predicted = this.predictiveCorrector.correct(idx, lm, this.history);
      return predicted;
    });
    filtersApplied.push('PredictiveCorrector');
    
    // Atualizar histórico
    this.updateHistory(landmarks);
    
    // Calcular confiança média
    const avgConfidence = landmarks.reduce((sum, lm) => sum + lm.confidence, 0) / landmarks.length;
    
    return {
      landmarks: landmarks.map(lm => ({
        ...lm,
        smoothed: true,
        predicted: false,
        interpolated: false,
        confidence: lm.visibility,
      })),
      confidence: avgConfidence,
      filtersApplied,
      correctionsMade,
      timestamp: frame.timestamp,
    };
  }
  
  private updateHistory(landmarks: Landmark[]): void {
    for (let i = 0; i < landmarks.length; i++) {
      if (!this.history.has(i)) {
        this.history.set(i, []);
      }
      const history = this.history.get(i)!;
      history.push({ ...landmarks[i] });
      if (history.length > 10) {
        history.shift();
      }
    }
  }
  
  reset(): void {
    this.history.clear();
  }
}
'''
    (core_dir / "MappingEngine.ts").write_text(engine_code, encoding="utf-8")
    print(f"  Created: core/MappingEngine.ts")
    
    # Criar diretório de filtros
    filters_dir = core_dir / "filters"
    filters_dir.mkdir(exist_ok=True)
    
    # TemporalSmoother.ts
    smoother_code = '''/**
 * Temporal Smoother
 * =================
 * Suavização temporal para reduzir jitter entre frames.
 * Usa Exponential Moving Average (EMA).
 */

import { Landmark } from '../MappingEngine';

export class TemporalSmoother {
  private alpha: number;
  private previousPositions: Map<number, Landmark> = new Map();
  
  constructor(alpha: number = 0.6) {
    this.alpha = Math.max(0, Math.min(1, alpha));
  }
  
  smooth(landmarkIndex: number, current: Landmark): Landmark {
    const previous = this.previousPositions.get(landmarkIndex);
    
    if (!previous) {
      this.previousPositions.set(landmarkIndex, current);
      return current;
    }
    
    const smoothed: Landmark = {
      x: this.alpha * current.x + (1 - this.alpha) * previous.x,
      y: this.alpha * current.y + (1 - this.alpha) * previous.y,
      z: this.alpha * current.z + (1 - this.alpha) * previous.z,
      visibility: current.visibility,
    };
    
    this.previousPositions.set(landmarkIndex, smoothed);
    return smoothed;
  }
  
  reset(): void {
    this.previousPositions.clear();
  }
  
  setAlpha(alpha: number): void {
    this.alpha = Math.max(0, Math.min(1, alpha));
  }
}
'''
    (filters_dir / "TemporalSmoother.ts").write_text(smoother_code, encoding="utf-8")
    print(f"  Created: core/filters/TemporalSmoother.ts")
    
    # ConfidenceFilter.ts
    confidence_code = '''/**
 * Confidence Filter
 * =================
 * Remove landmarks com confiança abaixo do threshold.
 */

import { Landmark } from '../MappingEngine';

export class ConfidenceFilter {
  private threshold: number;
  
  constructor(threshold: number = 0.4) {
    this.threshold = threshold;
  }
  
  filter(landmarks: Landmark[]): Landmark[] {
    return landmarks.map(lm => ({
      ...lm,
      visibility: lm.visibility >= this.threshold ? lm.visibility : 0,
    }));
  }
  
  setThreshold(threshold: number): void {
    this.threshold = threshold;
  }
}
'''
    (filters_dir / "ConfidenceFilter.ts").write_text(confidence_code, encoding="utf-8")
    print(f"  Created: core/filters/ConfidenceFilter.ts")
    
    # OutlierDetector.ts
    outlier_code = '''/**
 * Outlier Detector
 * =================
 * Detecta spikes abruptos entre frames.
 * Baseado em distância euclidiana.
 */

import { Landmark } from '../MappingEngine';

interface OutlierResult {
  filtered: Landmark[];
  corrections: number;
}

export class OutlierDetector {
  private thresholdMultiplier: number;
  private maxHistory: number;
  
  constructor(thresholdMultiplier: number = 2.0, maxHistory: number = 10) {
    this.thresholdMultiplier = thresholdMultiplier;
    this.maxHistory = maxHistory;
  }
  
  detect(landmarks: Landmark[], history: Map<number, Landmark[]>): OutlierResult {
    let corrections = 0;
    const filtered = landmarks.map((lm, idx) => {
      const historyLandmarks = history.get(idx) || [];
      if (historyLandmarks.length < 3) return lm;
      
      const distances = historyLandmarks.slice(-this.maxHistory).map((prev, i, arr) => {
        if (i === 0) return 0;
        return this.distance(prev, arr[i - 1]);
      });
      
      const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length;
      const stdDev = Math.sqrt(distances.reduce((sum, d) => sum + Math.pow(d - avgDistance, 2), 0) / distances.length);
      
      const lastDistance = historyLandmarks.length > 0 
        ? this.distance(lm, historyLandmarks[historyLandmarks.length - 1])
        : 0;
      
      if (lastDistance > avgDistance + this.thresholdMultiplier * stdDev && avgDistance > 0) {
        corrections++;
        return historyLandmarks[historyLandmarks.length - 1];
      }
      
      return lm;
    });
    
    return { filtered, corrections };
  }
  
  private distance(a: Landmark, b: Landmark): number {
    return Math.sqrt(
      Math.pow(a.x - b.x, 2) + 
      Math.pow(a.y - b.y, 2) + 
      Math.pow(a.z - b.z, 2)
    );
  }
}
'''
    (filters_dir / "OutlierDetector.ts").write_text(outlier_code, encoding="utf-8")
    print(f"  Created: core/filters/OutlierDetector.ts")
    
    # PredictiveCorrector.ts
    predictive_code = '''/**
 * Predictive Corrector
 * ====================
 * Corrige pontos que "pulam" entre frames.
 * Usa predição Newtoniana baseada em velocity.
 */

import { Landmark } from '../MappingEngine';

interface Velocity {
  vx: number;
  vy: number;
  vz: number;
}

export class PredictiveCorrector {
  private velocities: Map<number, Velocity> = new Map();
  private lastTimestamps: Map<number, number> = new Map();
  private maxJump: number;
  
  constructor(maxJump: number = 0.15) {
    this.maxJump = maxJump;
  }
  
  correct(landmarkIndex: number, current: Landmark, history: Map<number, Landmark[]>): Landmark {
    const historyLandmarks = history.get(landmarkIndex) || [];
    
    if (historyLandmarks.length < 2) {
      return current;
    }
    
    const prev = historyLandmarks[historyLandmarks.length - 1];
    const prevPrev = historyLandmarks.length >= 2 
      ? historyLandmarks[historyLandmarks.length - 2] 
      : prev;
    
    const jump = this.distance(current, prev);
    
    if (jump > this.maxJump) {
      const velocity = this.velocities.get(landmarkIndex);
      if (velocity) {
        return {
          x: prev.x + velocity.vx,
          y: prev.y + velocity.vy,
          z: prev.z + velocity.vz,
          visibility: current.visibility,
        };
      }
      return prev;
    }
    
    const dt = 1;
    const newVelocity: Velocity = {
      vx: (current.x - prevPrev.x) / (2 * dt),
      vy: (current.y - prevPrev.y) / (2 * dt),
      vz: (current.z - prevPrev.z) / (2 * dt),
    };
    this.velocities.set(landmarkIndex, newVelocity);
    
    return current;
  }
  
  private distance(a: Landmark, b: Landmark): number {
    return Math.sqrt(
      Math.pow(a.x - b.x, 2) + 
      Math.pow(a.y - b.y, 2) + 
      Math.pow(a.z - b.z, 2)
    );
  }
  
  reset(): void {
    this.velocities.clear();
    this.lastTimestamps.clear();
  }
}
'''
    (filters_dir / "PredictiveCorrector.ts").write_text(predictive_code, encoding="utf-8")
    print(f"  Created: core/filters/PredictiveCorrector.ts")
    
    # core/index.ts
    core_index = '''export { MappingEngine } from './MappingEngine';
export type { Landmark, PoseFrame, ExerciseContext, EnhancedLandmark, MappedBody } from './MappingEngine';
export { TemporalSmoother } from './filters/TemporalSmoother';
export { ConfidenceFilter } from './filters/ConfidenceFilter';
export { OutlierDetector } from './filters/OutlierDetector';
export { PredictiveCorrector } from './filters/PredictiveCorrector';
'''
    (core_dir / "index.ts").write_text(core_index, encoding="utf-8")
    print(f"  Created: core/index.ts")


def create_context_engine():
    """Cria o Context Engine."""
    context_dir = POSE_DIR / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    
    # ExerciseContext.ts
    exercise_context_code = '''/**
 * Exercise Context
 * =================
 * Define o contexto do exercício atual.
 */

export interface ExerciseConfig {
  type: string;
  name: string;
  fixedPoints: number[];
  movingPoints: number[];
  expectedROM: { [joint: string]: { min: number; max: number } };
  cameraAngle: 'frontal' | 'side' | '45degree';
}

export const EXERCISE_CONFIGS: { [key: string]: ExerciseConfig } = {
  squat: {
    type: 'lower_body',
    name: 'Agachamento',
    fixedPoints: [27, 28],
    movingPoints: [23, 24, 25, 26],
    expectedROM: {
      knee: { min: 60, max: 170 },
      hip: { min: 70, max: 170 },
    },
    cameraAngle: 'frontal',
  },
  bench_press: {
    type: 'upper_body',
    name: 'Supino',
    fixedPoints: [23, 24],
    movingPoints: [11, 12, 13, 14, 15, 16],
    expectedROM: {
      elbow: { min: 70, max: 170 },
      shoulder: { min: 0, max: 90 },
    },
    cameraAngle: 'frontal',
  },
};

export class ExerciseContext {
  private config: ExerciseConfig;
  
  constructor(exerciseType: string) {
    this.config = EXERCISE_CONFIGS[exerciseType] || EXERCISE_CONFIGS.squat;
  }
  
  getConfig(): ExerciseConfig {
    return this.config;
  }
  
  isFixedPoint(landmarkIndex: number): boolean {
    return this.config.fixedPoints.includes(landmarkIndex);
  }
  
  isMovingPoint(landmarkIndex: number): boolean {
    return this.config.movingPoints.includes(landmarkIndex);
  }
}
'''
    (context_dir / "ExerciseContext.ts").write_text(exercise_context_code, encoding="utf-8")
    print(f"  Created: context/ExerciseContext.ts")
    
    # DepthEstimator.ts
    depth_code = '''/**
 * Depth Estimator
 * ===============
 * Estimativa de profundidade baseada em geometria.
 * Usa tamanho conhecido dos ombros (~40cm) como referência.
 */

import { Landmark, PoseFrame } from '../core/MappingEngine';

export interface DepthMap {
  distances: Map<number, number>;
  bodyPlane: 'frontal' | 'lateral' | 'angled';
  userDistance: number;
  confidence: number;
}

export class DepthEstimator {
  private readonly SHOULDER_WIDTH_CM = 40;
  private readonly LANDMARK_LEFT_SHOULDER = 11;
  private readonly LANDMARK_RIGHT_SHOULDER = 12;
  
  estimateDepth(frame: PoseFrame): DepthMap {
    const landmarks = frame.landmarks;
    const distances = new Map<number, number>();
    
    const lShoulder = landmarks[this.LANDMARK_LEFT_SHOULDER];
    const rShoulder = landmarks[this.LANDMARK_RIGHT_SHOULDER];
    
    if (!lShoulder || !rShoulder) {
      return {
        distances,
        bodyPlane: 'frontal',
        userDistance: 2.0,
        confidence: 0,
      };
    }
    
    const shoulderWidthPixels = Math.abs(rShoulder.x - lShoulder.x) * 640;
    const scaleFactor = this.SHOULDER_WIDTH_CM / shoulderWidthPixels;
    
    const userDistance = this.estimateDistance(shoulderWidthPixels);
    
    const bodyPlane = this.estimateBodyPlane(lShoulder, rShoulder);
    
    for (let i = 0; i < landmarks.length; i++) {
      distances.set(i, userDistance);
    }
    
    const confidence = Math.min(lShoulder.visibility, rShoulder.visibility);
    
    return {
      distances,
      bodyPlane,
      userDistance,
      confidence,
    };
  }
  
  private estimateDistance(shoulderWidthPixels: number): number {
    if (shoulderWidthPixels <= 0) return 2.0;
    
    const referenceWidth = 200;
    const referenceDistance = 1.5;
    
    return referenceDistance * (referenceWidth / shoulderWidthPixels);
  }
  
  private estimateBodyPlane(lShoulder: Landmark, rShoulder: Landmark): 'frontal' | 'lateral' | 'angled' {
    const width = Math.abs(rShoulder.x - lShoulder.x);
    const depth = Math.abs(rShoulder.z - lShoulder.z);
    
    if (depth < 0.1) return 'frontal';
    if (depth > 0.3) return 'lateral';
    return 'angled';
  }
  
  getDistanceBetweenPoints(a: Landmark, b: Landmark): number {
    return Math.sqrt(
      Math.pow(a.x - b.x, 2) + 
      Math.pow(a.y - b.y, 2) + 
      Math.pow(a.z - b.z, 2)
    );
  }
}
'''
    (context_dir / "DepthEstimator.ts").write_text(depth_code, encoding="utf-8")
    print(f"  Created: context/DepthEstimator.ts")
    
    # OcclusionDetector.ts
    occlusion_code = '''/**
 * Occlusion Detector
 * ===================
 * Detecta landmarks ocluídos e classifica oclusão.
 */

import { Landmark } from '../core/MappingEngine';

export type OcclusionType = 'none' | 'partial' | 'total';

export interface OcclusionResult {
  type: OcclusionType;
  occludedLandmarks: number[];
  interpolatable: number[];
  confidence: number;
}

export class OcclusionDetector {
  private visibilityThreshold: number;
  private partialThreshold: number;
  
  constructor(visibilityThreshold: number = 0.3, partialThreshold: number = 0.5) {
    this.visibilityThreshold = visibilityThreshold;
    this.partialThreshold = partialThreshold;
  }
  
  detect(landmarks: Landmark[]): OcclusionResult {
    const occludedLandmarks: number[] = [];
    const interpolatable: number[] = [];
    
    const ADJACENT_MAP: { [key: number]: number[] } = {
      11: [12, 13, 23],
      12: [11, 14, 24],
      13: [11, 15],
      14: [12, 16],
      15: [13, 17],
      16: [14, 18],
      23: [11, 24, 25],
      24: [12, 23, 26],
      25: [23, 27],
      26: [24, 28],
      27: [25, 29],
      28: [26, 30],
    };
    
    for (let i = 0; i < landmarks.length; i++) {
      const lm = landmarks[i];
      
      if (lm.visibility < this.visibilityThreshold) {
        occludedLandmarks.push(i);
        
        const adjacent = ADJACENT_MAP[i] || [];
        const adjacentVisible = adjacent.filter(idx => 
          idx < landmarks.length && landmarks[idx].visibility > this.partialThreshold
        );
        
        if (adjacentVisible.length >= 2) {
          interpolatable.push(i);
        }
      }
    }
    
    let type: OcclusionType = 'none';
    if (occludedLandmarks.length > 0) {
      type = interpolatable.length > 0 ? 'partial' : 'total';
    }
    
    const totalLandmarks = landmarks.length;
    const visibleLandmarks = totalLandmarks - occludedLandmarks.length;
    const confidence = visibleLandmarks / totalLandmarks;
    
    return {
      type,
      occludedLandmarks,
      interpolatable,
      confidence,
    };
  }
  
  interpolatePosition(
    index: number,
    landmarks: Landmark[],
    adjacentIndices: number[]
  ): Landmark | null {
    const adjacent = adjacentIndices
      .filter(idx => idx < landmarks.length && landmarks[idx].visibility > this.partialThreshold)
      .map(idx => landmarks[idx]);
    
    if (adjacent.length === 0) return null;
    
    const avgX = adjacent.reduce((sum, lm) => sum + lm.x, 0) / adjacent.length;
    const avgY = adjacent.reduce((sum, lm) => sum + lm.y, 0) / adjacent.length;
    const avgZ = adjacent.reduce((sum, lm) => sum + lm.z, 0) / adjacent.length;
    
    return {
      x: avgX,
      y: avgY,
      z: avgZ,
      visibility: 0.3,
    };
  }
}
'''
    (context_dir / "OcclusionDetector.ts").write_text(occlusion_code, encoding="utf-8")
    print(f"  Created: context/OcclusionDetector.ts")
    
    # MovementPredictor.ts
    movement_code = '''/**
 * Movement Predictor
 * ===================
 * Predição de movimento baseada em velocity.
 * Útil para oclusão temporária.
 */

import { Landmark } from '../core/MappingEngine';

interface Velocity {
  vx: number;
  vy: number;
  vz: number;
  timestamp: number;
}

export class MovementPredictor {
  private velocities: Map<number, Velocity[]> = new Map();
  private maxHistory: number;
  private predictionHorizon: number;
  
  constructor(maxHistory: number = 5, predictionHorizon: number = 3) {
    this.maxHistory = maxHistory;
    this.predictionHorizon = predictionHorizon;
  }
  
  predict(landmarkIndex: number, current: Landmark, timestamp: number): Landmark {
    const history = this.velocities.get(landmarkIndex) || [];
    
    if (history.length < 2) {
      this.updateVelocity(landmarkIndex, current, timestamp);
      return current;
    }
    
    const avgVelocity = this.calculateAverageVelocity(history);
    
    const predictedX = current.x + avgVelocity.vx * this.predictionHorizon;
    const predictedY = current.y + avgVelocity.vy * this.predictionHorizon;
    const predictedZ = current.z + avgVelocity.vz * this.predictionHorizon;
    
    this.updateVelocity(landmarkIndex, current, timestamp);
    
    return {
      x: predictedX,
      y: predictedY,
      z: predictedZ,
      visibility: current.visibility,
    };
  }
  
  private updateVelocity(landmarkIndex: number, current: Landmark, timestamp: number): void {
    const history = this.velocities.get(landmarkIndex) || [];
    
    if (history.length > 0) {
      const last = history[history.length - 1];
      const dt = (timestamp - last.timestamp) / 1000;
      
      if (dt > 0) {
        const velocity: Velocity = {
          vx: (current.x - last.vx) / dt,
          vy: (current.y - last.vy) / dt,
          vz: (current.z - last.vz) / dt,
          timestamp,
        };
        
        history.push(velocity);
        if (history.length > this.maxHistory) {
          history.shift();
        }
      }
    } else {
      history.push({
        vx: 0,
        vy: 0,
        vz: 0,
        timestamp,
      });
    }
    
    this.velocities.set(landmarkIndex, history);
  }
  
  private calculateAverageVelocity(history: Velocity[]): Velocity {
    const recent = history.slice(-3);
    const avgVx = recent.reduce((sum, v) => sum + v.vx, 0) / recent.length;
    const avgVy = recent.reduce((sum, v) => sum + v.vy, 0) / recent.length;
    const avgVz = recent.reduce((sum, v) => sum + v.vz, 0) / recent.length;
    
    return { vx: avgVx, vy: avgVy, vz: avgVz, timestamp: 0 };
  }
  
  reset(): void {
    this.velocities.clear();
  }
}
'''
    (context_dir / "MovementPredictor.ts").write_text(movement_code, encoding="utf-8")
    print(f"  Created: context/MovementPredictor.ts")
    
    # ExerciseRules.ts
    rules_code = '''/**
 * Exercise Rules
 * ===============
 * Regras de validação por exercício.
 */

export interface Rule {
  name: string;
  description: string;
  validate: (landmarks: any[]) => boolean;
  message: string;
}

export interface ExerciseRulesConfig {
  exerciseType: string;
  fixedPoints: number[];
  rules: Rule[];
}

export class ExerciseRules {
  private config: ExerciseRulesConfig;
  
  constructor(exerciseType: string) {
    this.config = this.getConfigForExercise(exerciseType);
  }
  
  private getConfigForExercise(exerciseType: string): ExerciseRulesConfig {
    const configs: { [key: string]: ExerciseRulesConfig } = {
      squat: {
        exerciseType: 'squat',
        fixedPoints: [27, 28],
        rules: [
          {
            name: 'knee_past_toe',
            description: 'Joelho ultrapassa linha do pé',
            validate: (landmarks) => {
              const knee = landmarks[25];
              const ankle = landmarks[27];
              if (!knee || !ankle) return true;
              return knee.x <= ankle.x + 0.1;
            },
            message: 'Joelho está ultrapassando a linha do pé',
          },
          {
            name: 'back_arch',
            description: 'Costas arqueadas',
            validate: (landmarks) => {
              const shoulder = landmarks[11];
              const hip = landmarks[23];
              const knee = landmarks[25];
              if (!shoulder || !hip || !knee) return true;
              const torsoAngle = Math.abs(shoulder.y - hip.y) / Math.abs(shoulder.x - hip.x + 0.001);
              return torsoAngle > 0.5;
            },
            message: 'Costas estão arqueadas',
          },
        ],
      },
      bench_press: {
        exerciseType: 'bench_press',
        fixedPoints: [23, 24],
        rules: [
          {
            name: 'elbow_flare',
            description: 'Cotovelos abrindo demais',
            validate: (landmarks) => {
              const elbow = landmarks[13];
              const shoulder = landmarks[11];
              if (!elbow || !shoulder) return true;
              return Math.abs(elbow.x - shoulder.x) < 0.3;
            },
            message: 'Cotovelos estão abrindo demais',
          },
        ],
      },
    };
    
    return configs[exerciseType] || configs.squat;
  }
  
  validate(landmarks: any[]): { passed: Rule[]; failed: Rule[] } {
    const passed: Rule[] = [];
    const failed: Rule[] = [];
    
    for (const rule of this.config.rules) {
      if (rule.validate(landmarks)) {
        passed.push(rule);
      } else {
        failed.push(rule);
      }
    }
    
    return { passed, failed };
  }
  
  getFixedPoints(): number[] {
    return this.config.fixedPoints;
  }
}
'''
    (context_dir / "ExerciseRules.ts").write_text(rules_code, encoding="utf-8")
    print(f"  Created: context/ExerciseRules.ts")
    
    # context/index.ts
    context_index = '''export { ExerciseContext, EXERCISE_CONFIGS } from './ExerciseContext';
export type { ExerciseConfig } from './ExerciseContext';
export { DepthEstimator } from './DepthEstimator';
export type { DepthMap } from './DepthEstimator';
export { OcclusionDetector } from './OcclusionDetector';
export type { OcclusionType, OcclusionResult } from './OcclusionDetector';
export { MovementPredictor } from './MovementPredictor';
export { ExerciseRules } from './ExerciseRules';
export type { Rule, ExerciseRulesConfig } from './ExerciseRules';
'''
    (context_dir / "index.ts").write_text(context_index, encoding="utf-8")
    print(f"  Created: context/index.ts")


def update_pose_index():
    """Atualiza o index.ts do pose."""
    index_code = '''export { PoseDetectionWebView } from './PoseDetectionWebView';
export type { PoseDetectionWebViewRef } from './PoseDetectionWebView';
export { usePoseDetection } from './usePoseDetection';
export { useSensors } from './useSensors';
export { SensorService, sensorService } from './SensorService';
export type { SensorData, PhoneOrientation } from './SensorService';

// Body Mapping Engine V2
export * from './core';
export * from './context';
'''
    (POSE_DIR / "index.ts").write_text(index_code, encoding="utf-8")
    print(f"  Updated: pose/index.ts")


if __name__ == "__main__":
    print("=" * 60)
    print("Body Mapping V2 — Implementação")
    print("=" * 60)
    
    print("\n1. Criando Core Mapping Engine...")
    create_core_mapping_engine()
    
    print("\n2. Criando Context Engine...")
    create_context_engine()
    
    print("\n3. Atualizando index.ts...")
    update_pose_index()
    
    print("\n" + "=" * 60)
    print("Implementação concluída!")
    print("=" * 60)
