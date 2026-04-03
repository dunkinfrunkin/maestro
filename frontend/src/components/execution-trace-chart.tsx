"use client";

import { useState, useEffect, useMemo } from "react";
import { AgentRunResponse } from "@/lib/api";

const AGENT_COLORS: Record<string, { completed: string; failed: string; running: string; pending: string }> = {
  implementation: {
    completed: "bg-green-600 text-white",
    failed: "bg-green-800 text-white",
    running: "bg-green-500 text-white animate-pulse",
    pending: "bg-green-300 text-green-800"
  },
  review: {
    completed: "bg-purple-600 text-white",
    failed: "bg-purple-800 text-white",
    running: "bg-purple-500 text-white animate-pulse",
    pending: "bg-purple-300 text-purple-800"
  },
  risk_profile: {
    completed: "bg-orange-600 text-white",
    failed: "bg-orange-800 text-white",
    running: "bg-orange-500 text-white animate-pulse",
    pending: "bg-orange-300 text-orange-800"
  },
  deployment: {
    completed: "bg-blue-600 text-white",
    failed: "bg-blue-800 text-white",
    running: "bg-blue-500 text-white animate-pulse",
    pending: "bg-blue-300 text-blue-800"
  },
  monitor: {
    completed: "bg-teal-600 text-white",
    failed: "bg-teal-800 text-white",
    running: "bg-teal-500 text-white animate-pulse",
    pending: "bg-teal-300 text-teal-800"
  }
};

