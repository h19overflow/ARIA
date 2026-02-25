import { RotateCcw, Check, Zap } from 'lucide-react';
import clsx from 'clsx';

interface PhaseHeaderProps {
  activePhase: 0 | 1 | 2;
  completedPhases: Set<number>;
  onPhaseClick: (phase: 0 | 1 | 2) => void;
  onReset: () => void;
}

const PHASES = [
  { index: 0 as const, label: 'Describe',  color: '#ee4f27', dim: 'rgba(238,79,39,0.12)' },
  { index: 1 as const, label: 'Analyse',   color: '#ee4f27', dim: 'rgba(238,79,39,0.12)' },
  { index: 2 as const, label: 'Build',     color: '#ee4f27', dim: 'rgba(238,79,39,0.12)' },
];

export default function PhaseHeader({ activePhase, completedPhases, onPhaseClick, onReset }: PhaseHeaderProps) {
  return (
    <header className={clsx(
      'flex items-center justify-between shrink-0',
      'h-14 px-5',
      'border-b border-white/[0.05]',
    )} style={{ background: '#0c0c0c', zIndex: 50, position: 'relative' }}>

      {/* Logo */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: '#ee4f27', boxShadow: '0 2px 8px rgba(238,79,39,0.4)' }}>
          <Zap size={14} color="white" strokeWidth={2.5} fill="white" />
        </div>
        <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.1em', color: '#fff' }}>ARIA</span>
      </div>

      {/* Stepper — centered absolutely so logo/reset don't affect centering */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-0">
        {PHASES.map((phase, i) => {
          const isActive = activePhase === phase.index;
          const isDone   = completedPhases.has(phase.index);
          const isPending = !isActive && !isDone;
          const isClickable = !isActive && (isDone || phase.index === 0);

          return (
            <div key={phase.index} className="flex items-center">
              {/* Step pill */}
              <div
                role={isClickable ? 'button' : undefined}
                tabIndex={isClickable ? 0 : undefined}
                onClick={isClickable ? () => onPhaseClick(phase.index) : undefined}
                onKeyDown={isClickable ? (e) => { if (e.key === 'Enter') onPhaseClick(phase.index); } : undefined}
                className={clsx(
                'flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold',
                'transition-all duration-300',
                isClickable && 'cursor-pointer hover:brightness-125',
              )} style={{
                background: isActive ? phase.dim : isDone ? 'rgba(255,255,255,0.05)' : 'transparent',
                border: `1px solid ${isActive ? phase.color + '55' : isDone ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.06)'}`,
                color: isActive ? phase.color : isDone ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.28)',
                boxShadow: isActive ? `0 0 12px ${phase.color}30` : 'none',
              }}>
                {/* Circle indicator */}
                <div className="w-4 h-4 rounded-full flex items-center justify-center shrink-0"
                  style={{
                    background: isActive ? phase.color : isDone ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.06)',
                    border: isPending ? '1px solid rgba(255,255,255,0.12)' : 'none',
                  }}>
                  {isDone
                    ? <Check size={9} color="rgba(255,255,255,0.7)" strokeWidth={3} />
                    : isActive
                      ? <div className="w-1.5 h-1.5 rounded-full bg-white" />
                      : <span style={{ fontSize: 8, color: 'rgba(255,255,255,0.3)', fontWeight: 700, lineHeight: 1 }}>{phase.index + 1}</span>
                  }
                </div>
                {phase.label}
              </div>

              {/* Connector */}
              {i < PHASES.length - 1 && (
                <div className="w-8 h-px mx-1 rounded-full overflow-hidden"
                  style={{ background: 'rgba(255,255,255,0.08)' }}>
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: completedPhases.has(phase.index) ? '100%' : '0%',
                      background: 'linear-gradient(90deg, #ee4f27, #ff6b4a)',
                    }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Reset */}
      <button
        onClick={onReset}
        title="Start over"
        className={clsx(
          'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium shrink-0',
          'text-white/30 hover:text-white/70 border border-transparent hover:border-white/10',
          'transition-all duration-150',
          activePhase === 0 ? 'invisible' : 'visible',
        )}
      >
        <RotateCcw size={12} strokeWidth={2} />
        Reset
      </button>
    </header>
  );
}