const formatDuration = (ms: number) => {
  if (ms === 0) return "0s";
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

interface AgentBar {
  run: AgentRunResponse;
  startPercent: number;
  widthPercent: number;
  duration: number;
}

interface ExecutionTraceChartProps {
  runs: AgentRunResponse[];
  isCompact?: boolean;
}

export function ExecutionTraceChart({ runs, isCompact = false }: ExecutionTraceChartProps) {
  const [currentTime, setCurrentTime] = useState(Date.now());

  // Update current time for live agents
  useEffect(() => {
    const hasActiveAgents = runs.some(r => r.status === 'running' || r.status === 'pending');
    if (!hasActiveAgents) return;

    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, [runs]);

  // Calculate agent bars with proper positioning
  const { agentBars, totalDuration } = useMemo(() => {
    if (runs.length === 0) {
      return { agentBars: [], totalDuration: 0 };
    }

    // Sort runs by start time
    const sortedRuns = [...runs].sort((a, b) =>
      new Date(a.started_at || 0).getTime() - new Date(b.started_at || 0).getTime()
    );

    let cumulativeTime = 0;
    const bars: AgentBar[] = [];

    for (const run of sortedRuns) {
      const startTime = run.started_at ? new Date(run.started_at).getTime() : Date.now();
      const endTime = run.finished_at
        ? new Date(run.finished_at).getTime()
        : (run.status === 'running' ? currentTime : Date.now());

      const duration = Math.max(endTime - startTime, 1000); // Min 1 second for visibility

      bars.push({
        run,
        startPercent: 0, // Will be calculated after we know total
        widthPercent: 0, // Will be calculated after we know total
        duration
      });

      cumulativeTime += duration;
    }

    // Calculate percentages based on total duration
    let currentPosition = 0;
    for (let i = 0; i < bars.length; i++) {
      bars[i].startPercent = (currentPosition / cumulativeTime) * 100;
      bars[i].widthPercent = Math.max((bars[i].duration / cumulativeTime) * 100, 2);
      currentPosition += bars[i].duration;
    }

    return { agentBars: bars, totalDuration: cumulativeTime };
  }, [runs, currentTime]);

  const timeMarkers = useMemo(() => {
    if (agentBars.length === 0) return [];

    return [
      { position: 0, text: '0s' },
      { position: 100, text: formatDuration(totalDuration) }
    ];
  }, [agentBars.length, totalDuration]);

  if (runs.length === 0) {
    return (
      <div className="text-xs text-muted">
        No agent execution yet. Agents are triggered when you move the task to a pipeline stage.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Agent Bars */}
      <div className="space-y-2">
        {agentBars.map(({ run, startPercent, widthPercent, duration }) => (
          <div key={run.id} className={`flex items-center ${isCompact ? 'h-14' : 'h-16'}`}>
            {/* Container with grey background */}
            <div className={`w-full relative ${isCompact ? 'h-12' : 'h-16'} bg-surface-hover rounded-md overflow-hidden`}>
              {/* Agent bar positioned within container */}
              <div
                className={`
                  absolute h-full rounded-md flex items-center justify-between transition-colors overflow-hidden
                  ${isCompact ? 'px-4 py-3 text-xs' : 'px-5 py-3 text-sm'}
                  ${AGENT_COLORS[run.agent_type]?.[run.status as keyof typeof AGENT_COLORS[string]] || 'bg-gray-500 text-white'}
                `}
                style={{
                  left: `${startPercent}%`,
                  width: `${widthPercent}%`,
                  minWidth: isCompact ? '220px' : '400px',
                  maxWidth: 'none'
                }}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {run.status === 'running' && (
                    <svg className={`${isCompact ? 'w-3 h-3' : 'w-4 h-4'} animate-spin flex-shrink-0`} fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {run.status === 'pending' && (
                    <svg className={`${isCompact ? 'w-3 h-3' : 'w-4 h-4'} animate-pulse opacity-60 flex-shrink-0`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                    </svg>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className={`flex items-center gap-2 ${isCompact ? 'mb-0' : 'mb-1'}`}>
                      <span className="font-semibold capitalize whitespace-nowrap">
                        {run.agent_type.replace('_', ' ')}
                      </span>
                      {!isCompact && (
                        <span className="text-xs opacity-90 flex-shrink-0">
                          {run.model || 'sonnet'}
                        </span>
                      )}
                      {run.status === 'running' && (
                        <span className={`text-xs opacity-80 ${isCompact ? 'ml-1' : 'bg-white/20 px-2 py-0.5 rounded-full'} flex-shrink-0`}>
                          {isCompact ? '• Running' : 'LIVE'}
                        </span>
                      )}
                      {run.status === 'pending' && (
                        <span className={`text-xs opacity-60 ${isCompact ? 'ml-1' : 'bg-white/15 px-2 py-0.5 rounded-full'} flex-shrink-0`}>
                          {isCompact ? '• Queued' : 'QUEUED'}
                        </span>
                      )}
                    </div>
                    <div className={`${isCompact ? 'text-xs' : 'text-xs'} opacity-80 leading-tight`}>
                      {formatDuration(duration)}
                      {run.status === 'running' && <span className="opacity-70 ml-1">(live)</span>}
                      {run.status === 'pending' && <span className="opacity-70 ml-1">(waiting)</span>}
                      {!isCompact && run.started_at && (
                        <span className="ml-2">
                          Started {new Date(run.started_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <div className={`font-mono ${isCompact ? 'text-xs' : 'text-sm'} font-semibold`}>
                    ${(run.cost_usd || 0).toFixed(4)}
                  </div>
                  <div className="font-mono text-xs opacity-90 mt-0.5">
                    {(run.input_tokens || 0).toLocaleString()}/{(run.output_tokens || 0).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Time Axis */}
      <div className="pt-2 border-t border-border">
        <div className="relative h-4">
          {timeMarkers.map((marker, index) => (
            <div
              key={index}
              className="absolute bottom-0 text-xs text-muted font-mono whitespace-nowrap"
              style={{
                left: marker.position === 100 ? 'auto' : `${marker.position}%`,
                right: marker.position === 100 ? '8px' : 'auto',
                transform: marker.position === 0 ? 'translateX(0%)' : marker.position === 100 ? 'translateX(0%)' : 'translateX(-50%)'
              }}
            >
              {marker.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}